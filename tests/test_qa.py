"""qa.py: OpenCV ile üretilen sahte kliplerde kesme, sıçrama ve donmuş aralık ölçümü (GPU ve ağ gerektirmez)."""

import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from h3app import qa  # noqa: E402

FPS = 24


def _clip(path, shots, still=None, size=(320, 180)):
    """shots: [(kare sayısı, BGR renk)]; her çekimde hareket eden beyaz bir kare. still=(baş, son) karelerde hareket durur."""
    w = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"mp4v"), FPS, size)
    i = 0
    for frames, color in shots:
        for _ in range(frames):
            img = np.zeros((size[1], size[0], 3), np.uint8)
            img[:] = color
            x = 10 + (i if not still or i < still[0] else still[0] if i < still[1] else i - (still[1] - still[0])) * 2 % 260
            cv2.rectangle(img, (x, 60), (x + 40, 100), (255, 255, 255), -1)
            w.write(img)
            i += 1
    w.release()
    return path


def test_prompt_cuts():
    p = ("[Shot 1] ... [Shot 2] At 00:01.200, cut. [Shot 3] At 00:12.800 ... At about 4 seconds he smiles. "
         "At about 00:05.000, a cat darts past.")
    assert qa.prompt_cuts(p) == [1.2, 12.8]
    assert qa.prompt_cuts("[Shot 9] At 01:02.5 cut") == [62.5]
    assert qa.prompt_cuts("") == []


def test_cuts_match_prompt(tmp_path):
    path = _clip(str(tmp_path / "a.mp4"), [(48, (40, 40, 160)), (36, (160, 60, 30)), (60, (30, 140, 30))])
    r = qa.check(path, "[Shot 2] At 00:02.000 [Shot 3] At 00:03.500")
    assert r["kare"] == 144 and r["kesmeler"] == [2.0, 3.5]
    assert len(r["eslesen"]) == 2 and not r["bulunamayan"] and not r["beklenmeyen"]
    assert "beklenmeyen" not in qa.summary(r)


def test_single_shot_prompt_flags_jump(tmp_path):
    # aynı renk ama aradaki 10 kare başka bir andan: ALTER'in "araya eklenmiş kareler" kalibrasyon testi
    path = str(tmp_path / "b.mp4")
    w = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"mp4v"), FPS, (320, 180))
    for i in list(range(40)) + list(range(100, 110)) + list(range(50, 90)):
        img = np.full((180, 320, 3), 90, np.uint8)
        cv2.circle(img, (20 + i * 2 % 280, 90), 30, (255, 255, 255), -1)
        w.write(img)
    w.release()
    r = qa.check(path, "integrated_multimodal_description: one continuous shot.")
    assert r["beklenmeyen"] == [round(40 / FPS, 2), round(50 / FPS, 2)]
    assert "beklenmeyen kesme" in qa.summary(r)
    # prompt verilmezse kesme uyarısı yok
    assert "beklenmeyen" not in qa.summary(qa.check(path))


def test_frozen_span_and_images(tmp_path):
    path = _clip(str(tmp_path / "c.mp4"), [(96, (60, 60, 60))], still=(30, 54))
    r = qa.check(path, "", sheet=str(tmp_path / "s.jpg"), crops=str(tmp_path / "k.jpg"))
    assert len(r["donmus"]) == 1
    a, b = r["donmus"][0]
    assert abs(a - 30 / FPS) < 0.1 and abs(b - 53 / FPS) < 0.1
    assert cv2.imread(r["temas"]).shape[0] > 0 and cv2.imread(r["kirpinti"]).shape[0] > 0
    assert "donmuş" in qa.summary(r)
    assert r["lufs"] is None and qa.normalize_audio(path) is None


def test_lufs_normalization(tmp_path):
    import subprocess
    vid = str(tmp_path / "loud.mp4")
    subprocess.run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", "color=c=blue:s=320x180:r=24:d=3",
        "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100:duration=3",
        "-af", "volume=-6dB", "-c:v", "libx264", "-c:a", "aac", vid,
    ], check=True)
    before = qa.measure_lufs(vid)
    assert before is not None and abs(before - (-16.0)) > 3.0
    norm = qa.normalize_audio(vid)
    assert norm is not None and norm[0] == before
    assert abs(norm[1] - (-16.0)) <= 1.0
    r = qa.check(vid)
    assert r["kare"] == 72 and r["lufs"] == norm[1]
    assert "LUFS" in qa.summary(r)


def test_tail_drift_and_auto_trim(tmp_path):
    from h3app import assemble

    # 1. Son 8 karesinde şiddetli bulanıklaşma olan klip
    blur_path = str(tmp_path / "tail_blur.mp4")
    clean_path = str(tmp_path / "clean.mp4")
    for p, degrade in ((blur_path, "blur"), (clean_path, None)):
        w = cv2.VideoWriter(p, cv2.VideoWriter_fourcc(*"mp4v"), FPS, (320, 180))
        for i in range(48):
            img = np.full((180, 320, 3), 40, np.uint8)
            for gx in range(20, 300, 28):
                cv2.line(img, (gx, 10), (gx, 170), (220, 220, 220), 2)
            cv2.rectangle(img, (30 + (i % 20) * 2, 50), (90 + (i % 20) * 2, 130), (40, 200, 250), 2)
            if degrade == "blur" and i >= 40:
                img = cv2.GaussianBlur(img, (31, 31), 12)
            w.write(img)
        w.release()

    td_clean = qa.tail_drift(clean_path)
    assert not td_clean["bozuk"] and td_clean["kirp_kare"] == 0

    r_blur = qa.check(blur_path, "one shot")
    td_blur = r_blur["son_kayma"]
    assert td_blur["bozuk"] and td_blur["neden"] == "bulanıklaşma"
    assert 6 <= td_blur["kirp_kare"] <= 10
    assert "sonda bulanıklaşma" in qa.summary(r_blur)

    # 2. Son 8 karesinde beklenmeyen global kayma olan klip
    drift_path = str(tmp_path / "tail_drift.mp4")
    w = cv2.VideoWriter(drift_path, cv2.VideoWriter_fourcc(*"mp4v"), FPS, (320, 180))
    for i in range(48):
        img = np.full((180, 320, 3), 50, np.uint8)
        shift = (i - 39) * 35 if i >= 40 else i
        cv2.rectangle(img, (20 + shift % 220, 30), (100 + shift % 220, 150), (255, 255, 255), -1)
        w.write(img)
    w.release()
    td_drift = qa.tail_drift(drift_path)
    assert td_drift["bozuk"] and "kayma" in td_drift["neden"] and 6 <= td_drift["kirp_kare"] <= 10

    # 3. assemble.assemble() otomatik olarak ilk bloğun bozuk son karelerini kırpar (auto_trim_tail=True)
    merged = str(tmp_path / "merged_autotrim.mp4")
    res = assemble.assemble([blur_path, clean_path], merged, audio_mode="speech")
    trimmed = res["kirpilan_son_kareler"]
    assert 6 <= trimmed[0] <= 10 and trimmed[1] == 0
    assert res["kare"] == 96 - trimmed[0]


def test_style_check_photoreal_and_draft_drift(tmp_path):
    rng = np.random.default_rng(42)

    # Düz boyalı (anime/pixar tarzı) klip
    flat_path = str(tmp_path / "flat_anime.mp4")
    w = cv2.VideoWriter(flat_path, cv2.VideoWriter_fourcc(*"mp4v"), FPS, (320, 180))
    for i in range(24):
        img = np.full((180, 320, 3), (180, 120, 80), np.uint8)
        cv2.rectangle(img, (40 + i, 30), (180 + i, 150), (60, 190, 240), -1)
        cv2.circle(img, (240, 90), 40, (240, 240, 250), -1)
        w.write(img)
    w.release()

    # Yüksek frekanslı mikro-doku / sensör gürültüsü baskın (fotoğrafa kaymış) klip
    noisy_path = str(tmp_path / "noisy_photo.mp4")
    w = cv2.VideoWriter(noisy_path, cv2.VideoWriter_fourcc(*"mp4v"), FPS, (320, 180))
    for i in range(24):
        noise = rng.integers(20, 235, size=(180, 320, 3), dtype=np.uint8)
        w.write(noise)
    w.release()

    sc_flat = qa.style_check(flat_path, style="anime")
    assert sc_flat["stil"] == "anime" and not sc_flat["kayma"] and sc_flat["duz_oran"] > 0.5

    r_noisy = qa.check(noisy_path, "A moving watercolor painting.", style="watercolour")
    sc_noisy = r_noisy["stil_kontrol"]
    assert sc_noisy["kayma"] and sc_noisy["mikro_doku"] > 0.55 and sc_noisy["duz_oran"] < 0.12
    assert "stil kayması" in qa.summary(r_noisy)

    # Gerçek dünya stilinde aynı yüksek dokulu klip uyarı üretmez
    sc_real = qa.style_check(noisy_path, style="real")
    assert not sc_real["kayma"] and sc_real["uyari"] is None

    # Pika taslağından (flat_path) H3 finaline (noisy_path) geçerken göreceli stil kayması tespiti
    sc_rel = qa.style_check(noisy_path, style="pixar", ref_source=flat_path)
    assert sc_rel["kayma"] and sc_rel["taslaktan_kayma"]


def test_audio_check_speech_band(tmp_path):
    import subprocess

    # 1. Konuşma bandında (800 Hz, 300–3400 Hz içinde) ses + Türkçe replik prompt'u
    speech_vid = str(tmp_path / "speech_ok.mp4")
    subprocess.run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", "color=c=black:s=320x180:r=24:d=2",
        "-f", "lavfi", "-i", "sine=frequency=800:sample_rate=16000:duration=2",
        "-af", "volume=-10dB", "-c:v", "libx264", "-c:a", "aac", speech_vid,
    ], check=True)
    r_ok = qa.check(speech_vid, 'She says <d>[Turkish] Merhaba, hoş geldiniz!</d>')
    assert r_ok["ses"]["dolu"] and r_ok["ses"]["konusma_bekleniyor"]
    assert r_ok["ses"]["konusma_orani"] >= 0.90 and r_ok["ses"]["uyari"] is None
    assert "konuşma bandı:" in qa.summary(r_ok)

    # 2. Konuşma bandı dışında (5500 Hz tiz) ses + Türkçe replik prompt'u -> düşük konuşma bandı uyarısı
    non_speech_vid = str(tmp_path / "speech_low.mp4")
    subprocess.run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", "color=c=black:s=320x180:r=24:d=2",
        "-f", "lavfi", "-i", "sine=frequency=5500:sample_rate=16000:duration=2",
        "-af", "volume=-10dB", "-c:v", "libx264", "-c:a", "aac", non_speech_vid,
    ], check=True)
    r_low = qa.check(non_speech_vid, 'Vendor calls <d>[Turkish] Buyurun!</d>')
    assert r_low["ses"]["dolu"] and r_low["ses"]["konusma_orani"] < 0.20
    assert r_low["ses"]["uyari"] and "konuşma bandı enerjisi düşük" in qa.summary(r_low)

    # 3. Ses kanalı olmayan videoda Türkçe konuşma bekleniyorsa uyarı verir
    silent_vid = _clip(str(tmp_path / "no_audio.mp4"), [(24, (50, 50, 50))])
    r_no_aud = qa.check(silent_vid, 'He says <d>[Turkish] Günaydın!</d>')
    assert not r_no_aud["ses"]["var"] and "ses kanalı yok" in qa.summary(r_no_aud)


def test_normalize_lands_on_target_for_short_bursty_speech(tmp_path):
    """Kısa, araları sessiz konuşma: tek geçişli dinamik loudnorm hedefi aşıyordu (Colab: -16,7 → -13,8)."""
    import subprocess
    vid = str(tmp_path / "konusma.mp4")
    # 10 sn: 0,6 sn ses / 0,4 sn sessizlik, -16,7 LUFS civarı
    af = "sine=f=220:d=10,volume='if(lt(mod(t,1),0.6),1,0)':eval=frame,volume=-13dB"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=black:s=64x64:d=10:r=24",
                    "-f", "lavfi", "-i", af, "-shortest", "-c:v", "libx264", "-c:a", "aac", vid], check=True)
    for start in (qa.measure_lufs(vid),):
        before, after = qa.normalize_audio(vid)
        assert before == start
        assert abs(after - (-16.0)) <= 0.7, (before, after)
    # zaten hedefte olan dosya bozulmaz, yüksek dosya kısılır
    _, again = qa.normalize_audio(vid)
    assert abs(again - (-16.0)) <= 0.7
