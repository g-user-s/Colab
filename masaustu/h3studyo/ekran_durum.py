"""Durum ve kurulum: Colab girişi, 411 yaması, Gemini anahtarı, ffmpeg, CCU bakiyesi, kuru deneme."""

import os
import re
import shutil
from pathlib import Path

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import (QCheckBox, QFileDialog, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
                               QPushButton, QVBoxLayout, QWidget)

from . import arka
from .giris_penceresi import GirisPenceresi
from .ortak_ui import aciklama, baslik, gunluk_kutusu

TAMAM, YOK, BEKLE = "✅", "❌", "⏳"


class DurumEkrani(QWidget):
    izle = Signal(str)          # kuru deneme başlayınca oturum klasörü

    def __init__(self, ayar, parent=None):
        super().__init__(parent)
        self.ayar = ayar
        self.komutlar = []
        ly = QVBoxLayout(self)
        ly.addWidget(baslik("Durum ve kurulum"))
        ly.addWidget(aciklama("Üretimden önce burada her satır ✅ olmalı. GPU işi Colab'de yapılır; bu bilgisayarda "
                              "yalnızca senaryo, Gemini izlemesi ve indirme çalışır."))
        g = QGridLayout()
        self.etiket = {}
        satirlar = [("giris", "Colab girişi"), ("yama", "Colab CLI 411 yaması"), ("anahtar", "Gemini anahtarı"),
                    ("ffmpeg", "ffmpeg / ffprobe"), ("bakiye", "CCU bakiyesi"), ("oturumlar", "Sunucudaki oturumlar")]
        for i, (k, ad) in enumerate(satirlar):
            g.addWidget(QLabel(ad), i, 0)
            self.etiket[k] = QLabel(BEKLE)
            self.etiket[k].setWordWrap(True)
            g.addWidget(self.etiket[k], i, 1)
        self.giris_btn = QPushButton("Giriş yap…")
        self.giris_btn.clicked.connect(self._giris)
        g.addWidget(self.giris_btn, 0, 2)
        self.yama_btn = QPushButton("Yamayı uygula")
        self.yama_btn.clicked.connect(self._yama_uygula)
        g.addWidget(self.yama_btn, 1, 2)
        anahtar_ly = QHBoxLayout()
        self.anahtar_kutu = QLineEdit()
        self.anahtar_kutu.setEchoMode(QLineEdit.Password)
        self.anahtar_kutu.setPlaceholderText("Google AI Studio'dan API anahtarı")
        self.anahtar_kutu.setMinimumWidth(320)
        kaydet = QPushButton("Kaydet")
        kaydet.clicked.connect(self._anahtar_kaydet)
        dene = QPushButton("Dene")
        dene.clicked.connect(self._anahtar_dene)
        anahtar_ly.addWidget(self.anahtar_kutu)
        anahtar_ly.addWidget(kaydet)
        anahtar_ly.addWidget(dene)
        w = QWidget()
        w.setLayout(anahtar_ly)
        g.addWidget(w, 2, 2)
        g.setColumnStretch(1, 1)
        ly.addLayout(g)

        ayar_ly = QHBoxLayout()
        self.klasor = QLabel()
        degistir = QPushButton("Üretim klasörü…")
        degistir.clicked.connect(self._klasor_sec)
        self.duz = QCheckBox("Sistem anahtarlığı yok (Colab girişini düz dosyada sakla)")
        self.duz.setChecked(bool(ayar.get("duz_anahtarlik")))
        self.duz.toggled.connect(self._duz_degisti)
        ayar_ly.addWidget(degistir)
        ayar_ly.addWidget(self.klasor, 1)
        ly.addLayout(ayar_ly)
        ly.addWidget(self.duz)

        alt = QHBoxLayout()
        yenile = QPushButton("Yenile")
        yenile.clicked.connect(self.yenile)
        self.kuru = QPushButton("Kuru deneme (CPU, sahte video, ~0,01 CCU)")
        self.kuru.clicked.connect(self._kuru_deneme)
        alt.addWidget(yenile)
        alt.addStretch()
        alt.addWidget(self.kuru)
        ly.addLayout(alt)
        self.log = gunluk_kutusu(140)
        ly.addWidget(self.log)
        self._klasor_yaz()
        QTimer.singleShot(0, self.yenile)

    # ---- yardımcılar
    def _calistir(self, komut, bitince, satir=None):
        k = arka.Komut(self.ayar, self)
        k.bitti.connect(lambda rc, out, k=k: (bitince(rc, out), self.komutlar.remove(k) if k in self.komutlar else None))
        if satir:
            k.satir.connect(satir)
        self.komutlar.append(k)
        k.calistir(komut)
        return k

    def _yaz(self, k, durum, metin):
        self.etiket[k].setText(f"{durum} {metin}")

    def _klasor_yaz(self):
        self.klasor.setText(str(self.ayar.kok))

    # ---- kontroller
    def yenile(self):
        for k in self.etiket:
            self._yaz(k, BEKLE, "")
        self._giris_kontrol()
        self._calistir(arka.muse_komutu(self.ayar, "yama_411.py", "--kontrol"),
                       lambda rc, out: self._yaz("yama", TAMAM if rc == 0 else YOK,
                                                 "yerinde" if rc == 0 else "yok (Yamayı uygula)"))
        try:
            n = len(arka.ortak.anahtar_oku(self.ayar["anahtar"]))
            self._yaz("anahtar", TAMAM, f"kayıtlı ({n} karakter) · {self.ayar['anahtar']}")
        except SystemExit:
            self._yaz("anahtar", YOK, "yok: anahtarı yapıştırıp Kaydet'e bas")
        eksik = [a for a in ("ffmpeg", "ffprobe") if not shutil.which(a)]
        self._yaz("ffmpeg", YOK if eksik else TAMAM, f"eksik: {', '.join(eksik)} (sudo apt install ffmpeg)" if eksik
                  else "kurulu")
        self._calistir(arka.colab_komutu(self.ayar, "usage"), self._bakiye)
        self._calistir(arka.colab_komutu(self.ayar, "sessions"), self._oturumlar)

    def _giris_kontrol(self):
        """`colab whoami`: giriş yoksa CLI bağlantı basıp kod bekler; o zaman süreci durdurup "giriş yok" deriz."""
        k = arka.Komut(self.ayar, self)

        def satir(s):
            if "accounts.google.com" in s or "authorization code" in s:
                k.durdur()

        def bitti(rc, out):
            if "Auth provider" in out:
                m = re.search(r"Email:\s*(\S+)", out)
                self._yaz("giris", TAMAM, f"giriş yapılmış ({m.group(1) if m else 'hesap görünüyor'})")
            else:
                self._yaz("giris", YOK, "giriş yok: “Giriş yap…”a bas")
            if k in self.komutlar:
                self.komutlar.remove(k)
        k.satir.connect(satir)
        k.bitti.connect(bitti)
        self.komutlar.append(k)
        k.calistir(arka.colab_komutu(self.ayar, "whoami"))
        QTimer.singleShot(30000, k.durdur)

    def _bakiye(self, rc, out):
        b = re.search(r"Current balance:\s*([\d.]+)", out)
        n = re.search(r"Active assignments:\s*(\d+)", out)
        if b:
            self._yaz("bakiye", TAMAM, f"{b.group(1)} CCU · aktif atama: {n.group(1) if n else '?'}")
        else:
            self._yaz("bakiye", YOK, (out.strip().splitlines() or ["okunamadı"])[-1][:160])

    def _oturumlar(self, rc, out):
        if "No active sessions" in out:
            self._yaz("oturumlar", TAMAM, "açık oturum yok")
        elif rc == 0 and out.strip():
            satirlar = [s for s in out.splitlines() if s.strip() and not s.startswith("[colab]")]
            self._yaz("oturumlar", "⚠️", f"{len(satirlar)} açık oturum (CCU yakıyor olabilir): "
                      + "; ".join(satirlar)[:200])
        else:
            self._yaz("oturumlar", YOK, "okunamadı")

    # ---- eylemler
    def _giris(self):
        p = GirisPenceresi(self.ayar, self)
        p.exec()
        self.yenile()

    def _yama_uygula(self):
        self._calistir(arka.muse_komutu(self.ayar, "yama_411.py"),
                       lambda rc, out: (self.log.appendPlainText(out), self.yenile()))

    def _anahtar_kaydet(self):
        deger = self.anahtar_kutu.text().strip()
        if not deger:
            return
        yol = Path(os.path.expanduser(self.ayar["anahtar"]))
        yol.parent.mkdir(parents=True, exist_ok=True)
        os.chmod(yol.parent, 0o700)
        fd = os.open(yol, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(deger + "\n")
        os.chmod(yol, 0o600)
        self.anahtar_kutu.clear()
        self.yenile()

    def _anahtar_dene(self):
        self.log.appendPlainText("Gemini model listesi isteniyor…")
        kod = ("import sys; sys.path.insert(0, 'muse'); import ortak; from senaryo import h3_yukle; "
               "c, pw = h3_yukle(); k = ortak.anahtar_oku(sys.argv[1]); m = pw.gemini_models(k); "
               "print('Gemini erişimi tamam:', len(m), 'model; ilk:', ', '.join(m[:3]))")
        self._calistir([os.path.expanduser(self.ayar["python"]), "-c", kod, self.ayar["anahtar"]],
                       lambda rc, out: self.log.appendPlainText(out if rc == 0 else f"❌ {out[-600:]}"))

    def _klasor_sec(self):
        d = QFileDialog.getExistingDirectory(self, "Üretim klasörü", str(self.ayar.kok))
        if d:
            self.ayar["uretim_dizini"] = d
            self.ayar.kaydet()
            self._klasor_yaz()

    def _duz_degisti(self, v):
        self.ayar["duz_anahtarlik"] = bool(v)
        self.ayar.kaydet()

    def _kuru_deneme(self):
        if QMessageBox.question(self, "Kuru deneme",
                                "Colab'de CPU runtime açılır, sahte bir video üretilip indirilir ve runtime kapatılır. "
                                "Maliyet ~0,01 CCU. Başlansın mı?") != QMessageBox.Yes:
            return
        klasor = arka.yeni_is_klasoru(self.ayar, "kuru_deneme")
        senaryo = klasor / "senaryo.json"

        def bitti(rc, out):
            if rc not in (0, 2) or not senaryo.is_file():
                self.log.appendPlainText(f"❌ Sahte senaryo yazılamadı:\n{out}")
                return
            arka.uretim_baslat(self.ayar, klasor / "oturum", "uret", "--senaryo", senaryo, "--gpu", "cpu",
                               "--anahtar", "", "--aralik", self.ayar.get("aralik", 15), "--sorunlu-kabul")
            self.izle.emit(str(klasor / "oturum"))
        self._calistir(arka.muse_komutu(self.ayar, "senaryo.py", "--fikir", "Kuru deneme", "--sure", 5, "--sahte",
                                        "--cikti", senaryo), bitti, self.log.appendPlainText)
