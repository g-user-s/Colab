"""Üretimler: bütün oturumlar, aşamaları; Aç / Devam / Kapat / Klasör."""

from pathlib import Path

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import (QHBoxLayout, QHeaderView, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem,
                               QVBoxLayout, QWidget)

from . import arka
from .ortak_ui import aciklama, baslik, klasoru_ac


class Uretimler(QWidget):
    ac = Signal(str)

    def __init__(self, ayar, parent=None):
        super().__init__(parent)
        self.ayar = ayar
        self.satirlar = []
        ly = QVBoxLayout(self)
        ly.addWidget(baslik("Üretimler"))
        ly.addWidget(aciklama("“⚠️ yönetici süreç çalışmıyor” görünen bir üretimde Colab runtime'ı açık kalmış olabilir ve "
                              "CCU yakıyor olabilir: Devam ya da Kapat."))
        self.tablo = QTableWidget(0, 5)
        self.tablo.setHorizontalHeaderLabels(["Üretim", "Tür", "Aşama", "GPU", "Video"])
        self.tablo.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.tablo.horizontalHeader().setStretchLastSection(True)
        self.tablo.setSelectionBehavior(QTableWidget.SelectRows)
        self.tablo.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tablo.doubleClicked.connect(lambda _: self._ac())
        ly.addWidget(self.tablo, 1)
        d = QHBoxLayout()
        for ad, f in (("Aç", self._ac), ("Devam", self._devam), ("Kapat (runtime)", self._kapat),
                      ("Klasörü aç", self._klasor), ("Yenile", self.yenile)):
            b = QPushButton(ad)
            b.clicked.connect(f)
            d.addWidget(b)
        d.addStretch()
        ly.addLayout(d)
        self.zaman = QTimer(self)
        self.zaman.timeout.connect(self.yenile)
        self.zaman.start(5000)
        self.yenile()

    def yenile(self):
        secili = self._secili()
        self.satirlar = arka.oturumlar(self.ayar)
        self.tablo.setRowCount(len(self.satirlar))
        for r, (d, o) in enumerate(self.satirlar):
            s = arka.senaryo_oku(o.get("senaryo", "")) if o.get("senaryo") else {}
            tur = "uzun" if s.get("tur") == "uzun" else ("kuru deneme" if s.get("sahte") else "tek")
            video = arka.sonuc_video(d, o)
            for c, deger in enumerate([d.parent.name + ("" if d.name == "oturum" else f" / {d.name}"),
                                       f"{tur} · {s.get('sure', '?')} sn", arka.asama_metni(d, o),
                                       (o.get("gpu") or "-").upper(), Path(video).name if video else "-"]):
                self.tablo.setItem(r, c, QTableWidgetItem(str(deger)))
        if secili:
            for r, (d, _) in enumerate(self.satirlar):
                if d == secili:
                    self.tablo.selectRow(r)

    def _secili(self):
        r = self.tablo.currentRow()
        return self.satirlar[r][0] if 0 <= r < len(self.satirlar) else None

    def _ac(self):
        d = self._secili()
        if d:
            self.ac.emit(str(d))

    def _devam(self):
        d = self._secili()
        if not d:
            return
        o = arka.oturum_oku(d)
        if o.get("asama") == "kapatildi" or arka.surec_canli(d):
            QMessageBox.information(self, "Devam", "Bu üretim bitmiş ya da zaten çalışıyor.")
            return
        arka.uretim_baslat(self.ayar, d, "devam")
        self.ac.emit(str(d))

    def _kapat(self):
        d = self._secili()
        if not d:
            return
        o = arka.oturum_oku(d)
        if not o.get("ad") or o.get("asama") == "kapatildi":
            QMessageBox.information(self, "Kapat", "Bu üretimde açık runtime yok.")
            return
        if QMessageBox.question(self, "Kapat", "Üretim durdurulsun ve Colab runtime'ı kapatılsın mı?") \
                != QMessageBox.Yes:
            return
        arka.uretimi_durdur(d)
        arka.uretim_baslat(self.ayar, d, "kapat")
        self.ac.emit(str(d))

    def _klasor(self):
        d = self._secili()
        if d:
            klasoru_ac(d.parent)
