"""Ekranların ortak küçük parçaları."""

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices, QFont
from PySide6.QtWidgets import QLabel, QMessageBox, QPlainTextEdit


def gunluk_kutusu(yukseklik=140):
    k = QPlainTextEdit()
    k.setReadOnly(True)
    k.setMaximumBlockCount(4000)
    f = QFont("monospace")
    f.setStyleHint(QFont.Monospace)
    f.setPointSize(9)
    k.setFont(f)
    k.setMinimumHeight(yukseklik)
    return k


def baslik(metin):
    l = QLabel(metin)
    f = l.font()
    f.setPointSize(f.pointSize() + 3)
    f.setBold(True)
    l.setFont(f)
    return l


def aciklama(metin):
    l = QLabel(metin)
    l.setWordWrap(True)
    l.setStyleSheet("color: palette(mid);")
    return l


def klasoru_ac(yol):
    QDesktopServices.openUrl(QUrl.fromLocalFile(str(yol)))


def hata(parent, metin):
    QMessageBox.warning(parent, "H3 Stüdyo", metin)
