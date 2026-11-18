"""Uzun video: hikâye kartı düzenleyici ve karakter/mekân görselleri paneli."""

import json
import os
import sys
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QFileDialog, QFormLayout, QGridLayout, QGroupBox, QHBoxLayout, QHeaderView, QLabel,
                               QLineEdit, QPlainTextEdit, QPushButton, QScrollArea, QTableWidget, QTableWidgetItem,
                               QVBoxLayout, QWidget)

from . import arka

if str(arka.REPO / "h3") not in sys.path:
    sys.path.insert(0, str(arka.REPO / "h3"))

KARAKTER_SUTUN = [("id", "Kimlik"), ("ad", "Ad"), ("konusmaci", "Konuşmacı"), ("gorunum", "Görünüş (İngilizce)"),
                  ("kiyafet", "Kıyafet (İngilizce)"), ("ses", "Ses (İngilizce)")]


def _tablo(sutunlar):
    t = QTableWidget(0, len(sutunlar))
    t.setHorizontalHeaderLabels(sutunlar)
    t.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
    t.horizontalHeader().setStretchLastSection(True)
    t.verticalHeader().setVisible(False)
    t.setWordWrap(True)
    return t


def _hucre(t, r, c, deger):
    t.setItem(r, c, QTableWidgetItem("" if deger is None else str(deger)))


def _oku(t, r, c):
    it = t.item(r, c)
    return it.text().strip() if it else ""


class KartDuzenleyici(QWidget):
    """hikaye.json'u tablolarla düzenler. Görünüş/kıyafet/ses İngilizce (H3 prompt'una girer), replikler Türkçe."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.kart = {}
        ly = QVBoxLayout(self)
        ust = QFormLayout()
        self.baslik = QLineEdit()
        ust.addRow("Başlık", self.baslik)
        ly.addLayout(ust)

        kg = QGroupBox("Karakterler (konuşanlar S1, S2… sırasıyla; görsel sırası buna göre)")
        kl = QVBoxLayout(kg)
        self.karakterler = _tablo([b for _, b in KARAKTER_SUTUN])
        self.karakterler.setMinimumHeight(120)
        kl.addWidget(self.karakterler)
        ly.addWidget(kg)

        mg = QGroupBox("Mekân (hikâye başlamadan önceki hâli; sonradan getirilen nesne burada olmaz)")
        ml = QFormLayout(mg)
        self.mekan_ad = QLineEdit()
        self.mekan_tarif = QPlainTextEdit()
        self.mekan_tarif.setMaximumHeight(80)
        self.zaman = QLineEdit()
        self.palet = QLineEdit()
        ml.addRow("Ad", self.mekan_ad)
        ml.addRow("Tarif", self.mekan_tarif)
        ml.addRow("Zaman ve ışık", self.zaman)
        ml.addRow("Renk paleti", self.palet)
        ly.addWidget(mg)

        bg = QGroupBox("Bloklar ve replikler (replik metni harfi harfine Türkçe)")
        bl = QHBoxLayout(bg)
        self.bloklar = _tablo(["Blok", "Süre (sn)", "Ne oluyor (İngilizce)"])
        self.replikler = _tablo(["Blok", "Konuşmacı", "Replik"])
        for t in (self.bloklar, self.replikler):
            t.setMinimumHeight(140)
        sag = QVBoxLayout()
        sag.addWidget(self.replikler)
        rb = QHBoxLayout()
        ekle = QPushButton("Replik ekle")
        ekle.clicked.connect(lambda: self.replikler.insertRow(self.replikler.rowCount()))
        sil = QPushButton("Seçili repliği sil")
        sil.clicked.connect(lambda: self.replikler.removeRow(self.replikler.currentRow())
                            if self.replikler.currentRow() >= 0 else None)
        rb.addWidget(ekle)
        rb.addWidget(sil)
        rb.addStretch()
        sag.addLayout(rb)
        bl.addWidget(self.bloklar, 3)
        bl.addLayout(sag, 2)
        ly.addWidget(bg)

    def yukle(self, kart):
        self.kart = kart
        self.baslik.setText(kart.get("baslik", ""))
        k = kart.get("karakterler") or []
        self.karakterler.setRowCount(len(k))
        for r, kar in enumerate(k):
            for c, (alan, _) in enumerate(KARAKTER_SUTUN):
                _hucre(self.karakterler, r, c, kar.get(alan, ""))
        m = kart.get("mekan") or {}
        self.mekan_ad.setText(m.get("ad", ""))
        self.mekan_tarif.setPlainText(m.get("tarif", ""))
        self.zaman.setText(kart.get("zaman_isik", ""))
        self.palet.setText(kart.get("renk_paleti", ""))
        b = kart.get("bloklar") or []
        self.bloklar.setRowCount(len(b))
        rep = []
        for r, blok in enumerate(b):
            _hucre(self.bloklar, r, 0, blok.get("blok", r + 1))
            _hucre(self.bloklar, r, 1, blok.get("sure", 15))
            _hucre(self.bloklar, r, 2, blok.get("ozet", ""))
            rep += [(blok.get("blok", r + 1), x.get("konusmaci", ""), x.get("metin", ""))
                    for x in blok.get("replikler") or []]
        self.replikler.setRowCount(len(rep))
        for r, (n, s, m_) in enumerate(rep):
            _hucre(self.replikler, r, 0, n)
            _hucre(self.replikler, r, 1, s)
            _hucre(self.replikler, r, 2, m_)
        self.karakterler.resizeColumnsToContents()
        for t, sutun in ((self.karakterler, 3), (self.bloklar, 2)):
            t.setColumnWidth(sutun, 280)
            t.resizeRowsToContents()

    def kart_al(self):
        """Tablolardaki hâliyle kart (meta alanları korunur)."""
        kart = dict(self.kart)
        kart["baslik"] = self.baslik.text().strip()
        kart["karakterler"] = [{alan: _oku(self.karakterler, r, c) for c, (alan, _) in enumerate(KARAKTER_SUTUN)}
                               for r in range(self.karakterler.rowCount())]
        kart["mekan"] = {"ad": self.mekan_ad.text().strip(), "tarif": self.mekan_tarif.toPlainText().strip()}
        kart["zaman_isik"] = self.zaman.text().strip()
        kart["renk_paleti"] = self.palet.text().strip()
        bloklar = []
        for r in range(self.bloklar.rowCount()):
            try:
                n, sure = int(_oku(self.bloklar, r, 0)), int(_oku(self.bloklar, r, 1))
            except ValueError:
                n, sure = r + 1, 0
            bloklar.append({"blok": n, "sure": sure, "ozet": _oku(self.bloklar, r, 2), "replikler": []})
        for r in range(self.replikler.rowCount()):
            try:
                n = int(_oku(self.replikler, r, 0))
            except ValueError:
                continue
            for b in bloklar:
                if b["blok"] == n and _oku(self.replikler, r, 2):
                    b["replikler"].append({"konusmaci": _oku(self.replikler, r, 1), "metin": _oku(self.replikler, r, 2)})
        kart["bloklar"] = bloklar
        return kart

    def denetle(self):
        from h3app import hikaye
        kart = self.kart_al()
        meta = kart.get("_meta") or {}
        return kart, hikaye.kart_denetle(kart, meta.get("sure", sum(b["sure"] for b in kart["bloklar"])),
                                         meta.get("fikir", ""))


class GorselPaneli(QWidget):
    """Karakter ve mekân referans görselleri: önizleme, yeniden üret, kendi görselini ver."""
    yeniden = Signal(str)            # görsel kimliği
    kendi = Signal(str, str)         # kimlik, dosya yolu

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ly = QVBoxLayout(self)
        self.alan = QScrollArea()
        self.alan.setWidgetResizable(True)
        self.ic = QWidget()
        self.izgara = QGridLayout(self.ic)
        self.alan.setWidget(self.ic)
        self.ly.addWidget(self.alan)
        self.gorunen = 0

    def yukle(self, kart, dizin):
        from h3app import hikaye
        while self.izgara.count():
            w = self.izgara.takeAt(0).widget()
            if w:
                w.deleteLater()
        self.gorunen = 0
        for i, g in enumerate(hikaye.gorsel_listesi(kart, str(Path(dizin) / "gorseller"))):
            kutu = QGroupBox(f"{g['id']} · {g['ad']} ({'mekân' if g['rol'] != 'karakter' else 'karakter'})")
            kl = QVBoxLayout(kutu)
            resim = QLabel()
            resim.setAlignment(Qt.AlignCenter)
            resim.setMinimumSize(300, 170)
            if os.path.isfile(g["dosya"]):
                resim.setPixmap(QPixmap(g["dosya"]).scaled(300, 170, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                self.gorunen += 1
                kaynak = (kart.get("_gorseller") or {}).get(g["id"], "")
                alt = QLabel(f"kaynak: {kaynak}")
            else:
                resim.setText("(henüz yok)")
                alt = QLabel("")
            kl.addWidget(resim)
            kl.addWidget(alt)
            bl = QHBoxLayout()
            y = QPushButton("Yeniden üret")
            y.clicked.connect(lambda _=False, k=g["id"]: self.yeniden.emit(k))
            d = QPushButton("Kendi görselim…")
            d.clicked.connect(lambda _=False, k=g["id"]: self._dosya_sec(k))
            bl.addWidget(y)
            bl.addWidget(d)
            kl.addLayout(bl)
            self.izgara.addWidget(kutu, i // 3, i % 3)

    def _dosya_sec(self, kimlik):
        yol, _ = QFileDialog.getOpenFileName(self, f"{kimlik} için PNG görsel", str(Path.home()), "PNG (*.png)")
        if yol:
            self.kendi.emit(kimlik, yol)


def kart_yaz(yol, kart):
    Path(yol).write_text(json.dumps(kart, ensure_ascii=False, indent=2), encoding="utf-8")
