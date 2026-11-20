"""Anahtar kare (FL2VA) yöntemi: grafik, prompt kurma/denetim, kırpma."""
import subprocess

import pytest

from h3app import config, graphs, kare


def test_graf_ilk_ve_son_kare():
    g = graphs.build("pika", "p", 1, 1344, 768, 124, first_frame="a.png", last_frame="b.png")
    assert g["cond"]["class_type"] == "MiniMaxH3ImageToVideo"
    assert g["cond"]["inputs"]["first_frame"] == ["kf_first_frame", 0]
    assert g["cond"]["inputs"]["last_frame"] == ["kf_last_frame", 0]
    assert g["kf_first_frame"]["inputs"]["image"] == "a.png"
    assert g["unet"]["inputs"]["unet_name"] == "minimax_h3_fl2va_pruned_int8_convrot.safetensors"
    assert g["lora"]["inputs"]["lora_name"] == "pika_h3_flex_fl2va_v1_bf16.safetensors"
    g2 = graphs.build("turbo", "p", 1, 1344, 768, 124, first_frame="a.png")
    assert "last_frame" not in g2["cond"]["inputs"] and g2["lora"]["inputs"]["lora_name"].startswith("minimax_h3_fl2v_turbo")
    with pytest.raises(ValueError):
        graphs.build("pika", "p", 1, 1344, 768, 124, ref_images=["r.png"], first_frame="a.png")


def test_hizalama_satiri_rehberdeki_gibi():
    s = kare.hizalama_satiri(8)
    assert s == ("How the reference pictures align with the target video — Picture 1 (from Shot 1) aligns with the "
                 "0.00-second mark of the target video; Picture 2 (from Shot 1) aligns with the 8.00-second mark of "
                 "the target video.")
    assert kare.hizalama_satiri(5, son=False).startswith("For the target video, at 0.00 seconds")
    assert "5.17-second" in kare.hizalama_satiri(5, ilk=False)


def test_prompt_kur_ve_kontrol():
    p = kare.prompt_kur(6, '[Shot 1] Live-action. A man (S1) says: <d>[Turkish] Merhaba.</d>', "Wind.")
    assert kare.kontrol(p, 6, replikler=("Merhaba.",)) == []
    assert any("[Shot 2]" in s for s in kare.kontrol(p.replace("Wind.", "Wind. [Shot 2] At 00:03.000, x."), 6))
    assert any("Replik" in s for s in kare.kontrol(p, 6, replikler=("Yok.",)))
    assert any("aşıyor" in s for s in kare.kontrol(p.replace("Live-action.", "At 00:09.000, x."), 6))
    assert any("kısa" in s for s in kare.kontrol(kare.prompt_kur(4, "[Shot 1] x", "y"), 4))
    assert any("İlk satır" in s for s in kare.kontrol(p.split("\n\n", 1)[1], 6))


def test_hizala_tam_boyut(tmp_path):
    kaynak, hedef = tmp_path / "k.png", tmp_path / "h.png"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc=size=1000x1000", "-frames:v", "1",
                    str(kaynak)], check=True)
    kare.hizala(str(kaynak), str(hedef), 1344, 768)
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=width,height", "-of", "csv=p=0",
                        str(hedef)], capture_output=True, text=True, check=True)
    assert r.stdout.strip() == "1344,768"


def test_kare_metni():
    m = kare.kare_metni("A man stands.", taban=True, kompozisyon=True)
    assert "BASE FRAME" in m and "COMPOSITION" in m and m.rstrip().endswith("A man stands.")
    assert config.STYLES["real"]["kind"] in m
