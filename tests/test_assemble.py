"""assemble.py ve çok bloklu uzun video akışı (blok birleştirme, crossfade, müzik modu, seçmeli re-roll) testleri."""

import os
import subprocess
import sys
import types as pytypes

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from h3app import assemble, qa  # noqa: E402


def _make_av_clip(path, color, seconds=1, fps=24, freq=440, vol_db=-6):
    subprocess.run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", f"color=c={color}:s=320x180:r={fps}:d={seconds}",
        "-f", "lavfi", "-i", f"sine=frequency={freq}:sample_rate=44100:duration={seconds}",
        "-af", f"volume={vol_db}dB",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", path,
    ], check=True)
    return path


def test_assemble_three_clips_speech_mode(tmp_path):
    c1 = _make_av_clip(str(tmp_path / "b1.mp4"), "red", seconds=1, freq=330, vol_db=-4)
    c2 = _make_av_clip(str(tmp_path / "b2.mp4"), "green", seconds=1, freq=440, vol_db=-8)
    c3 = _make_av_clip(str(tmp_path / "b3.mp4"), "blue", seconds=1, freq=550, vol_db=-6)
    out = str(tmp_path / "merged_speech.mp4")

    res = assemble.assemble([c1, c2, c3], out, audio_mode="speech", crossfade_sec=0.12)
    assert res["blok_sayisi"] == 3
    assert res["kare"] == 72
    assert res["saniye"] == 3.0
    assert res["lufs"] is not None and abs(res["lufs"] - (-16.0)) <= 1.2

    # Birleşik videoda 1.0 sn ve 2.0 sn kesmeleri QA tarafından bulunur
    r = qa.check(out, "[Shot 2] At 00:01.000 [Shot 3] At 00:02.000")
    assert r["kare"] == 72 and r["kesmeler"] == [1.0, 2.0] and not r["bulunamayan"]



def _dominant_freq(path, start, length=0.2):
    import numpy as np
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{start:.3f}", "-t", f"{length:.3f}", "-i", path,
                          "-vn", "-ac", "1", "-ar", "16000", "-f", "f32le", "-"], capture_output=True, check=True).stdout
    pcm = np.frombuffer(raw, dtype=np.float32)
    spec = np.abs(np.fft.rfft(pcm * np.hanning(pcm.size)))
    return float(np.fft.rfftfreq(pcm.size, 1 / 16000.0)[int(np.argmax(spec))])


def test_assemble_keeps_audio_in_sync_and_48k(tmp_path):
    # Her blok 2 sn; 3. bloğun sesi tam 4,0 sn'de başlamalı (eski acrossfade 2×0,12 sn erken başlatıyordu)
    clips = [_make_av_clip(str(tmp_path / f"s{i}.mp4"), c, seconds=2, freq=f)
             for i, (c, f) in enumerate((("red", 300), ("green", 700), ("blue", 1500)))]
    out = str(tmp_path / "sync.mp4")
    assemble.assemble(clips, out, audio_mode="speech", crossfade_sec=0.12, auto_trim_tail=False)
    assert abs(_dominant_freq(out, 3.70) - 700) < 40     # 3,70–3,90 sn hâlâ 2. blok
    assert abs(_dominant_freq(out, 4.10) - 1500) < 40    # 4,10–4,30 sn 3. blok
    sr = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=sample_rate",
                         "-of", "csv=p=0", out], capture_output=True, text=True).stdout.strip()
    assert sr == "48000"

def test_assemble_music_mode_and_overlap_trim(tmp_path):
    c1 = _make_av_clip(str(tmp_path / "m1.mp4"), "yellow", seconds=1, freq=300)
    c2 = _make_av_clip(str(tmp_path / "m2.mp4"), "purple", seconds=1, freq=400)
    c3 = _make_av_clip(str(tmp_path / "m3.mp4"), "cyan", seconds=1, freq=500)
    music = str(tmp_path / "song.mp3")
    subprocess.run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", "sine=frequency=261.63:sample_rate=44100:duration=8",
        "-af", "volume=-3dB", "-c:a", "libmp3lame", music,
    ], check=True)

    # 8 saniyelik müzik 3 saniyelik videoya döşendiğinde çıkış tam 3.0 sn (72 kare) olur
    out_music = str(tmp_path / "merged_music.mp4")
    res_m = assemble.assemble([c1, c2, c3], out_music, audio_mode="music", music_path=music, keep_ambient=True)
    assert res_m["kare"] == 72 and res_m["saniye"] == 3.0
    assert res_m["lufs"] is not None and abs(res_m["lufs"] - (-16.0)) <= 1.5

    # Örtüşme kırpması (overlap_frames=4 -> ilk 2 bloktan 4'er kare düşer: 72 - 8 = 64 kare)
    out_ov = str(tmp_path / "merged_overlap.mp4")
    res_ov = assemble.assemble([c1, c2, c3], out_ov, audio_mode="speech", overlap_frames=4)
    assert res_ov["kare"] == 64

    # Sonda bozuk kare kırpması (trim_tails=[3, 5, 2] -> toplam 10 kare düşer: 72 - 10 = 62 kare)
    out_trim = str(tmp_path / "merged_trim.mp4")
    res_tr = assemble.assemble([c1, c2, c3], out_trim, audio_mode="speech", trim_tails=[3, 5, 2])
    assert res_tr["kare"] == 62


def test_ui_long_video_and_selective_reroll(monkeypatch, tmp_path):
    monkeypatch.setitem(sys.modules, "gradio", pytypes.SimpleNamespace(update=lambda **kw: kw))
    from h3app import ui
    fake_vid = _make_av_clip(str(tmp_path / "fake.mp4"), "blue", seconds=1, freq=440)
    monkeypatch.setattr(ui, "FAKE", True)
    monkeypatch.setenv("H3APP_FAKE_VIDEO", fake_vid)
    monkeypatch.setattr(ui.config, "OUTPUT_DIR", str(tmp_path / "out"))

    anchor, rows, msg = ui.do_plan_shots(
        "Kapalıçarşı'da yürüyen kadın", 30, "speech", "gemini-test-pro", "k", None, "real", [], {}
    )
    assert "Grand Bazaar" in anchor and len(rows) == 4 and "2 blok" in msg

    prompts_txt, dd_update, msg2 = ui.do_rewrite_blocks(
        "Kapalıçarşı'da yürüyen kadın", anchor, rows, "speech", "gemini-test-pro", "k", None, "real", [], {}
    )
    assert "=== BLOK 1" in prompts_txt and "=== BLOK 2" in prompts_txt and "2 blok" in msg2

    gen_steps = list(ui.generate_long(
        prompts_txt, anchor, rows, "speech", None, False,
        ["pika"], "16:9 yatay · 1344×768", 22, "fikir", None, "real", [], {}
    ))
    log, pika_final, h3_final, bvideos, files, sheets, bstate = gen_steps[-1]
    assert pika_final and os.path.isfile(pika_final) and h3_final is None
    assert assemble.probe_video(pika_final)["frames"] == 48   # 2 blok × 24 kare
    assert set(bstate["blocks"].keys()) == {1, 2}

    # Yalnızca 2. bloğu yeni seed (99) ile yeniden üret ve birleştir
    reroll_steps = list(ui.reroll_block(
        2, 99, "pika", prompts_txt, "speech", None, False, bstate
    ))
    r_log, r_pika, _, r_bvideos, _, _, r_bstate = reroll_steps[-1]
    assert r_bstate["blocks"][2]["seed"] == 99
    assert r_bstate["blocks"][1]["seed"] == 22   # 1. blok değişmedi
    assert "seed99.mp4" in r_bstate["blocks"][2]["pika"]
    assert r_pika and os.path.isfile(r_pika)

    # Mevcut blokları yeniden üretmeden birleştir
    a_log, a_pika, _, a_files = ui.reassemble_blocks("speech", None, False, r_bstate)
    assert "Birleştirildi" in a_log and a_pika and os.path.isfile(a_pika)

    # Bağlantı koptuğunda 'Son Üretimleri Yükle' uzun video oturumunu geri yükler
    rec = ui.load_last_outputs()
    rec_log, rec_left, _, rec_files, rec_sheets, _, rec_bprompts, rec_anchor, rec_shots, rec_bvideos, rec_bstate = rec
    assert "geri yüklendi" in rec_log and rec_left == a_pika
    assert "=== BLOK 1" in rec_bprompts and rec_anchor == anchor and len(rec_shots) == 4
    assert len(rec_bvideos) == 2 and set(rec_bstate["blocks"].keys()) == {1, 2}


def test_checkpointing_drive_sync_pil_gallery_and_single_recovery(monkeypatch, tmp_path):
    from PIL import Image
    monkeypatch.setitem(sys.modules, "gradio", pytypes.SimpleNamespace(update=lambda **kw: kw))
    from h3app import prompt_writer, ui
    fake_vid = _make_av_clip(str(tmp_path / "fake.mp4"), "green", seconds=1, freq=440)
    out_dir = tmp_path / "out_single"
    drive_dir = tmp_path / "drive_single"
    monkeypatch.setattr(ui, "FAKE", True)
    monkeypatch.setenv("H3APP_FAKE_VIDEO", fake_vid)
    monkeypatch.setattr(ui.config, "OUTPUT_DIR", str(out_dir))
    ui._state["drive_dir"] = str(drive_dir)

    try:
        # 3.2: Galeri önizlemeleri dosya yolu dizgesi yerine PIL.Image nesnesi döner (proxyPort düzeltmesi)
        ref_img = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "referans.png")
        previews = ui._preview_refs([ref_img])
        assert len(previews) == 1 and isinstance(previews[0], Image.Image)
        styled_gal, _, styled_map, _ = ui.do_stylize([ref_img], "anime", "k", "kırmızı paltolu kadın")
        assert len(styled_gal) == 2 and isinstance(styled_gal[0][0], Image.Image)
        assert isinstance(list(styled_map.values())[0], str)

        # 3.1: İki yöntem ("turbo", "pika") seçildiğinde ilk yöntem biter bitmez (ikinci yöntem beklenmeden)
        # bilgi.json, prompt.txt, video ve kontrol görselleri diske ve Drive'a anında yazılır.
        gen = ui.generate(
            prompt_writer.EXAMPLE_OUTPUT, ["turbo", "pika"], "16:9 yatay · 1344×768", 5, 22,
            "fikir", "brief", [ref_img], "real", [], {}
        )
        mid_found = False
        for step in gen:
            log, v_left, v_right, files, sheets = step
            if v_left and v_right is None and sheets:
                # İlk yöntem ("turbo") yeni bitti, "pika" henüz başlamadı!
                mid_found = True
                drive_files = os.listdir(drive_dir)
                assert any(f.endswith("_bilgi.json") for f in drive_files)
                assert any(f.endswith("_prompt.txt") for f in drive_files)
                assert any("minimax_h3_turbo" in f and f.endswith(".mp4") for f in drive_files)
                assert any(f.endswith("_kontrol.jpg") for f in drive_files)
                assert isinstance(sheets[0][0], Image.Image)
        assert mid_found
        assert v_left and v_right   # İki yöntem de tamamlandığında sol=turbo, sağ=pika

        # Tarayıcı kopup yeniden bağlandığında tekil oturum geri yüklenir
        rec = ui.load_last_outputs()
        r_log, r_left, r_right, r_files, r_sheets, r_prompt, *_ = rec
        assert "geri yüklendi" in r_log
        assert r_left and r_right and len(r_files) >= 6
        assert isinstance(r_sheets[0][0], Image.Image)
        assert r_prompt == prompt_writer.EXAMPLE_OUTPUT.strip()
    finally:
        ui._state["drive_dir"] = None
