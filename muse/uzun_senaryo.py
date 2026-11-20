#!/usr/bin/env python3
"""Uzun video (16–60 sn) senaryosu: hikâye kartı → karakter/mekân görselleri → blok planı → blok prompt'ları.

GPU açmaz, CCU harcamaz (Gemini kotası harcar). Asıl iş h3app.hikaye'de; bu dosya Muse için komut satırıdır.
Üç alt komut, sırayla:

  kart    Fikirden hikâye kartı (hikaye.json): karakterler (görünüş, kıyafet, ses), mekân, ışık, bloklar ve
          her bloğun replikleri. Muse kartı okur, gerekirse JSON'u elle düzeltir, orhan'a onaylatır.
  gorsel  Karttaki her karakter ve mekân için referans görseli üretir (gorseller/K1.png, MEKAN.png).
          Kullanıcının görseli varsa --ref K1=yol.png ile verilir, üretilmez. Beğenilmeyen görsel
          --yeniden K1 ile yeniden üretilir. Görseller orhan'a onaylatılır.
  plan    Kart + görseller → çekim planı → her blok için H3 prompt'u → uzun_senaryo.json (üretimin girdisi).
          --kol ref    : kimliği görseller taşır (Ref2VA, önerilen)
          --kol metin  : eski yöntem, yalnızca metin çapası (T2VA)
          --kol ikisi  : DENEY — aynı plan iki yöntemle de üretilir, sonuçlar karşılaştırılır

  kareler Anahtar kareli senaryoda (uzun_senaryo.json içinde "kareler") her çekimin ilk/son karesini Gemini görsel
          modeliyle üretir (kareler/<id>.png, tam çözünürlüğe kırpılmış). Senaryo elle (ör. olustur.py) yazılmıştır;
          bu komut yalnızca görselleri üretir. --yeniden ID, --ref ID=YOL.png. Taban karesi değişirse ona bağlı
          kareleri de --yeniden ile yenile.

Çıkış kodları: 0 = hazır, 2 = yazıldı ama denetimde sorun var, 1 = hata.
"""

import argparse
import datetime
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ortak  # noqa: E402
from senaryo import h3_yukle  # noqa: E402


def _sonuc(sorunlar):
    if sorunlar:
        print("⚠️ Denetimde sorun var:\n  - " + "\n  - ".join(sorunlar))
        return 2
    print("✅ Hazır.")
    return 0


def kmt_kart(a, config, pw, hk):
    if not hk.MIN_TOPLAM <= a.sure <= hk.MAX_TOPLAM:
        raise SystemExit(f"--sure {hk.MIN_TOPLAM}–{hk.MAX_TOPLAM} olmalı. 15 sn ve altı için senaryo.py kullan.")
    if a.sahte:
        kart = hk.ornek_kart(a.fikir, a.sure)
    else:
        anahtar = ortak.anahtar_oku(a.anahtar)
        print("⏳ Gemini hikâye kartını yazıyor…", flush=True)
        kart, _ = hk.kart_yaz(a.fikir, a.sure, anahtar, style=a.stil, log=print)
        if not isinstance(kart, dict):
            print("❌ Gemini geçerli bir kart yazamadı.")
            return 1
    kart["_meta"] = {"fikir": a.fikir.strip(), "sure": a.sure, "stil": a.stil, "sahte": a.sahte,
                     "modeller": dict(pw.used_models),
                     "olusturma": datetime.datetime.now().isoformat(timespec="seconds")}
    os.makedirs(a.dizin, exist_ok=True)
    yol = os.path.join(a.dizin, "hikaye.json")
    ortak.json_yaz(yol, kart)
    print(f"Hikâye kartı: {yol}")
    return _sonuc(hk.kart_denetle(kart, a.sure, a.fikir))


def kmt_gorsel(a, config, pw, hk):
    yol = os.path.join(a.dizin, "hikaye.json")
    if not os.path.isfile(yol):
        print(f"❌ Hikâye kartı yok: {yol}. Önce 'kart' adımını çalıştır (ve başarılı olduğunu gör).")
        return 1
    kart = ortak.json_oku(yol)
    meta = kart["_meta"]
    gdizin = os.path.join(a.dizin, "gorseller")
    os.makedirs(gdizin, exist_ok=True)
    verilen = dict(r.split("=", 1) for r in a.ref)
    ilhamlar = {k: os.path.expanduser(v) for k, v in (r.split("=", 1) for r in a.ilham)}
    for k, v in ilhamlar.items():
        if not os.path.isfile(v):
            raise SystemExit(f"İlham görseli yok: {v}")
    anahtar = None if meta.get("sahte") else ortak.anahtar_oku(a.anahtar)
    kayit = kart.setdefault("_gorseller", {})
    for g in hk.gorsel_listesi(kart, gdizin):
        if g["id"] in verilen:
            kaynak = os.path.expanduser(verilen[g["id"]])
            if not os.path.isfile(kaynak) or not kaynak.lower().endswith(".png"):
                raise SystemExit(f"{g['id']} için var olan bir PNG dosyası ver ({kaynak}).")
            shutil.copyfile(kaynak, g["dosya"])
            kayit[g["id"]] = "kullanıcı"
            print(f"✅ {g['id']}: kullanıcının görseli kopyalandı")
            continue
        if os.path.isfile(g["dosya"]) and g["id"] not in a.yeniden:
            print(f"• {g['id']}: zaten var ({kayit.get(g['id'], '?')}); yeniden üretmek için --yeniden {g['id']}")
            continue
        if meta.get("sahte"):
            hk.ornek_png(g["dosya"])
            kayit[g["id"]] = "sahte"
            print(f"✅ {g['id']}: sahte görsel")
            continue
        print(f"⏳ {g['id']} görseli üretiliyor…", flush=True)
        try:
            ilham = ilhamlar.get(g["id"])
            if ilham:
                print(f"   ilham görseli: {ilham}", flush=True)
            model = hk.gorsel_uret(hk.gorsel_metni(kart, g["id"], meta["stil"]), anahtar, g["dosya"],
                                   ilham=ilham, mekan=g["id"] == "MEKAN")
        except Exception as e:  # noqa: BLE001
            print(f"❌ {g['id']}: {str(e).replace(anahtar, '***')}")
            ortak.json_yaz(yol, kart)
            return 1
        kayit[g["id"]] = model
        print(f"✅ {g['id']}: {g['dosya']} ({model})")
    ortak.json_yaz(yol, kart)
    print("Görselleri aç ve kontrol et: yüz, kıyafet ve mekân karttaki tarife uyuyor mu? (Muse: sonra orhan'a onaylat.)")
    return 0


def kmt_plan(a, config, pw, hk):
    if not os.path.isfile(os.path.join(a.dizin, "hikaye.json")):
        print(f"❌ Hikâye kartı yok: {a.dizin}/hikaye.json. Önce 'kart' ve 'gorsel' adımlarını çalıştır.")
        return 1
    kart = ortak.json_oku(os.path.join(a.dizin, "hikaye.json"))
    meta = kart["_meta"]
    sorunlar = hk.kart_denetle(kart, meta["sure"], meta["fikir"])
    if sorunlar:
        print("❌ Hikâye kartında sorun var, önce düzelt:\n  - " + "\n  - ".join(sorunlar))
        return 1
    gorseller = hk.gorsel_listesi(kart, os.path.join(a.dizin, "gorseller"))
    kollar = list(hk.KOLLAR) if a.kol == "ikisi" else [a.kol]
    if "ref" in kollar:
        eksik = [g["id"] for g in gorseller if not os.path.isfile(g["dosya"])]
        if eksik:
            print(f"❌ Görseller eksik: {', '.join(eksik)}. Önce 'gorsel' komutunu çalıştır.")
            return 1
    else:
        gorseller = []
    notlar = []
    if meta.get("sahte"):
        plan, kol_bloklar, sorunlar = hk.ornek_planla(kart, kollar, gorseller, meta["stil"], meta["fikir"])
    else:
        print("⏳ Gemini çekim planını ve blok prompt'larını yazıyor…", flush=True)
        plan, kol_bloklar, sorunlar = hk.planla(kart, ortak.anahtar_oku(a.anahtar), gorseller, kollar,
                                                style=meta["stil"], fikir=meta["fikir"], log=notlar.append)
        if not kol_bloklar:
            ortak.json_yaz(os.path.join(a.dizin, "plan_sorunlu.json"), plan)
            print("❌ Çekim planı denetimden geçmedi:\n  - " + "\n  - ".join(sorunlar))
            return 2
    modeller = dict(pw.used_models)
    senaryo = {
        "surum": 2, "tur": "uzun",
        "olusturma": datetime.datetime.now().isoformat(timespec="seconds"),
        "h3app_surum": ortak.h3app_surum(a.h3),
        "fikir": meta["fikir"], "sure": meta["sure"], "stil": meta["stil"],
        "yontem": a.yontem, "cozunurluk": ortak.COZUNURLUKLER[a.cozunurluk], "seed": a.seed,
        "referanslar": [{"dosya": g["dosya"], "rol": g["rol"], "ad": g["ad"]} for g in gorseller],
        "hikaye": {k: v for k, v in kart.items() if not k.startswith("_")},
        "dunya_capasi": plan["world_anchor"], "plan": plan,
        "kollar": {k: {"ref": k == "ref", "bloklar": v} for k, v in kol_bloklar.items()},
        "yeniden_uretim": 0 if a.kol == "ikisi" else a.yeniden_uretim,
        "kopru": bool(a.kopru), "deney": a.kol == "ikisi",
        "brief": hk.plan_fikri(kart),
        "sorunlar": sorunlar, "modeller": modeller,
        "yedek_model": [s for s, m in modeller.items() if "(yedek)" in m], "notlar": notlar,
        "sahte": bool(meta.get("sahte")),
        "durum": "hazir" if not sorunlar else "sorunlu",
    }
    yol = os.path.join(a.dizin, "uzun_senaryo.json")
    ortak.json_yaz(yol, senaryo)
    n_blok = len(next(iter(kol_bloklar.values())))
    print(f"Uzun senaryo: {yol} · {n_blok} blok · kol: {', '.join(kollar)}")
    if senaryo["yedek_model"]:
        print(f"⚠️ Yedek modelle yazılan adımlar: {', '.join(senaryo['yedek_model'])}")
    return _sonuc(sorunlar)


def kmt_kareler(a, config, pw, hk):
    from h3app import kare
    yol = os.path.join(a.dizin, "uzun_senaryo.json")
    if not os.path.isfile(yol):
        print(f"❌ Senaryo yok: {yol}")
        return 1
    senaryo = ortak.json_oku(yol)
    liste = senaryo.get("kareler") or []
    if not liste:
        print("❌ Bu senaryoda anahtar kare yok (\"kareler\" boş).")
        return 1
    boyut = tuple(config.RESOLUTIONS[senaryo["cozunurluk"]])
    verilen = {k: os.path.expanduser(v) for k, v in (r.split("=", 1) for r in a.ref)}
    bilinen = {k["id"] for k in liste}
    for x in list(verilen) + a.yeniden:
        if x not in bilinen:
            raise SystemExit(f"Bilinmeyen kare: {x}. Kareler: {', '.join(sorted(bilinen))}")
    sahte = bool(senaryo.get("sahte"))
    anahtar = None if sahte else ortak.anahtar_oku(a.anahtar)
    dosya = {k["id"]: k["dosya"] for k in liste}
    kayit = senaryo.setdefault("kare_modelleri", {})
    for k in liste:
        i = k["id"]
        if i in verilen:
            if not os.path.isfile(verilen[i]):
                raise SystemExit(f"{i}: dosya yok ({verilen[i]})")
            kare.hizala(verilen[i], k["dosya"], *boyut)
            kayit[i] = "kullanıcı"
            print(f"✅ {i}: kullanıcının görseli kırpılıp kopyalandı")
            continue
        if os.path.isfile(k["dosya"]) and i not in a.yeniden:
            print(f"• {i}: zaten var ({kayit.get(i, '?')}); yeniden üretmek için --yeniden {i}")
            continue
        if sahte:
            hk.ornek_png(k["dosya"])
            kayit[i] = "sahte"
            print(f"✅ {i}: sahte kare")
            continue
        girdiler = []
        if k.get("taban"):
            if not os.path.isfile(dosya[k["taban"]]):
                print(f"❌ {i}: taban karesi {k['taban']} henüz yok.")
                return 1
            girdiler.append(("BASE FRAME", dosya[k["taban"]]))
        if k.get("kompozisyon"):
            girdiler.append(("COMPOSITION", os.path.expanduser(k["kompozisyon"])))
        girdiler += [(g["etiket"], os.path.expanduser(g["dosya"])) for g in k.get("girdiler") or []]
        eksik = [d for _, d in girdiler if not os.path.isfile(d)]
        if eksik:
            print(f"❌ {i}: girdi görseli yok: {', '.join(eksik)}")
            return 1
        print(f"⏳ {i} karesi üretiliyor ({len(girdiler)} girdi görseli)…", flush=True)
        try:
            metin = kare.kare_metni(k["tarif"], senaryo["stil"], taban=bool(k.get("taban")),
                                    kompozisyon=bool(k.get("kompozisyon")))
            model = kare.kare_uret(metin, anahtar, k["dosya"], girdiler, boyut)
        except Exception as e:  # noqa: BLE001
            print(f"❌ {i}: {str(e).replace(anahtar, '***')}")
            ortak.json_yaz(yol, senaryo)
            return 1
        kayit[i] = model
        print(f"✅ {i}: {k['dosya']} ({model})")
    ortak.json_yaz(yol, senaryo)
    print("Kareleri sırayla aç ve kontrol et (kimlik, kompozisyon, ilk→son farkı). Muse: sonra orhan'a onaylat.")
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(description="Uzun video senaryosu (GPU'suz)")
    alt = p.add_subparsers(dest="komut", required=True)
    for ad in ("kart", "gorsel", "plan", "kareler"):
        q = alt.add_parser(ad)
        q.add_argument("--h3", help="h3 klasörü (varsayılan: bu deponun h3/ klasörü)")
        q.add_argument("--dizin", required=True, help="Bu uzun videonun klasörü")
        q.add_argument("--anahtar", default="~/.config/h3muse/gemini.key")
        if ad == "kart":
            q.add_argument("--fikir", required=True)
            q.add_argument("--sure", type=int, required=True, help="16–60 sn")
            q.add_argument("--stil", choices=ortak.STILLER, default="real")
            q.add_argument("--sahte", action="store_true")
        if ad == "gorsel":
            q.add_argument("--ref", action="append", default=[], metavar="ID=YOL.png",
                           help="Bu görseli olduğu gibi kullan (üretme)")
            q.add_argument("--ilham", action="append", default=[], metavar="ID=YOL",
                           help="Görseli üretirken bu fotoğrafı/resmi Gemini'ye ilham olarak ver (MEKAN: mimari "
                                "referans; karakter: kıyafet/zırh ilhamı). --yeniden ile birlikte mevcut görseli yeniler")
            q.add_argument("--yeniden", action="append", default=[], metavar="ID")
        if ad == "kareler":
            q.add_argument("--ref", action="append", default=[], metavar="ID=YOL",
                           help="Bu kareyi üretme; verilen görseli kırpıp kullan")
            q.add_argument("--yeniden", action="append", default=[], metavar="ID")
        if ad == "plan":
            q.add_argument("--kol", choices=("ref", "metin", "ikisi"), default="ref")
            q.add_argument("--yontem", choices=ortak.YONTEMLER, default="pika")
            q.add_argument("--cozunurluk", choices=list(ortak.COZUNURLUKLER), default="yatay")
            q.add_argument("--seed", type=int, default=22)
            q.add_argument("--yeniden-uretim", type=int, default=1,
                           help="Kusurlu blok için en fazla kaç yeniden üretim (deneyde 0)")
            q.add_argument("--kopru", action=argparse.BooleanOptionalAction, default=True,
                           help="Köprü (varsayılan açık): her bloğa önceki bloğun son karesi de sahne görseli olarak "
                                "verilir ve bloğun prompt'u o kareye göre yeniden yazılır. Kapatmak: --no-kopru")
    a = p.parse_args(argv)
    a.dizin = os.path.abspath(os.path.expanduser(a.dizin))
    config, pw = h3_yukle(a.h3)
    from h3app import hikaye as hk
    pw.used_models.clear()
    try:
        return {"kart": kmt_kart, "gorsel": kmt_gorsel, "plan": kmt_plan, "kareler": kmt_kareler}[a.komut](a, config, pw, hk)
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        print(f"❌ Hata: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
