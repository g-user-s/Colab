"""Yeni video sihirbazı: fikir → (tek) senaryo / (uzun) kart → görseller → plan → onay → üretim."""

import json
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (QComboBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPlainTextEdit,
                               QPushButton, QSpinBox, QStackedWidget, QVBoxLayout, QWidget)

from . import arka
from .kart_duzenleyici import GorselPaneli, KartDuzenleyici, kart_yaz
from .ortak_ui import aciklama, baslik, gunluk_kutusu, hata

STILLER = [("real", "Gerçek dünya"), ("anime", "Anime"), ("pixar", "3D animasyon"), ("watercolour", "Suluboya")]
YONTEMLER = [("pika", "Pika H3 Flex (önerilen, hızlı)"), ("turbo", "MiniMax-H3 Turbo (en hızlı, ölçülmedi)"),
             ("h3", "MiniMax-H3 (en yavaş, ~3 kat)")]
COZUNURLUK = [("yatay", "16:9 yatay · 1344×768"), ("dikey", "9:16 dikey · 768×1344"), ("kare", "1:1 kare · 1024×1024")]
ESIK = [("yuksek", "Yalnızca yüksek önemde kusur (varsayılan)"), ("orta", "Orta kusurlar da (daha temiz, ~2 kat CCU)")]

SAYFA_FORM, SAYFA_TEK, SAYFA_KART, SAYFA_GORSEL = range(4)


def _combo(secenekler):
    c = QComboBox()
    for k, ad in secenekler:
        c.addItem(ad, k)
    return c


class YeniVideo(QWidget):
    uretim_basladi = Signal(str)       # oturum klasörü

    def __init__(self, ayar, bakiye_al=None, parent=None):
        super().__init__(parent)
        self.ayar = ayar
        self.bakiye_al = bakiye_al
        self.klasor = None
        self.komut = None
        ly = QVBoxLayout(self)
        self.yigin = QStackedWidget()
        ly.addWidget(self.yigin, 1)
        self.log = gunluk_kutusu(110)
        ly.addWidget(self.log)
        self._form()
        self._tek_sayfa()
        self._kart_sayfa()
        self._gorsel_sayfa()

    # ---------- sayfalar
    def _form(self):
        w = QWidget()
        ly = QVBoxLayout(w)
        ly.addWidget(baslik("Yeni video"))
        ly.addWidget(aciklama("Fikri kısa ve net yaz: kim, nerede, ne yapıyor, ekranda nerede duruyor. Türkçe replikleri "
                              "çift tırnak içinde, harfi harfine yaz. Kamera, ışık ve sesi de söyleyebilirsin."))
        f = QFormLayout()
        self.ad = QLineEdit()
        self.ad.setPlaceholderText("ör. sahaf_haritasi")
        self.fikir = QPlainTextEdit()
        self.fikir.setPlaceholderText('Yağmurlu bir öğleden sonra, eski bir sahaf dükkânı… Kız: "Eski haritalarınız var mı?"')
        self.tur = _combo([("tek", "Tek video (4–15 sn)"), ("uzun", "Uzun video (16–60 sn, karakter görselleriyle)")])
        self.tur.currentIndexChanged.connect(self._tur_degisti)
        self.sure = QSpinBox()
        self.stil = _combo(STILLER)
        self.yontem = _combo(YONTEMLER)
        self.coz = _combo(COZUNURLUK)
        self.seed = QSpinBox()
        self.seed.setRange(0, 999999)
        self.seed.setValue(22)
        self.gpu = QLineEdit(self.ayar.get("gpu", "a100,g4"))
        self.gpu.setToolTip("Denenecek GPU sırası. A100 Pika için G4'ten ucuz ve genelde daha kolay bulunuyor.")
        self.esik = _combo(ESIK)
        f.addRow("Kısa ad", self.ad)
        f.addRow("Fikir", self.fikir)
        f.addRow("Tür", self.tur)
        f.addRow("Süre (sn)", self.sure)
        f.addRow("Stil", self.stil)
        f.addRow("Yöntem", self.yontem)
        f.addRow("Çözünürlük", self.coz)
        f.addRow("Seed", self.seed)
        f.addRow("GPU sırası", self.gpu)
        f.addRow("Yeniden üretim", self.esik)
        ly.addLayout(f)
        alt = QHBoxLayout()
        alt.addStretch()
        self.ileri = QPushButton("Senaryo yaz →")
        self.ileri.clicked.connect(self._baslat)
        alt.addWidget(self.ileri)
        ly.addLayout(alt)
        self.yigin.addWidget(w)
        self._tur_degisti()

    def _tek_sayfa(self):
        w = QWidget()
        ly = QVBoxLayout(w)
        ly.addWidget(baslik("Senaryo"))
        self.tek_bilgi = aciklama("")
        ly.addWidget(self.tek_bilgi)
        ly.addWidget(QLabel("Brief (Gemini'nin yönetmen tarifi; düzenleyip prompt'u yeniden yazdırabilirsin)"))
        self.brief = QPlainTextEdit()
        ly.addWidget(self.brief, 1)
        ly.addWidget(QLabel("H3 prompt'u (üretimde kullanılacak)"))
        self.prompt = QPlainTextEdit()
        self.prompt.setReadOnly(True)
        ly.addWidget(self.prompt, 1)
        alt = QHBoxLayout()
        geri = QPushButton("← Geri")
        geri.clicked.connect(lambda: self.yigin.setCurrentIndex(SAYFA_FORM))
        self.yeniden_yaz = QPushButton("Brief'ten prompt'u yeniden yaz")
        self.yeniden_yaz.clicked.connect(self._prompt_yeniden)
        self.tek_uret = QPushButton("Üret →")
        self.tek_uret.clicked.connect(lambda: self._onay(self.klasor / "senaryo.json"))
        alt.addWidget(geri)
        alt.addStretch()
        alt.addWidget(self.yeniden_yaz)
        alt.addWidget(self.tek_uret)
        ly.addLayout(alt)
        self.yigin.addWidget(w)

    def _kart_sayfa(self):
        w = QWidget()
        ly = QVBoxLayout(w)
        ly.addWidget(baslik("Hikâye kartı"))
        ly.addWidget(aciklama("Bu kart bütün bloklarda aynen kullanılır. Karakterlerin görünüşünü, kıyafetini ve sesini, "
                              "mekânı ve replikleri kontrol et; gerekirse düzelt."))
        self.kart_sorun = aciklama("")
        ly.addWidget(self.kart_sorun)
        self.kart = KartDuzenleyici()
        ly.addWidget(self.kart, 1)
        alt = QHBoxLayout()
        geri = QPushButton("← Geri")
        geri.clicked.connect(lambda: self.yigin.setCurrentIndex(SAYFA_FORM))
        kaydet = QPushButton("Kaydet ve denetle")
        kaydet.clicked.connect(self._kart_kaydet)
        self.gorsele = QPushButton("Görsellere geç →")
        self.gorsele.clicked.connect(self._gorsellere_gec)
        alt.addWidget(geri)
        alt.addStretch()
        alt.addWidget(kaydet)
        alt.addWidget(self.gorsele)
        ly.addLayout(alt)
        self.yigin.addWidget(w)

    def _gorsel_sayfa(self):
        w = QWidget()
        ly = QVBoxLayout(w)
        ly.addWidget(baslik("Karakter ve mekân görselleri"))
        ly.addWidget(aciklama("Her blok bu görsellerle üretilir; videodaki yüzler ve mekân bunlardan gelir. Kontrol et: "
                              "tam boy mu, tek kişi mi, karta uyuyor mu, mekânda insan veya yazı var mı, sonradan "
                              "getirilecek bir nesne şimdiden görünüyor mu?"))
        self.gorseller = GorselPaneli()
        self.gorseller.yeniden.connect(lambda k: self._uzun("gorsel", "--yeniden", k, sonra=self._gorselleri_goster))
        self.gorseller.kendi.connect(lambda k, y: self._uzun("gorsel", "--ref", f"{k}={y}", sonra=self._gorselleri_goster))
        ly.addWidget(self.gorseller, 1)
        alt = QHBoxLayout()
        geri = QPushButton("← Kart")
        geri.clicked.connect(lambda: self.yigin.setCurrentIndex(SAYFA_KART))
        uret = QPushButton("Eksik görselleri üret")
        uret.clicked.connect(lambda: self._uzun("gorsel", sonra=self._gorselleri_goster))
        self.plan_btn = QPushButton("Plan yaz ve üretime geç →")
        self.plan_btn.clicked.connect(self._plan)
        alt.addWidget(geri)
        alt.addStretch()
        alt.addWidget(uret)
        alt.addWidget(self.plan_btn)
        ly.addLayout(alt)
        self.yigin.addWidget(w)

    # ---------- yardımcılar
    def _tur_degisti(self):
        uzun = self.tur.currentData() == "uzun"
        self.sure.setRange(16, 60) if uzun else self.sure.setRange(4, 15)
        self.sure.setValue(30 if uzun else 10)
        self.ileri.setText("Hikâye kartı yaz →" if uzun else "Senaryo yaz →")

    def _calistir(self, komut, sonra):
        if self.komut and self.komut.calisiyor():
            hata(self, "Bir işlem sürüyor; bitmesini bekle.")
            return
        self.setEnabled(False)
        self.log.appendPlainText("$ " + " ".join(Path(x).name if i < 2 else x for i, x in enumerate(map(str, komut))))
        self.komut = arka.Komut(self.ayar, self)
        self.komut.satir.connect(self.log.appendPlainText)
        self.komut.bitti.connect(lambda rc, out: (self.setEnabled(True), sonra(rc, out)))
        self.komut.calistir(komut)

    def _anahtar_args(self):
        return [] if self.ayar.get("sahte") else ["--anahtar", self.ayar["anahtar"]]

    def _uzun(self, alt, *args, sonra):
        self._calistir(arka.muse_komutu(self.ayar, "uzun_senaryo.py", alt, "--dizin", self.klasor, *args,
                                        *self._anahtar_args()), sonra)

    # ---------- akış
    def _baslat(self):
        fikir = self.fikir.toPlainText().strip()
        if not fikir:
            hata(self, "Önce fikri yaz.")
            return
        self.klasor = arka.yeni_is_klasoru(self.ayar, self.ad.text().strip() or fikir[:30])
        (self.klasor / "fikir.txt").write_text(fikir + "\n", encoding="utf-8")
        if self.tur.currentData() == "uzun":
            args = ["kart", "--dizin", self.klasor, "--fikir", fikir, "--sure", self.sure.value(),
                    "--stil", self.stil.currentData(), *self._anahtar_args()]
            if self.ayar.get("sahte"):
                args.append("--sahte")
            self._calistir(arka.muse_komutu(self.ayar, "uzun_senaryo.py", *args), self._kart_geldi)
        else:
            self._senaryo_yaz()

    def _senaryo_yaz(self, brief_dosyasi=None):
        args = ["--fikir", self.fikir.toPlainText().strip(), "--sure", self.sure.value(),
                "--stil", self.stil.currentData(), "--yontem", self.yontem.currentData(),
                "--cozunurluk", self.coz.currentData(), "--seed", self.seed.value(),
                "--cikti", self.klasor / "senaryo.json", *self._anahtar_args()]
        if brief_dosyasi:
            args += ["--brief-dosyasi", brief_dosyasi]
        if self.ayar.get("sahte"):
            args.append("--sahte")
        self._calistir(arka.muse_komutu(self.ayar, "senaryo.py", *args), self._senaryo_geldi)

    def _senaryo_geldi(self, rc, out):
        s = arka.senaryo_oku(self.klasor / "senaryo.json")
        if rc not in (0, 2) or not s:
            hata(self, "Senaryo yazılamadı. Ayrıntı aşağıdaki günlükte.\n\n" + out[-800:])
            return
        self.brief.setPlainText(s.get("brief", ""))
        self.prompt.setPlainText(s.get("prompt", ""))
        bilgi = [f"Modeller: {s.get('modeller') or '-'}"]
        if s.get("yedek_model"):
            bilgi.append(f"⚠️ Yedek modelle yazılan adımlar: {', '.join(s['yedek_model'])} (kalite düşük olabilir).")
        if s.get("sorunlar"):
            bilgi.append("⚠️ Denetim sorunları: " + " | ".join(s["sorunlar"]))
        else:
            bilgi.append("✅ Denetimden geçti.")
        self.tek_bilgi.setText("\n".join(bilgi))
        self.yigin.setCurrentIndex(SAYFA_TEK)

    def _prompt_yeniden(self):
        yol = self.klasor / "brief_duzenlenmis.txt"
        yol.write_text(self.brief.toPlainText().strip() + "\n", encoding="utf-8")
        self._senaryo_yaz(brief_dosyasi=yol)

    def _kart_geldi(self, rc, out):
        yol = self.klasor / "hikaye.json"
        if rc not in (0, 2) or not yol.is_file():
            hata(self, "Hikâye kartı yazılamadı. Ayrıntı aşağıdaki günlükte.\n\n" + out[-800:])
            return
        self._karti_goster()
        self.yigin.setCurrentIndex(SAYFA_KART)

    def _karti_goster(self):
        kart = json.loads((self.klasor / "hikaye.json").read_text(encoding="utf-8"))
        self.kart.yukle(kart)
        model = ((kart.get("_meta") or {}).get("modeller") or {})
        self._kart_sorunlari(kart, model)

    def _kart_sorunlari(self, kart, model=None):
        _, sorunlar = self.kart.denetle()
        satirlar = [f"Kartı yazan: {model}"] if model else []
        satirlar.append(("⚠️ " + " | ".join(sorunlar)) if sorunlar else "✅ Kart denetimden geçti.")
        self.kart_sorun.setText("\n".join(satirlar))
        return sorunlar

    def _kart_kaydet(self):
        kart, sorunlar = self.kart.denetle()
        kart_yaz(self.klasor / "hikaye.json", kart)
        self.kart.kart = kart
        self._kart_sorunlari(kart)
        return not sorunlar

    def _gorsellere_gec(self):
        if not self._kart_kaydet():
            if QMessageBox.question(self, "Kart", "Kartta denetim sorunu var. Yine de devam edilsin mi?") \
                    != QMessageBox.Yes:
                return
        self._gorselleri_goster(0, "")
        self.yigin.setCurrentIndex(SAYFA_GORSEL)
        kart = json.loads((self.klasor / "hikaye.json").read_text(encoding="utf-8"))
        from h3app import hikaye
        if any(not Path(g["dosya"]).is_file() for g in hikaye.gorsel_listesi(kart, str(self.klasor / "gorseller"))):
            self._uzun("gorsel", sonra=self._gorselleri_goster)

    def _gorselleri_goster(self, rc, out):
        if rc not in (0,):
            self.log.appendPlainText("⚠️ Görsel adımı hata verdi; ayrıntı yukarıda.")
        kart = json.loads((self.klasor / "hikaye.json").read_text(encoding="utf-8"))
        self.kart.kart = kart
        self.gorseller.yukle(kart, self.klasor)

    def _plan(self):
        self._uzun("plan", "--kol", "ref", "--yontem", self.yontem.currentData(), "--cozunurluk",
                   self.coz.currentData(), "--seed", self.seed.value(), sonra=self._plan_geldi)

    def _plan_geldi(self, rc, out):
        yol = self.klasor / "uzun_senaryo.json"
        if rc not in (0, 2) or not yol.is_file():
            hata(self, "Plan yazılamadı. Ayrıntı aşağıdaki günlükte.\n\n" + out[-800:])
            return
        self._onay(yol)

    def _onay(self, senaryo_yol):
        s = arka.senaryo_oku(senaryo_yol)
        gpu = "cpu" if self.ayar.get("sahte") else self.gpu.text().strip()
        esik = self.esik.currentData()
        metin = [f"“{s.get('hikaye', {}).get('baslik') or self.ad.text() or 'Video'}” · {s.get('sure')} sn · "
                 f"{'uzun, görsel referanslı' if s.get('tur') == 'uzun' else 'tek video'}",
                 arka.maliyet_metni(s, gpu, esik)]
        if self.bakiye_al:
            metin.append(f"Güncel bakiye: {self.bakiye_al() or '?'}")
        if s.get("yedek_model"):
            metin.append(f"⚠️ Yedek modelle yazılan adımlar: {', '.join(s['yedek_model'])}")
        ek = []
        if s.get("durum") != "hazir":
            metin.append("⚠️ Senaryoda denetim sorunu var: " + " | ".join(s.get("sorunlar") or []))
            ek = ["--sorunlu-kabul"]
        metin.append("\nColab'de GPU açılacak ve CCU harcanacak. Üretim uygulama kapansa da sürer. Başlansın mı?")
        if QMessageBox.question(self, "Üretim onayı", "\n".join(metin)) != QMessageBox.Yes:
            return
        oturum = self.klasor / "oturum"
        args = ["--senaryo", senaryo_yol, "--gpu", gpu, "--yeniden-esik", esik,
                "--aralik", self.ayar.get("aralik", 30), *ek]
        args += ["--anahtar", "" if self.ayar.get("sahte") else self.ayar["anahtar"]]
        arka.uretim_baslat(self.ayar, oturum, "uret", *args)
        self.log.appendPlainText(f"Üretim başladı: {oturum}")
        self.yigin.setCurrentIndex(SAYFA_FORM)
        self.uretim_basladi.emit(str(oturum))
