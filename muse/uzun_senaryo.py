#!/usr/bin/env python3
"""Uzun video (16–60 sn) senaryosu: hikâye kartı → karakter/mekân görselleri → blok planı → blok prompt'ları.

GPU açmaz, CCU harcamaz (Gemini kotası harcar). Üç alt komut, sırayla:

  kart    Fikirden hikâye kartı (hikaye.json): karakterler (görünüş, kıyafet, ses), mekân, ışık, bloklar ve
          her bloğun replikleri. Muse kartı okur, gerekirse JSON'u elle düzeltir, orhan'a onaylatır.
  gorsel  Karttaki her karakter ve mekân için referans görseli üretir (gorseller/K1.png, MEKAN.png).
          Kullanıcının görseli varsa --ref K1=yol.png ile verilir, üretilmez. Beğenilmeyen görsel
          --yeniden K1 ile yeniden üretilir. Görseller orhan'a onaylatılır.
  plan    Kart + görseller → çekim planı → her blok için H3 prompt'u → uzun_senaryo.json (üretimin girdisi).
          --kol ref    : kimliği görseller taşır (Ref2VA, önerilen)
          --kol metin  : bugünkü yöntem, yalnızca metin çapası (T2VA)
          --kol ikisi  : DENEY — aynı plan iki yöntemle de üretilir, sonuçlar karşılaştırılır

Çıkış kodları: 0 = hazır, 2 = yazıldı ama denetimde sorun var, 1 = hata.
"""

import argparse
import datetime
import json
import os
import re
import shutil
import struct
import sys
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ortak  # noqa: E402
from senaryo import h3_yukle  # noqa: E402

MIN_TOPLAM, MAX_TOPLAM = 16, 60
MAX_KARAKTER = 3

KART_PROMPT = """You are a film writer and continuity supervisor. Turn a short video idea into a STORY BIBLE for a
{total}-second video made of {n} block(s). An AI video model renders each block separately (4–15 seconds each), so
everything that must stay identical between blocks has to be written down here once, precisely.

Output ONLY valid JSON with exactly this structure (no markdown):
{{
  "baslik": "short Turkish title",
  "karakterler": [
    {{"id": "K1", "ad": "Turkish name or role (e.g. Çaycı Ahmet)", "konusmaci": "S1",
      "gorunum": "English: sex, age, face shape, skin tone, eyes, eyebrows, nose, moustache/beard, hair colour, length and style, build, height",
      "kiyafet": "English: every garment with colour and material, accessories, flat shoes or boots",
      "ses": "English: voice timbre, pitch, pace and accent (e.g. warm deep gravelly baritone, slow pace, Istanbul Turkish)"}}
  ],
  "mekan": {{"ad": "Turkish place name", "tarif": "English: architecture, layout, materials, furniture, props that stay in place, background"}},
  "zaman_isik": "English: time of day, light direction and quality",
  "renk_paleti": "English: 3-5 colours",
  "bloklar": [
    {{"blok": 1, "sure": 15, "ozet": "English: what happens in this block, beat by beat",
      "replikler": [{{"konusmaci": "S1", "metin": "exact Turkish line"}}]}}
  ]
}}

Rules:
- At most {max_char} characters. Only speaking characters get a "konusmaci" (S1, S2... in order of first line);
  silent characters use "konusmaci": "".
- Block durations are whole seconds between 4 and 15 and sum to exactly {total}. Use {n} block(s).
- Every quoted line and quoted on-screen text of the idea appears EXACTLY (same letters and punctuation) in some
  block's "replikler" "metin". Do not add lines the idea does not imply; you may add at most one short line per block
  only if the idea asks for a conversation without giving all lines.
- About 2.5 words per second of speech at most; leave the first and last second of every block without speech.
- Each block ends on a calm moment (no fast motion across the block boundary).
- The place, outfits and props never change between blocks unless the idea says so.
{style_note}"""

PORTRE = """A {kind} full-body character reference image of one person: {gorunum}. Wearing: {kiyafet}.
Standing in a relaxed neutral pose, facing three-quarters toward the viewer, the whole figure from head to feet,
in front of a plain light-grey background, even soft studio light. Exactly one person. {look}
No text, no letters, no logos, no watermark."""

MEKAN_GORSELI = """A {kind} wide establishing image of an empty place, ready for actors: {tarif}. {isik}.
Colour palette: {palet}. Eye-level camera, natural perspective. No people, no animals. {look}
No readable text, no signs, no letters, no logos, no watermark."""


def blok_sayisi(toplam):
    return -(-toplam // 15)   # H3 tek üretimde en fazla 15 sn


def kart_denetle(kart, toplam, fikir, pw):
    """Kartın biçimini ve fikirdeki tırnak içi metinlerin korunmasını denetler; sorun listesi döner."""
    sorunlar = []
    karakterler = kart.get("karakterler") or []
    if not karakterler:
        sorunlar.append("En az bir karakter olmalı.")
    if len(karakterler) > MAX_KARAKTER:
        sorunlar.append(f"En fazla {MAX_KARAKTER} karakter olabilir ({len(karakterler)} var).")
    idler, konusmacilar = set(), []
    for k in karakterler:
        for alan in ("id", "ad", "gorunum", "kiyafet"):
            if not (k.get(alan) or "").strip():
                sorunlar.append(f"Karakter {k.get('id', '?')}: '{alan}' boş.")
        if k.get("id") in idler:
            sorunlar.append(f"Karakter kimliği tekrar ediyor: {k.get('id')}")
        idler.add(k.get("id"))
        if k.get("konusmaci"):
            konusmacilar.append(k["konusmaci"])
            if not (k.get("ses") or "").strip():
                sorunlar.append(f"Konuşan karakter {k.get('id')}: 'ses' tarifi boş.")
    if konusmacilar != [f"S{i}" for i in range(1, len(konusmacilar) + 1)]:
        sorunlar.append(f"Konuşmacı kimlikleri S1, S2… sırasıyla verilmeli (şu an: {konusmacilar}).")
    if not ((kart.get("mekan") or {}).get("tarif") or "").strip():
        sorunlar.append("Mekân tarifi boş.")
    bloklar = kart.get("bloklar") or []
    if not bloklar:
        sorunlar.append("Blok listesi boş.")
    toplam_blok = 0
    for i, b in enumerate(bloklar, 1):
        try:
            s = int(b.get("sure"))
        except (TypeError, ValueError):
            sorunlar.append(f"Blok {i}: süre sayı değil.")
            continue
        if not 4 <= s <= 15:
            sorunlar.append(f"Blok {i}: süre 4–15 sn olmalı ({s}).")
        toplam_blok += s
        if int(b.get("blok", i)) != i:
            sorunlar.append(f"Blok numaraları 1'den başlayıp sırayla artmalı ({b.get('blok')}).")
        for r in b.get("replikler") or []:
            if r.get("konusmaci") not in konusmacilar:
                sorunlar.append(f"Blok {i}: replikteki konuşmacı ({r.get('konusmaci')}) karakterlerde yok.")
            kelime = len((r.get("metin") or "").split())
            if kelime > int(b.get("sure", 15)) * 2.5:
                sorunlar.append(f"Blok {i}: replik bloğa sığmayacak kadar uzun ({kelime} kelime).")
    if toplam_blok != toplam:
        sorunlar.append(f"Blok süreleri toplamı {toplam_blok} sn; {toplam} sn olmalı.")
    tum = pw._norm_quotes(json.dumps(kart, ensure_ascii=False))
    for lit in pw.literals(fikir):
        if lit.strip() and pw._norm_quotes(lit.strip()) not in tum:
            sorunlar.append(f'Fikirdeki şu metin kartta yok: "{lit.strip()}"')
    return sorunlar


def dunya_capasi(kart):
    """Her blokta harfi harfine aynı kalacak dünya/karakter çapası (İngilizce)."""
    parcalar = []
    for k in kart["karakterler"]:
        kim = f"{k['ad']}" + (f" ({k['konusmaci']})" if k.get("konusmaci") else "")
        ses = f" Voice: {k['ses']}." if k.get("konusmaci") and k.get("ses") else ""
        parcalar.append(f"{kim}: {k['gorunum']}. Outfit: {k['kiyafet']}.{ses}")
    m = kart["mekan"]
    parcalar.append(f"Place — {m.get('ad', '')}: {m['tarif']}.")
    if kart.get("zaman_isik"):
        parcalar.append(f"Time and light: {kart['zaman_isik']}.")
    if kart.get("renk_paleti"):
        parcalar.append(f"Colour palette: {kart['renk_paleti']}.")
    parcalar.append("Faces, hair, outfits, voices, the place and its props stay exactly the same in every block.")
    return " ".join(parcalar)


def plan_fikri(kart):
    """plan_shots için fikir metni: kart blok blok, replikler tırnak içinde (planda korunmaları denetlenir)."""
    satirlar = ["Follow this story bible exactly. Keep the block count and each block's duration as given.",
                "Characters: " + "; ".join(
                    f"{k['ad']}" + (f" (speaker {k['konusmaci']}, voice: {k.get('ses', '')})" if k.get("konusmaci") else "")
                    for k in kart["karakterler"]),
                f"Place: {kart['mekan'].get('ad', '')} — {kart['mekan']['tarif']}"]
    ad = {k["konusmaci"]: k["ad"] for k in kart["karakterler"] if k.get("konusmaci")}
    for b in kart["bloklar"]:
        satir = f"Block {b['blok']} — exactly {b['sure']} seconds: {b['ozet']}"
        for r in b.get("replikler") or []:
            satir += f' {ad.get(r["konusmaci"], r["konusmaci"])} ({r["konusmaci"]}) says in Turkish: "{r["metin"]}"'
        satirlar.append(satir)
    return "\n".join(satirlar)


def gorsel_listesi(kart, gorsel_dizin):
    """Ref2VA görselleri, rol sırasıyla: önce konuşan karakterler (S1, S2…), sonra sessizler, en son mekân."""
    karakterler = sorted(kart["karakterler"], key=lambda k: (not k.get("konusmaci"), k.get("konusmaci") or "", k["id"]))
    liste = [{"id": k["id"], "dosya": os.path.join(gorsel_dizin, f"{k['id']}.png"), "rol": "karakter", "ad": k["ad"]}
             for k in karakterler]
    liste.append({"id": "MEKAN", "dosya": os.path.join(gorsel_dizin, "MEKAN.png"), "rol": "arka_plan",
                  "ad": kart["mekan"].get("ad", "")})
    return liste


def sahte_png(yol, renk=(200, 180, 150), boyut=(64, 96)):
    """Bağımlılıksız küçük bir PNG (yalnızca sahte mod)."""
    w, h = boyut
    ham = b"".join(b"\x00" + bytes(renk) * w for _ in range(h))

    def parca(tur, veri):
        return struct.pack(">I", len(veri)) + tur + veri + struct.pack(">I", zlib.crc32(tur + veri) & 0xFFFFFFFF)
    png = (b"\x89PNG\r\n\x1a\n" + parca(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
           + parca(b"IDAT", zlib.compress(ham)) + parca(b"IEND", b""))
    with open(yol, "wb") as f:
        f.write(png)


def sahte_kart(fikir, toplam):
    lits = re.findall(r'"([^"]+)"', fikir) or ["Merhaba."]
    n = blok_sayisi(toplam)
    sureler = [toplam // n + (1 if i < toplam % n else 0) for i in range(n)]
    return {
        "baslik": "Sahte deneme",
        "karakterler": [{"id": "K1", "ad": "Çaycı", "konusmaci": "S1", "gorunum": "a man in his fifties",
                         "kiyafet": "white apron", "ses": "warm deep voice"}],
        "mekan": {"ad": "Çay bahçesi", "tarif": "a seaside tea garden"},
        "zaman_isik": "golden hour", "renk_paleti": "amber, teal",
        "bloklar": [{"blok": i + 1, "sure": s, "ozet": "the tea seller serves tea",
                     "replikler": [{"konusmaci": "S1", "metin": lits[i]}] if i < len(lits) else []}
                    for i, s in enumerate(sureler)],
    }


def sahte_plan(kart):
    shots = []
    for b in kart["bloklar"]:
        yarim = b["sure"] / 2
        sesler = " ".join(f'"{r["metin"]}"' for r in b.get("replikler") or [])
        shots += [{"block": b["blok"], "shot": 1, "start_sec": 0.0, "duration": yarim, "framing": "wide",
                   "action": b["ozet"], "camera": "static", "sound": sesler or "ambience"},
                  {"block": b["blok"], "shot": 2, "start_sec": yarim, "duration": b["sure"] - yarim,
                   "framing": "medium", "action": "calm hold", "camera": "static", "sound": "ambience"}]
    return {"world_anchor": dunya_capasi(kart), "shots": shots}


def gemini_gorsel(pw, anahtar, metin, yol):
    from google.genai import types
    modeller = pw.image_models(anahtar)
    if not modeller:
        raise RuntimeError("Bu anahtarla görsel üretebilen Gemini modeli yok.")
    client = pw._client(anahtar, pw.IMAGE_TIMEOUT_MS)
    cfg = types.GenerateContentConfig(response_modalities=["IMAGE", "TEXT"], temperature=1.0)
    hatalar = []
    for model in modeller[:2]:
        try:
            resp = client.models.generate_content(model=model, contents=[metin], config=cfg)
        except Exception as e:  # noqa: BLE001
            hatalar.append(f"{model}: {str(e)[:150]}")
            continue
        for cand in resp.candidates or []:
            for part in (cand.content.parts if cand.content else None) or []:
                if getattr(part, "inline_data", None) and part.inline_data.data:
                    with open(yol, "wb") as f:
                        f.write(part.inline_data.data)
                    return model
        hatalar.append(f"{model}: görsel dönmedi")
    raise RuntimeError("Görsel üretilemedi: " + " | ".join(hatalar))


# ---------------- alt komutlar ----------------

def kmt_kart(a, config, pw):
    if not MIN_TOPLAM <= a.sure <= MAX_TOPLAM:
        raise SystemExit(f"--sure {MIN_TOPLAM}–{MAX_TOPLAM} olmalı. 15 sn ve altı için senaryo.py kullan.")
    n = blok_sayisi(a.sure)
    if a.sahte:
        kart = sahte_kart(a.fikir, a.sure)
    else:
        anahtar = ortak.anahtar_oku(a.anahtar)
        stil = config.STYLES[a.stil]
        sistem = KART_PROMPT.format(total=a.sure, n=n, max_char=MAX_KARAKTER,
                                    style_note=f"- Visual style of the video: {stil['kind']}.")
        icerik = [f"Total duration: {a.sure} seconds in {n} block(s).\n\nIdea:\n{a.fikir.strip()}"]
        print("⏳ Gemini hikâye kartını yazıyor…", flush=True)
        kart, sorunlar = None, []
        for deneme in range(2):
            ham = pw._generate(anahtar, config.GEMINI_MODEL, sistem, icerik, 0.6, log=print, step="hikâye kartı")
            try:
                kart = pw._parse_json(ham)
                sorunlar = kart_denetle(kart, a.sure, a.fikir, pw)
            except Exception as e:  # noqa: BLE001
                sorunlar = [f"Geçerli JSON değil: {e}"]
            if not sorunlar:
                break
            print("Kartta sorun, düzeltiliyor: " + " | ".join(sorunlar), flush=True)
            icerik = [icerik[0] + f"\n\nYour previous answer:\n{ham}\n\nFix these problems and output ONLY valid "
                      "JSON:\n- " + "\n- ".join(sorunlar)]
        if kart is None:
            print("❌ Gemini geçerli bir kart yazamadı.")
            return 1
    kart.update(_meta={"fikir": a.fikir.strip(), "sure": a.sure, "stil": a.stil, "sahte": a.sahte,
                       "modeller": dict(pw.used_models),
                       "olusturma": datetime.datetime.now().isoformat(timespec="seconds")})
    os.makedirs(a.dizin, exist_ok=True)
    yol = os.path.join(a.dizin, "hikaye.json")
    ortak.json_yaz(yol, kart)
    sorunlar = kart_denetle(kart, a.sure, a.fikir, pw)
    print(f"Hikâye kartı: {yol}")
    return _sonuc(sorunlar)


def kmt_gorsel(a, config, pw):
    kart = ortak.json_oku(os.path.join(a.dizin, "hikaye.json"))
    meta = kart["_meta"]
    gdizin = os.path.join(a.dizin, "gorseller")
    os.makedirs(gdizin, exist_ok=True)
    verilen = dict(r.split("=", 1) for r in a.ref)
    stil = config.STYLES[meta["stil"]]
    look = f"Style: {stil['look']}. Avoid: {stil['avoid']}." if stil.get("look") else "Photorealistic, natural skin texture."
    anahtar = None if meta.get("sahte") else ortak.anahtar_oku(a.anahtar)
    kayit = kart.setdefault("_gorseller", {})
    for g in gorsel_listesi(kart, gdizin):
        if g["id"] in verilen:
            kaynak = os.path.expanduser(verilen[g["id"]])
            if not os.path.isfile(kaynak):
                raise SystemExit(f"Görsel yok: {kaynak}")
            uzanti = os.path.splitext(kaynak)[1].lower()
            if uzanti != ".png":
                raise SystemExit(f"{g['id']} için PNG görsel ver ({kaynak}).")
            shutil.copyfile(kaynak, g["dosya"])
            kayit[g["id"]] = "kullanıcı"
            print(f"✅ {g['id']}: kullanıcının görseli kopyalandı")
            continue
        if os.path.isfile(g["dosya"]) and g["id"] not in a.yeniden:
            print(f"• {g['id']}: zaten var ({kayit.get(g['id'], '?')}); yeniden üretmek için --yeniden {g['id']}")
            continue
        if meta.get("sahte"):
            sahte_png(g["dosya"])
            kayit[g["id"]] = "sahte"
            print(f"✅ {g['id']}: sahte görsel")
            continue
        if g["id"] == "MEKAN":
            m = kart["mekan"]
            metin = MEKAN_GORSELI.format(kind=stil["kind"], tarif=m["tarif"], isik=kart.get("zaman_isik", ""),
                                         palet=kart.get("renk_paleti", ""), look=look)
        else:
            k = next(x for x in kart["karakterler"] if x["id"] == g["id"])
            metin = PORTRE.format(kind=stil["kind"], gorunum=k["gorunum"], kiyafet=k["kiyafet"], look=look)
        print(f"⏳ {g['id']} görseli üretiliyor…", flush=True)
        try:
            model = gemini_gorsel(pw, anahtar, metin, g["dosya"])
        except Exception as e:  # noqa: BLE001
            print(f"❌ {g['id']}: {str(e).replace(anahtar, '***')}")
            return 1
        kayit[g["id"]] = model
        print(f"✅ {g['id']}: {g['dosya']} ({model})")
    ortak.json_yaz(os.path.join(a.dizin, "hikaye.json"), kart)
    print("Görselleri aç ve kontrol et: yüz, kıyafet ve mekân karttaki tarife uyuyor mu? Sonra orhan'a onaylat.")
    return 0


def kmt_plan(a, config, pw):
    kart = ortak.json_oku(os.path.join(a.dizin, "hikaye.json"))
    meta = kart["_meta"]
    sorunlar = kart_denetle(kart, meta["sure"], meta["fikir"], pw)
    if sorunlar:
        print("❌ Hikâye kartında sorun var, önce düzelt:\n  - " + "\n  - ".join(sorunlar))
        return 1
    gorseller = gorsel_listesi(kart, os.path.join(a.dizin, "gorseller"))
    kollar = ["metin", "ref"] if a.kol == "ikisi" else [a.kol]
    if "ref" in kollar:
        eksik = [g["id"] for g in gorseller if not os.path.isfile(g["dosya"])]
        if eksik:
            print(f"❌ Görseller eksik: {', '.join(eksik)}. Önce 'gorsel' komutunu çalıştır.")
            return 1
    anahtar = None if meta.get("sahte") else ortak.anahtar_oku(a.anahtar)
    yollar = [g["dosya"] for g in gorseller]
    roller = [{"role": g["rol"], "name": g["ad"]} for g in gorseller]
    notlar = []

    if meta.get("sahte"):
        plan = sahte_plan(kart)
    else:
        print("⏳ Gemini çekim planını yazıyor…", flush=True)
        plan, psorun = pw.plan_shots(plan_fikri(kart), meta["sure"], anahtar, config.GEMINI_MODEL,
                                     images=yollar if "ref" in kollar else (), style=meta["stil"], log=notlar.append,
                                     roles=roller if "ref" in kollar else None)
        if psorun:
            print("❌ Çekim planı denetimden geçmedi:\n  - " + "\n  - ".join(psorun))
            ortak.json_yaz(os.path.join(a.dizin, "plan_sorunlu.json"), plan)
            return 2
    plan["world_anchor"] = dunya_capasi(kart)   # her blokta ve her kolda harfi harfine aynı çapa

    sonuc_kollar, tum_sorunlar = {}, []
    for kol in kollar:
        imgs = yollar if kol == "ref" else ()
        rls = roller if kol == "ref" else None
        bloklar = []
        for binfo in pw.blocks_from_plan(plan):
            istek = pw.block_request(binfo, style=meta["stil"], idea=meta["fikir"])
            if meta.get("sahte"):
                prompt, sorun = pw.EXAMPLE_OUTPUT, []
            else:
                print(f"⏳ [{kol}] Blok {binfo['block']} prompt'u yazılıyor…", flush=True)
                prompt, sorun = pw.rewrite(istek, binfo["seconds"], anahtar, config.GEMINI_MODEL, imgs,
                                           log=notlar.append, style=meta["stil"], roles=rls)
            bloklar.append({"blok": binfo["block"], "sure": binfo["seconds"], "istek": istek,
                            "prompt": prompt, "sorunlar": list(sorun)})
            tum_sorunlar += [f"[{kol}] blok {binfo['block']}: {s}" for s in sorun]
        sonuc_kollar[kol] = {"ref": kol == "ref", "bloklar": bloklar}

    modeller = dict(pw.used_models)
    senaryo = {
        "surum": 1, "tur": "uzun",
        "olusturma": datetime.datetime.now().isoformat(timespec="seconds"),
        "h3_commit": ortak.H3_COMMIT,
        "fikir": meta["fikir"], "sure": meta["sure"], "stil": meta["stil"],
        "yontem": a.yontem, "cozunurluk": ortak.COZUNURLUKLER[a.cozunurluk], "seed": a.seed,
        "referanslar": [{"dosya": g["dosya"], "rol": g["rol"], "ad": g["ad"]} for g in gorseller]
        if "ref" in kollar else [],
        "hikaye": {k: v for k, v in kart.items() if not k.startswith("_")},
        "dunya_capasi": plan["world_anchor"], "plan": plan,
        "kollar": sonuc_kollar,
        "yeniden_uretim": 0 if a.kol == "ikisi" else a.yeniden_uretim,
        "kopru": bool(a.kopru),
        "deney": a.kol == "ikisi",
        "brief": plan_fikri(kart),
        "sorunlar": tum_sorunlar, "modeller": modeller,
        "yedek_model": [s for s, m in modeller.items() if "(yedek)" in m], "notlar": notlar,
        "sahte": bool(meta.get("sahte")),
        "durum": "hazir" if not tum_sorunlar else "sorunlu",
    }
    yol = os.path.join(a.dizin, "uzun_senaryo.json")
    ortak.json_yaz(yol, senaryo)
    n_blok = len(next(iter(sonuc_kollar.values()))["bloklar"])
    print(f"Uzun senaryo: {yol} · {n_blok} blok · kol: {', '.join(kollar)}")
    if senaryo["yedek_model"]:
        print(f"⚠️ Yedek modelle yazılan adımlar: {', '.join(senaryo['yedek_model'])}")
    return _sonuc(tum_sorunlar)


def _sonuc(sorunlar):
    if sorunlar:
        print("⚠️ Denetimde sorun var:\n  - " + "\n  - ".join(sorunlar))
        return 2
    print("✅ Hazır.")
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(description="Uzun video senaryosu (GPU'suz)")
    alt = p.add_subparsers(dest="komut", required=True)
    for ad in ("kart", "gorsel", "plan"):
        q = alt.add_parser(ad)
        q.add_argument("--h3", required=True)
        q.add_argument("--dizin", required=True, help="Bu uzun videonun klasörü")
        q.add_argument("--anahtar", default="~/.config/h3muse/gemini.key")
        if ad == "kart":
            q.add_argument("--fikir", required=True)
            q.add_argument("--sure", type=int, required=True, help=f"{MIN_TOPLAM}–{MAX_TOPLAM} sn")
            q.add_argument("--stil", choices=ortak.STILLER, default="real")
            q.add_argument("--sahte", action="store_true")
        if ad == "gorsel":
            q.add_argument("--ref", action="append", default=[], metavar="ID=YOL.png")
            q.add_argument("--yeniden", action="append", default=[], metavar="ID")
        if ad == "plan":
            q.add_argument("--kol", choices=("ref", "metin", "ikisi"), default="ref")
            q.add_argument("--yontem", choices=ortak.YONTEMLER, default="pika")
            q.add_argument("--cozunurluk", choices=list(ortak.COZUNURLUKLER), default="yatay")
            q.add_argument("--seed", type=int, default=22)
            q.add_argument("--yeniden-uretim", type=int, default=1,
                           help="Kusurlu blok için en fazla kaç yeniden üretim (deneyde 0)")
            q.add_argument("--kopru", action="store_true",
                           help="Deneysel: her bloğa önceki bloğun son karesi de sahne görseli olarak verilir")
    a = p.parse_args(argv)
    a.dizin = os.path.abspath(os.path.expanduser(a.dizin))
    config, pw = h3_yukle(a.h3)
    pw.used_models.clear()
    try:
        return {"kart": kmt_kart, "gorsel": kmt_gorsel, "plan": kmt_plan}[a.komut](a, config, pw)
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        print(f"❌ Hata: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
