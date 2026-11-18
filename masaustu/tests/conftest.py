import os
import subprocess
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK / "masaustu"))
EKRAN = Path(os.environ.get("H3STUDYO_EKRAN", "/tmp/h3studyo_ekran"))


@pytest.fixture
def uygulama_ortami(tmp_path, monkeypatch):
    """Sahte colab + sahte mod ayarları; uygulamanın alt süreçleri bu ortamı devralır."""
    video = tmp_path / "ornek.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc=size=320x184:rate=24:duration=5",
                    "-f", "lavfi", "-i", "sine=frequency=440:duration=5", "-shortest", "-c:v", "libx264",
                    "-pix_fmt", "yuv420p", "-c:a", "aac", str(video)], check=True)
    runtime = tmp_path / "runtime"
    (runtime / "content" / "h3muse").mkdir(parents=True)
    colab = tmp_path / "colab"
    colab.write_text(f"#!/bin/sh\nexec {sys.executable} {KOK / 'tests' / 'sahte_colab.py'} \"$@\"\n")
    colab.chmod(0o755)
    for k, v in {"SAHTE_KOK": str(runtime), "SAHTE_PYTHON": sys.executable, "H3APP_FAKE_VIDEO": str(video),
                 "H3MUSE_BEKLE_SN": "0", "H3MUSE_TEKRAR_SN": "0", "SAHTE_PLAN": "cpu:ok",
                 "H3APP_WORK_DIR": str(tmp_path / "yerel_cache")}.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setenv("H3STUDYO_AYAR", str(tmp_path / "ayar.json"))
    from h3studyo import arka
    monkeypatch.setattr(arka, "AYAR_YOLU", tmp_path / "ayar.json")
    ayar = arka.Ayarlar()
    ayar.update(uretim_dizini=str(tmp_path / "uretimler"), python=sys.executable, colab=str(colab), sahte=True,
                aralik=1, anahtar=str(tmp_path / "yok.key"))
    ayar.kaydet()
    EKRAN.mkdir(parents=True, exist_ok=True)
    return {"ayar": ayar, "tmp": tmp_path, "runtime": runtime}


@pytest.fixture(autouse=True)
def onaylari_evet(monkeypatch):
    from PySide6.QtWidgets import QMessageBox
    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.Yes))
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: QMessageBox.Ok))
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: QMessageBox.Ok))
