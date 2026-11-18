"""Çok çekimli uzun video bloklarını (15–60 sn) ffmpeg ile kare-tam birleştirme ve ses miksajı.

İki ses modu desteklenir:
1. "speech" (Türkçe konuşmalı sahne, varsayılan): Her blok kendi doğal sesiyle korunur, blok geçişlerinde
   pop/click sesini önlemek için kısa fade-out/fade-in uygulanır (senkron korunur) ve çıkış -16 LUFS seviyesine dengelenir.
2. "music" (Müzikli, konuşmasız kurgu): Kullanıcının yüklediği telifsiz müzik dosyası video süresine
   kırpılarak döşenir (isteğe bağlı olarak blokların ortam sesi -12 dB altta mikslenir) ve -16 LUFS'a dengelenir.
"""

import os
import shutil
import subprocess
import tempfile

import cv2

from . import config, qa


def has_audio(path):
    """Video dosyasında ses kanalı olup olmadığını döner."""
    try:
        p = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", path],
            capture_output=True, text=True, timeout=15,
        )
        return bool((p.stdout or "").strip())
    except Exception:
        return False


def probe_video(path):
    """Videonun kare sayısı, fps, boyut, süre ve ses kanalı bilgisini döner."""
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        raise ValueError(f"Video açılamadı: {path}")
    fps = round(cap.get(cv2.CAP_PROP_FPS) or 24.0, 4)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    n = 0
    while True:
        ok, _ = cap.read()
        if not ok:
            break
        n += 1
    cap.release()
    if n == 0:
        raise ValueError(f"Videoda kare bulunamadı: {path}")
    return {
        "frames": n,
        "fps": fps,
        "width": w,
        "height": h,
        "duration": round(n / fps, 4),
        "has_audio": has_audio(path),
    }


def _prepare_clip(src, dest, target_w, target_h, target_fps, keep_frames, add_silent_audio=False):
    """Tek bir bloğu hedef çözünürlük/fps ve kesin kare sayısına (`keep_frames`) göre hazırlar."""
    info = probe_video(src)
    keep_frames = max(1, min(int(keep_frames), info["frames"]))
    dur = keep_frames / float(target_fps)
    vf = (f"fps={target_fps},scale={target_w}:{target_h}:force_original_aspect_ratio=decrease,"
          f"pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2,format=yuv420p,trim=end_frame={keep_frames},setpts=PTS-STARTPTS")
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", src]
    if info["has_audio"]:
        af = f"aresample=48000,aformat=sample_rates=48000:channel_layouts=stereo,atrim=0:{dur:.4f},asetpts=PTS-STARTPTS"
        cmd += ["-vf", vf, "-af", af, "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-c:a", "aac", "-b:a", "192k", dest]
    elif add_silent_audio:
        cmd += [
            "-f", "lavfi", "-t", f"{dur:.4f}", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
            "-vf", vf, "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-c:a", "aac", "-b:a", "192k",
            "-frames:v", str(keep_frames), dest,
        ]
    else:
        cmd += ["-vf", vf, "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "18", dest]
    subprocess.run(cmd, check=True, timeout=180)
    return keep_frames


def assemble(clips, dest, audio_mode=config.DEFAULT_AUDIO_MODE, music_path=None, keep_ambient=False,
             ambient_db=-12.0, crossfade_sec=0.12, overlap_frames=0, trim_tails=None,
             auto_trim_tail=True, target_lufs=config.TARGET_LUFS):
    """Blok videolarını kare-tam olarak birleştirir ve seçilen ses moduna göre miksleyip -16 LUFS'a dengeler.

    Parametreler:
      clips: Blok video dosya yolları listesi.
      dest: Çıkış video dosya yolu (.mp4).
      audio_mode: "speech" (doğal konuşmalı sahne) veya "music" (telifsiz dış müzikli kurgu).
      music_path: `audio_mode="music"` iken altına döşenecek müzik dosyasının yolu.
      keep_ambient: `audio_mode="music"` iken blokların kendi ortam sesini `ambient_db` seviyesinde koru.
      ambient_db: Ortam sesinin müzik altındaki seviyesi (dB, varsayılan -12.0).
      crossfade_sec: Blok geçişlerinde ses tıklamasını önleyen crossfade süresi (sn, varsayılan 0.12).
      overlap_frames: Kesintisiz uzatma modunda her sonraki bloktan (veya önceki bloğun sonundan) kırpılacak kare sayısı.
      trim_tails: Her bloğun sonundan kırpılacak kare sayıları listesi (None ise `auto_trim_tail` devreye girer).
      auto_trim_tail: True ise `qa.tail_drift()` ile son 12 karede bulanıklaşma/kayma bulunan blokların son 6–10 karesini otomatik kırpar.
      target_lufs: EBU R128 ses normalizasyonu hedefi (varsayılan -16.0 LUFS).
    """
    clips = [c for c in (clips or []) if c]
    if not clips:
        raise ValueError("Birleştirilecek en az bir video bloğu gerekli.")
    os.makedirs(os.path.dirname(os.path.abspath(dest)) or ".", exist_ok=True)

    infos = [probe_video(c) for c in clips]
    w, h, fps = infos[0]["width"], infos[0]["height"], round(infos[0]["fps"] or 24.0, 2)
    any_audio = any(inf["has_audio"] for inf in infos)
    use_music = audio_mode == "music" and bool(music_path and os.path.isfile(music_path))

    # Sonda bozulma varsa otomatik kırpılacak kare sayılarını belirle
    if trim_tails is None and auto_trim_tail:
        applied_trims = []
        for c in clips:
            try:
                td = qa.tail_drift(c, fps=fps)
                applied_trims.append(int(td["kirp_kare"]) if td.get("bozuk") else 0)
            except Exception:
                applied_trims.append(0)
    else:
        applied_trims = [int(trim_tails[i]) if trim_tails and i < len(trim_tails) and trim_tails[i] else 0
                         for i in range(len(clips))]

    # Her bloktan kaç kare korunacağını hesapla
    keep_counts = []
    for idx, inf in enumerate(infos):
        n = inf["frames"] - applied_trims[idx]
        if overlap_frames and idx < len(infos) - 1:
            n -= int(overlap_frames)
        keep_counts.append(max(1, n))

    total_frames = sum(keep_counts)
    total_dur = total_frames / float(fps)

    with tempfile.TemporaryDirectory(prefix="h3app_asm_") as tmpdir:
        need_clip_audio = any_audio and (audio_mode != "music" or keep_ambient or not use_music)
        prep_paths = []
        for idx, (src, kframes) in enumerate(zip(clips, keep_counts)):
            p = os.path.join(tmpdir, f"blk_{idx:02d}.mp4")
            _prepare_clip(src, p, w, h, fps, kframes, add_silent_audio=need_clip_audio)
            prep_paths.append(p)

        # Tek blok varsa ve müzik eklenmeyecekse doğrudan kopyala + normalize et
        if len(prep_paths) == 1 and not use_music:
            shutil.copyfile(prep_paths[0], dest)
            if any_audio and target_lufs is not None:
                qa.normalize_audio(dest, target_lufs=target_lufs)
            out_info = probe_video(dest)
            return {
                "path": dest, "kare": out_info["frames"], "saniye": round(out_info["frames"] / fps, 2),
                "fps": fps, "boyut": [w, h], "lufs": qa.measure_lufs(dest), "blok_sayisi": 1,
                "kirpilan_son_kareler": applied_trims,
            }

        # Görüntü akışlarını concat filtresiyle kare-tam birleştir
        n = len(prep_paths)
        inputs = []
        for p in prep_paths:
            inputs += ["-i", p]
        v_in = "".join(f"[{i}:v:0]" for i in range(n))
        filter_parts = [f"{v_in}concat=n={n}:v=1:a=0[vout]"]

        # Ses akışı kurgusu
        map_audio = False
        if need_clip_audio:
            if n == 1:
                filter_parts.append("[0:a:0]anull[amb]")
            elif crossfade_sec and crossfade_sec > 0:
                # Her blok sınırında kısa fade-out/fade-in (tıklama önleme). acrossfade sesi her geçişte kısaltıp
                # sonraki blokların sesini görüntünün önüne kaydırırdı (dudak senkronu); concat süreyi korur.
                labels = []
                for i in range(n):
                    dur_i = keep_counts[i] / fps
                    f = min(float(crossfade_sec) / 2.0, dur_i * 0.2)
                    chain = []
                    if i > 0:
                        chain.append(f"afade=t=in:st=0:d={f:.3f}")
                    if i < n - 1:
                        chain.append(f"afade=t=out:st={max(0.0, dur_i - f):.4f}:d={f:.3f}")
                    filter_parts.append(f"[{i}:a:0]{','.join(chain)}[af{i}]")
                    labels.append(f"[af{i}]")
                filter_parts.append(f"{''.join(labels)}concat=n={n}:v=0:a=1,apad,atrim=0:{total_dur:.4f},"
                                    "asetpts=PTS-STARTPTS[amb]")
            else:
                a_in = "".join(f"[{i}:a:0]" for i in range(n))
                filter_parts.append(f"{a_in}concat=n={n}:v=0:a=1[amb]")

        if use_music:
            mus_idx = n
            inputs += ["-stream_loop", "-1", "-i", music_path]
            fade_st = max(0.0, total_dur - 0.6)
            filter_parts.append(
                f"[{mus_idx}:a:0]aresample=48000,aformat=sample_rates=48000:channel_layouts=stereo,"
                f"atrim=0:{total_dur:.4f},asetpts=PTS-STARTPTS,afade=t=out:st={fade_st:.3f}:d=0.6[mus]"
            )
            if need_clip_audio and keep_ambient:
                filter_parts.append(
                    f"[amb]volume={float(ambient_db):.1f}dB[amb_low];"
                    f"[amb_low][mus]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[aout]"
                )
            else:
                filter_parts.append("[mus]anull[aout]")
            map_audio = True
        elif need_clip_audio:
            filter_parts.append("[amb]anull[aout]")
            map_audio = True

        cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"] + inputs + [
            "-filter_complex", ";".join(filter_parts),
            "-map", "[vout]",
        ]
        if map_audio:
            cmd += ["-map", "[aout]", "-c:a", "aac", "-b:a", "192k"]
        else:
            cmd += ["-an"]
        cmd += ["-c:v", "libx264", "-preset", "fast", "-crf", "18", "-frames:v", str(total_frames), dest]
        subprocess.run(cmd, check=True, timeout=300)

    if map_audio and target_lufs is not None:
        qa.normalize_audio(dest, target_lufs=target_lufs)

    out_info = probe_video(dest)
    return {
        "path": dest,
        "kare": out_info["frames"],
        "saniye": round(out_info["frames"] / fps, 2),
        "fps": fps,
        "boyut": [w, h],
        "lufs": qa.measure_lufs(dest) if map_audio else None,
        "blok_sayisi": len(clips),
        "kirpilan_son_kareler": applied_trims,
    }
