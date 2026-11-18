#!/usr/bin/env python3
"""Adım 1: senaryo. GPU açmadan, Muse'un kendi makinesinde Gemini ile fikir → brief → H3 prompt'u yazar.

CCU harcamaz. Çıktı: senaryo.json (üretim adımının tek girdisi).

Örnek:
  python muse/senaryo.py --h3 ~/workspace/h3-video-studyosu \
      --fikir 'Deniz kenarında bir çay bahçesi. Çaycı: "Çaylar taze, buyurun."' \
      --sure 10 --stil real --yontem pika --cozunurluk yatay \
      --anahtar ~/.config/h3muse/gemini.key --cikti ~/workspace/h3uretim/caybahcesi/senaryo.json

Brief'i elle düzelttiysen yalnızca prompt'u yeniden yazdır:
  python muse/senaryo.py ... --brief-dosyasi duzeltilmis_brief.txt

Çıkış kodları: 0 = senaryo hazır, 2 = prompt yazıldı ama denetimde sorun var, 1 = hata.
"""

import argparse
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ortak  # noqa: E402


def h3_yukle(h3_dizin=None):
    """h3app'i bu deponun h3/ klasöründen yükler."""
    h3_dizin = os.path.abspath(os.path.expanduser(h3_dizin or ortak.H3_DIZIN))
    if not os.path.isfile(os.path.join(h3_dizin, "h3app", "prompt_writer.py")):
        raise SystemExit(f"h3app bulunamadı: {h3_dizin}. 'git pull' ile depoyu güncelle.")
    # Kılavuz önbelleği /content yerine yerel bir klasöre yazılsın (config içe aktarılmadan önce)
    os.environ.setdefault("H3APP_WORK_DIR", os.path.expanduser("~/.cache/h3muse"))
    if h3_dizin not in sys.path:
        sys.path.insert(0, h3_dizin)
    from h3app import config, prompt_writer
    return config, prompt_writer


def ref_coz(deger):
    """'yol[:rol[:ad]]' → {'dosya','rol','ad'}"""
    parcalar = deger.split(":", 2)
    yol = os.path.abspath(os.path.expanduser(parcalar[0]))
    rol = parcalar[1] if len(parcalar) > 1 and parcalar[1] else "karakter"
    ad = parcalar[2] if len(parcalar) > 2 else ""
    if rol not in ortak.ROLLER:
        raise SystemExit(f"Geçersiz rol '{rol}'. Seçenekler: {', '.join(ortak.ROLLER)}")
    if not os.path.isfile(yol):
        raise SystemExit(f"Referans görsel yok: {yol}")
    return {"dosya": yol, "rol": rol, "ad": ad}


def main(argv=None):
    p = argparse.ArgumentParser(description="Fikir → brief → H3 prompt'u (Gemini, GPU'suz)")
    p.add_argument("--h3", help="h3 klasörü (varsayılan: bu deponun h3/ klasörü)")
    p.add_argument("--fikir", required=True, help="Kısa fikir (Türkçe; replikler çift tırnak içinde)")
    p.add_argument("--sure", type=int, default=10, help="Saniye, 4–15 (varsayılan 10)")
    p.add_argument("--stil", choices=ortak.STILLER, default="real")
    p.add_argument("--yontem", choices=ortak.YONTEMLER, default="pika")
    p.add_argument("--cozunurluk", choices=list(ortak.COZUNURLUKLER), default="yatay")
    p.add_argument("--seed", type=int, default=22)
    p.add_argument("--ref", action="append", default=[], metavar="YOL[:ROL[:AD]]",
                   help="Referans görsel; rol: karakter | arka_plan | nesne. En fazla 9, tekrarlanabilir.")
    p.add_argument("--brief-dosyasi", help="Gemini'nin brief'i yerine bu dosyadaki brief kullanılır")
    p.add_argument("--anahtar", default="~/.config/h3muse/gemini.key", help="Gemini anahtar dosyası (chmod 600)")
    p.add_argument("--cikti", required=True, help="Yazılacak senaryo.json yolu")
    p.add_argument("--sahte", action="store_true", help="Gemini çağırmadan örnek metinlerle dene (test)")
    a = p.parse_args(argv)

    if not 4 <= a.sure <= 15:
        raise SystemExit("--sure 4 ile 15 arasında olmalı. Daha uzun video bu akışta desteklenmiyor.")
    refs = [ref_coz(r) for r in a.ref]
    if len(refs) > 9:
        raise SystemExit("En fazla 9 referans görsel verilebilir.")
    config, pw = h3_yukle(a.h3)
    anahtar = None if a.sahte else ortak.anahtar_oku(a.anahtar)
    gorseller = [r["dosya"] for r in refs]
    roller = [{"role": r["rol"], "name": r["ad"]} for r in refs] or None
    notlar = []
    pw.used_models.clear()

    try:
        if a.brief_dosyasi:
            brief = open(os.path.expanduser(a.brief_dosyasi), encoding="utf-8").read().strip()
            brief_kaynak = "elle"
        elif a.sahte:
            brief, brief_kaynak = pw.BRIEF_EXAMPLES[0][1], "sahte"
        else:
            print("⏳ 1/2 Gemini brief'i yazıyor…", flush=True)
            brief = pw.expand(a.fikir, a.sure, anahtar, config.GEMINI_MODEL, gorseller, log=notlar.append,
                              style=a.stil, roles=roller)
            brief_kaynak = "gemini"
        if a.sahte:
            prompt = pw.EXAMPLE_OUTPUT
            sorunlar = pw.check(prompt, brief, len(gorseller), a.stil, roles=roller)
        else:
            print("⏳ 2/2 Gemini H3 prompt'unu yazıyor…", flush=True)
            prompt, sorunlar = pw.rewrite(brief, a.sure, anahtar, config.GEMINI_MODEL, gorseller,
                                          log=notlar.append, style=a.stil, roles=roller)
    except Exception as e:  # noqa: BLE001
        mesaj = str(e)
        if anahtar:
            mesaj = mesaj.replace(anahtar, "***")
        print(f"❌ Gemini hatası: {mesaj}")
        return 1

    modeller = dict(pw.used_models)
    yedek = [adim for adim, m in modeller.items() if "(yedek)" in m]
    senaryo = {
        "surum": 1,
        "olusturma": datetime.datetime.now().isoformat(timespec="seconds"),
        "h3app_surum": ortak.h3app_surum(a.h3),
        "fikir": a.fikir.strip(),
        "sure": a.sure,
        "stil": a.stil,
        "yontem": a.yontem,
        "cozunurluk": ortak.COZUNURLUKLER[a.cozunurluk],
        "seed": a.seed,
        "referanslar": refs,
        "brief": brief,
        "brief_kaynak": brief_kaynak,
        "prompt": prompt,
        "sorunlar": list(sorunlar),
        "modeller": modeller,
        "yedek_model": yedek,
        "notlar": notlar,
        "sahte": a.sahte,
        "durum": "hazir" if prompt.strip() and not sorunlar else "sorunlu",
    }
    os.makedirs(os.path.dirname(os.path.abspath(a.cikti)), exist_ok=True)
    ortak.json_yaz(a.cikti, senaryo)

    print(f"Senaryo yazıldı: {a.cikti}")
    print(f"Modeller: {modeller or '-'}")
    if yedek:
        print(f"⚠️ Yedek modelle yazılan adımlar: {', '.join(yedek)}. Kalite düşük olabilir; "
              "bir süre sonra yeniden dene.")
    if sorunlar:
        print("⚠️ Prompt denetiminde sorun var:")
        for s in sorunlar:
            print(f"  - {s}")
        return 2
    print("✅ Senaryo hazır.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
