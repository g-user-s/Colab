"""H3 Stüdyo arayüz testleri: sahte colab ve sahte mod ile uçtan uca (ekransız Qt)."""

import json
import time
from pathlib import Path

from conftest import EKRAN
from h3studyo import arka
from h3studyo.app import AnaPencere
from h3studyo.ekran_yeni import SAYFA_GORSEL, SAYFA_KART, SAYFA_TEK
from h3studyo.giris_penceresi import GirisPenceresi


def _pencere(qtbot, ortam):
    w = AnaPencere(ortam["ayar"])
    qtbot.addWidget(w)
    w.resize(1100, 820)
    w.show()
    return w


def _bitene_kadar(qtbot, w, sure=180_000):
    def bitti():
        w.izleme.tazele()
        o = arka.oturum_oku(w.izleme.dizin) if w.izleme.dizin else {}
        return o.get("asama") == "kapatildi" and not arka.surec_canli(w.izleme.dizin)
    qtbot.waitUntil(bitti, timeout=sure)
    w.izleme.tazele()


def test_tek_video_akisi(qtbot, uygulama_ortami):
    w = _pencere(qtbot, uygulama_ortami)
    y = w.yeni
    y.ad.setText("cay bahcesi")
    y.fikir.setPlainText('Çay bahçesi. Çaycı: "Çaylar taze, buyurun."')
    y.sure.setValue(5)
    y.ileri.click()
    qtbot.waitUntil(lambda: y.yigin.currentIndex() == SAYFA_TEK, timeout=60_000)
    assert y.prompt.toPlainText().startswith("integrated_multimodal_description")
    w.grab().save(str(EKRAN / "2_tek_senaryo.png"))
    y.tek_uret.click()
    assert w.sekmeler.currentWidget() is w.izleme
    _bitene_kadar(qtbot, w)
    o = arka.oturum_oku(w.izleme.dizin)
    assert o["asama"] == "kapatildi" and arka.sonuc_video(w.izleme.dizin, o)
    assert w.izleme.sonuc.isVisible() and "teslim edildi" in w.izleme.sonuc.rapor.toPlainText()
    w.grab().save(str(EKRAN / "5_sonuc_tek.png"))
    w.sekmeler.setCurrentWidget(w.uretimler)
    w.uretimler.yenile()
    assert w.uretimler.tablo.rowCount() == 1 and "Bitti" in w.uretimler.tablo.item(0, 2).text()
    w.grab().save(str(EKRAN / "6_uretimler.png"))


def test_uzun_video_akisi(qtbot, uygulama_ortami):
    w = _pencere(qtbot, uygulama_ortami)
    y = w.yeni
    y.tur.setCurrentIndex(1)
    y.sure.setValue(24)
    y.ad.setText("sahaf")
    y.fikir.setPlainText('Sahaf. Kız: "Eski haritalarınız var mı?" Rıza: "En güzelleri arka odada."')
    w.grab().save(str(EKRAN / "1_yeni_video.png"))
    y.ileri.click()
    qtbot.waitUntil(lambda: y.yigin.currentIndex() == SAYFA_KART, timeout=60_000)
    # kartı arayüzde düzenle: kıyafeti değiştir, kaydet → hikaye.json'a yazılmalı
    y.kart.karakterler.item(0, 4).setText("white apron, grey wool vest")
    w.grab().save(str(EKRAN / "3_kart.png"))
    y.gorsele.click()
    qtbot.waitUntil(lambda: y.yigin.currentIndex() == SAYFA_GORSEL, timeout=10_000)
    qtbot.waitUntil(lambda: y.gorseller.gorunen == 2, timeout=60_000)   # K1 + MEKAN önizlemede
    kart = json.loads((y.klasor / "hikaye.json").read_text(encoding="utf-8"))
    assert kart["karakterler"][0]["kiyafet"] == "white apron, grey wool vest"
    assert kart["_meta"]["sahte"] is True                       # meta korundu
    w.grab().save(str(EKRAN / "4_gorseller.png"))
    y.plan_btn.click()
    qtbot.waitUntil(lambda: w.sekmeler.currentWidget() is w.izleme, timeout=60_000)
    s = json.loads((y.klasor / "uzun_senaryo.json").read_text(encoding="utf-8"))
    assert "grey wool vest" in s["dunya_capasi"]               # düzenleme üretime gitti
    _bitene_kadar(qtbot, w)
    assert "Kol `ref`" in w.izleme.sonuc.rapor.toPlainText() or "Kol ref" in w.izleme.sonuc.rapor.toPlainText()
    w.grab().save(str(EKRAN / "5_sonuc_uzun.png"))


def test_giris_penceresi(qtbot, uygulama_ortami, monkeypatch):
    monkeypatch.setenv("SAHTE_GIRIS", "yok")
    p = GirisPenceresi(uygulama_ortami["ayar"])
    qtbot.addWidget(p)
    p.show()
    qtbot.waitUntil(lambda: p.url is not None, timeout=20_000)
    assert p.url.startswith("https://accounts.google.com/") and p.ac.isEnabled()
    p.kod.setText("dogru-kod")
    p.gonder.click()
    qtbot.waitUntil(lambda: p.basarili, timeout=20_000)
    p.grab().save(str(EKRAN / "7_giris.png"))


def test_kesinti_sonrasi_devam(qtbot, uygulama_ortami):
    ortam = uygulama_ortami
    ayar = ortam["ayar"]
    klasor = arka.yeni_is_klasoru(ayar, "kesinti")
    import subprocess
    subprocess.run(arka.muse_komutu(ayar, "senaryo.py", "--fikir", "x", "--sure", 5, "--sahte", "--cikti",
                                    klasor / "senaryo.json"), check=True, env=arka.ortam(ayar), capture_output=True)
    oturum = klasor / "oturum"
    arka.uretim_baslat(ayar, oturum, "uret", "--senaryo", klasor / "senaryo.json", "--gpu", "cpu", "--anahtar", "",
                       "--aralik", 1, "--sorunlu-kabul")
    qtbot.waitUntil(lambda: bool(arka.oturum_oku(oturum).get("isler")), timeout=60_000)
    arka.uretimi_durdur(oturum)                                  # uygulama/makine kapandı
    qtbot.waitUntil(lambda: not arka.surec_canli(oturum), timeout=10_000)
    assert arka.acik_kalmis(oturum, arka.oturum_oku(oturum))   # açılışta uyarılacak durum
    w = _pencere(qtbot, ortam)
    qtbot.waitUntil(lambda: w.sekmeler.currentWidget() is w.uretimler, timeout=5_000)   # açılış uyarısı
    w.uretimler.yenile()
    assert "Devam gerekli" in w.uretimler.tablo.item(0, 2).text()
    w.uretimler.tablo.selectRow(0)
    w.uretimler._devam()
    _bitene_kadar(qtbot, w)
    assert arka.sonuc_video(oturum, arka.oturum_oku(oturum))
