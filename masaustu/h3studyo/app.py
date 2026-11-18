"""H3 Stüdyo: Colab GPU'sunda H3 Video Stüdyosu ile video üreten Linux masaüstü uygulaması."""

import re
import sys
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox, QTabWidget

from . import arka
from .ekran_durum import DurumEkrani
from .ekran_uretimler import Uretimler
from .ekran_yeni import YeniVideo
from .izleme import Izleme

SIMGE = Path(__file__).resolve().parent / "h3studyo.svg"


class AnaPencere(QMainWindow):
    def __init__(self, ayar=None):
        super().__init__()
        self.ayar = ayar or arka.Ayarlar()
        self.setWindowTitle("H3 Stüdyo")
        if SIMGE.is_file():
            self.setWindowIcon(QIcon(str(SIMGE)))
        self.resize(1100, 820)
        self.sekmeler = QTabWidget()
        self.setCentralWidget(self.sekmeler)
        self.durum = DurumEkrani(self.ayar)
        self.yeni = YeniVideo(self.ayar, bakiye_al=self._bakiye)
        self.izleme = Izleme(self.ayar)
        self.uretimler = Uretimler(self.ayar)
        self.sekmeler.addTab(self.yeni, "Yeni video")
        self.sekmeler.addTab(self.izleme, "Üretim")
        self.sekmeler.addTab(self.uretimler, "Üretimler")
        self.sekmeler.addTab(self.durum, "Durum ve kurulum")
        self.yeni.uretim_basladi.connect(self._izle)
        self.durum.izle.connect(self._izle)
        self.uretimler.ac.connect(self._izle)
        QTimer.singleShot(500, self._acilis_kontrolu)

    def _bakiye(self):
        m = re.search(r"([\d.]+ CCU)", self.durum.etiket["bakiye"].text())
        return m.group(1) if m else None

    def _izle(self, oturum_dizini):
        self.izleme.ac(oturum_dizini)
        self.sekmeler.setCurrentWidget(self.izleme)
        self.uretimler.yenile()

    def _acilis_kontrolu(self):
        acik = [(d, o) for d, o in arka.oturumlar(self.ayar) if arka.acik_kalmis(d, o)]
        if not acik:
            return
        adlar = "\n".join(f"• {d.parent.name} ({arka.asama_metni(d, o)})" for d, o in acik)
        QMessageBox.warning(self, "Bitmemiş üretim",
                            "Bu üretimlerde Colab runtime'ı açık kalmış olabilir ve CCU yakıyor olabilir:\n\n"
                            f"{adlar}\n\nÜretimler sekmesinden Devam ya da Kapat.")
        self.sekmeler.setCurrentWidget(self.uretimler)

    def closeEvent(self, olay):
        calisan = [d for d, o in arka.oturumlar(self.ayar) if arka.surec_canli(d)]
        if calisan:
            QMessageBox.information(self, "H3 Stüdyo", "Süren üretim arka planda devam edecek. Uygulamayı yeniden "
                                    "açınca Üretimler sekmesinden izleyebilirsin.")
        olay.accept()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("H3 Stüdyo")
    app.setDesktopFileName("h3studyo")
    w = AnaPencere()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
