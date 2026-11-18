"""Colab'e ilk giriş: CLI'nın verdiği Google bağlantısı açılır, onaydan sonra gösterilen kod buraya yapıştırılır."""

import re

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout)

from . import arka
from .ortak_ui import aciklama, baslik, gunluk_kutusu

URL_RE = re.compile(r"https://accounts\.google\.com/\S+")


class GirisPenceresi(QDialog):
    def __init__(self, ayar, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Colab'e giriş")
        self.resize(640, 420)
        self.ayar = ayar
        self.url = None
        self.basarili = False
        ly = QVBoxLayout(self)
        ly.addWidget(baslik("Google Colab'e giriş"))
        ly.addWidget(aciklama(
            "1) “Tarayıcıda aç” ile Google sayfasını aç ve Colab'e izin ver.\n"
            "2) Google'ın gösterdiği kodu kopyala, aşağıya yapıştır, “Gönder”e bas.\n"
            "Bu bir kez yapılır; sonraki açılışlarda sorulmaz."))
        self.durum = QLabel("Bağlantı hazırlanıyor…")
        self.durum.setWordWrap(True)
        ly.addWidget(self.durum)
        sat = QHBoxLayout()
        self.ac = QPushButton("Tarayıcıda aç")
        self.ac.setEnabled(False)
        self.ac.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(self.url)))
        sat.addWidget(self.ac)
        sat.addStretch()
        ly.addLayout(sat)
        sat2 = QHBoxLayout()
        self.kod = QLineEdit()
        self.kod.setPlaceholderText("Google'ın verdiği kod")
        self.gonder = QPushButton("Gönder")
        self.gonder.setEnabled(False)
        self.gonder.clicked.connect(self._gonder)
        sat2.addWidget(self.kod)
        sat2.addWidget(self.gonder)
        ly.addLayout(sat2)
        self.log = gunluk_kutusu(120)
        ly.addWidget(self.log)
        self.kapat = QPushButton("Kapat")
        self.kapat.clicked.connect(self.reject)
        ly.addWidget(self.kapat)
        self.komut = arka.Komut(ayar, self)
        self.komut.satir.connect(self._satir)
        self.komut.bitti.connect(self._bitti)
        self.komut.calistir(arka.colab_komutu(ayar, "whoami"))

    def _satir(self, s):
        self.log.appendPlainText(s)
        m = URL_RE.search(s)
        if m and not self.url:
            self.url = m.group(0)
            self.ac.setEnabled(True)
            self.gonder.setEnabled(True)
            self.durum.setText("Bağlantı hazır. Tarayıcıda aç, izin ver, kodu yapıştır.")

    def _gonder(self):
        kod = self.kod.text().strip()
        if not kod:
            return
        self.komut.yaz(kod + "\n")
        self.gonder.setEnabled(False)
        self.durum.setText("Kod gönderildi, doğrulanıyor…")

    def _bitti(self, rc, cikti):
        if rc == 0 and "Auth provider" in cikti:
            self.basarili = True
            self.durum.setText("✅ Giriş tamam.")
            self.kapat.setText("Tamam")
        else:
            self.durum.setText(f"❌ Giriş tamamlanmadı (kod {rc}). Ayrıntı aşağıda; tekrar deneyebilirsin.")

    def reject(self):
        self.komut.durdur()
        super().reject()
