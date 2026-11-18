"""Üretimi izleme ve sonuç: aşama, canlı günlük, Devam/Kapat; bitince video, rapor, izleme kusurları."""

import json
import os
import time
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QMessageBox, QPushButton, QSplitter, QTextBrowser, QVBoxLayout,
                               QWidget)

from . import arka
from .ortak_ui import aciklama, baslik, gunluk_kutusu, klasoru_ac

try:
    from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
    from PySide6.QtMultimediaWidgets import QVideoWidget
    OYNATICI = True
except Exception:  # noqa: BLE001 - PySide6-Addons yoksa sistem oynatıcısı kullanılır
    OYNATICI = False

ONEM = {"high": "yüksek", "medium": "orta", "low": "düşük"}


class SonucPaneli(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.video = None
        ly = QVBoxLayout(self)
        if OYNATICI:
            self.ekran = QVideoWidget()
            self.ekran.setMinimumHeight(260)
            self.oynatici = QMediaPlayer(self)
            self.ses = QAudioOutput(self)
            self.oynatici.setAudioOutput(self.ses)
            self.oynatici.setVideoOutput(self.ekran)
            ly.addWidget(self.ekran, 3)
        else:
            self.oynatici = None
            ly.addWidget(aciklama("Uygulama içi oynatıcı yok (PySide6-Addons kurulu değil); “Sistem oynatıcısında aç”."))
        dugmeler = QHBoxLayout()
        self.oynat = QPushButton("Oynat / Duraklat")
        self.oynat.clicked.connect(self._oynat)
        self.oynat.setEnabled(OYNATICI)
        dis = QPushButton("Sistem oynatıcısında aç")
        dis.clicked.connect(lambda: self.video and QDesktopServices.openUrl(QUrl.fromLocalFile(self.video)))
        self.klasor_btn = QPushButton("Çıktı klasörünü aç")
        self._cikti = None
        self.klasor_btn.clicked.connect(lambda: self._cikti and klasoru_ac(self._cikti))
        dugmeler.addWidget(self.oynat)
        dugmeler.addWidget(dis)
        dugmeler.addStretch()
        dugmeler.addWidget(self.klasor_btn)
        ly.addLayout(dugmeler)
        self.rapor = QTextBrowser()
        self.rapor.setOpenExternalLinks(True)
        ly.addWidget(self.rapor, 2)

    def goster(self, oturum_dizini, o):
        self.video = arka.sonuc_video(oturum_dizini, o)
        self._cikti = Path(oturum_dizini) / "cikti"
        if self.oynatici and self.video:
            self.oynatici.setSource(QUrl.fromLocalFile(self.video))
        md = []
        rapor = Path(oturum_dizini) / "rapor.md"
        if rapor.is_file():
            md.append(rapor.read_text(encoding="utf-8"))
        inc = o.get("incelemeler") or {}
        if inc:
            md.append("\n## Gemini izlemesi (aday başına)\n")
            for ad, r in inc.items():
                if not r:
                    md.append(f"- **{ad}**: izlenemedi")
                    continue
                md.append(f"- **{ad}** ({r.get('model', '')}): {len(r.get('defects') or [])} kusur")
                for d in r.get("defects") or []:
                    md.append(f"  - [{d.get('start_s')}–{d.get('end_s')} sn, {ONEM.get(d.get('severity'), '?')}] "
                              f"{d.get('description', '')}")
        self.rapor.setMarkdown("\n".join(md) or "Rapor yok.")

    def _oynat(self):
        if not self.oynatici:
            return
        if self.oynatici.playbackState() == QMediaPlayer.PlayingState:
            self.oynatici.pause()
        else:
            self.oynatici.play()

    def durdur(self):
        if self.oynatici:
            self.oynatici.stop()


class Izleme(QWidget):
    def __init__(self, ayar, parent=None):
        super().__init__(parent)
        self.ayar = ayar
        self.dizin = None
        self._son_satir = 0
        self._sonuc_gosterildi = False
        ly = QVBoxLayout(self)
        self.baslik = baslik("Üretim")
        ly.addWidget(self.baslik)
        self.asama = QLabel("Henüz izlenen üretim yok. Yeni video başlat ya da Üretimler'den birini aç.")
        self.asama.setWordWrap(True)
        ly.addWidget(self.asama)
        self.bilgi = aciklama("")
        ly.addWidget(self.bilgi)
        d = QHBoxLayout()
        self.devam = QPushButton("Devam (kaldığı yerden)")
        self.devam.clicked.connect(self._devam)
        self.kapat = QPushButton("Durdur ve runtime'ı kapat")
        self.kapat.clicked.connect(self._kapat)
        self.klasor = QPushButton("Klasörü aç")
        self.klasor.clicked.connect(lambda: self.dizin and klasoru_ac(Path(self.dizin).parent))
        for b in (self.devam, self.kapat):
            b.setEnabled(False)
        d.addWidget(self.devam)
        d.addWidget(self.kapat)
        d.addStretch()
        d.addWidget(self.klasor)
        ly.addLayout(d)
        bol = QSplitter(Qt.Vertical)
        self.log = gunluk_kutusu(160)
        self.sonuc = SonucPaneli()
        self.sonuc.hide()
        bol.addWidget(self.sonuc)
        bol.addWidget(self.log)
        ly.addWidget(bol, 1)
        self.zaman = QTimer(self)
        self.zaman.timeout.connect(self.tazele)
        self.zaman.start(2000)

    def ac(self, oturum_dizini):
        self.dizin = str(oturum_dizini)
        self._son_satir = 0
        self._sonuc_gosterildi = False
        self.log.clear()
        self.sonuc.durdur()
        self.sonuc.hide()
        self.baslik.setText(f"Üretim · {Path(self.dizin).parent.name}")
        self.tazele()

    def tazele(self):
        if not self.dizin:
            return
        o = arka.oturum_oku(self.dizin)
        satirlar = arka.gunluk_son(self.dizin, 100000)
        for s in satirlar[self._son_satir:]:
            self.log.appendPlainText(s)
        self._son_satir = len(satirlar)
        canli = arka.surec_canli(self.dizin)
        bitti = o.get("asama") == "kapatildi"
        self.asama.setText(("✅ " if bitti and o.get("video") else "") + arka.asama_metni(self.dizin, o)
                           if o else ("Başlıyor…" if canli else "Oturum bulunamadı."))
        bilgi = []
        if o.get("gpu"):
            bilgi.append(f"GPU: {o['gpu'].upper()} {o.get('gpu_adi') or ''}")
        if o.get("acilis"):
            son = o.get("kapanis") or time.time()
            dk = (son - o["acilis"]) / 60
            oran = arka.ortak.ORANLAR.get(o.get("gpu"))
            bilgi.append(f"açık kalma: {dk:.1f} dk" + (f" · ~{dk / 60 * oran:.2f} CCU" if oran else ""))
        if o.get("isler"):
            bilgi.append(f"GPU işi: {len(o['isler'])} · izlenen video: {len(o.get('incelemeler') or {})}")
        self.bilgi.setText(" · ".join(bilgi))
        self.devam.setEnabled(bool(o) and not bitti and not canli)
        self.kapat.setEnabled(bool(o.get("ad")) and not bitti)
        if bitti and not self._sonuc_gosterildi:
            self._sonuc_gosterildi = True
            self.sonuc.goster(self.dizin, o)
            self.sonuc.show()

    def _devam(self):
        arka.uretim_baslat(self.ayar, self.dizin, "devam")
        self.tazele()

    def _kapat(self):
        if QMessageBox.question(self, "Durdur", "Üretim durdurulsun ve Colab runtime'ı kapatılsın mı? "
                                "O ana kadar inen dosyalar kalır.") != QMessageBox.Yes:
            return
        arka.uretimi_durdur(self.dizin)
        arka.uretim_baslat(self.ayar, self.dizin, "kapat")
        self.tazele()
