"""Uzun video (16–60 sn) için hikâye kartı, karakter/mekân referans görselleri ve blok planı.

Sorun: H3 tek seferde en fazla 15 sn üretir; uzun video ayrı üretilen bloklardan oluşur. Bloklar arasında kimliği
yalnızca birkaç cümlelik bir metin taşıyınca model yüzü, kıyafeti ve mekânı bloktan bloğa farklı çizer.

Çözüm:
1. Hikâye kartı: karakterlerin görünüşü, kıyafeti ve SESİ; mekân; ışık; bloklar ve her bloğun replikleri bir kez
   yazılır, denetlenir ve her bloğa harfi harfine aynı "dünya çapası" olarak verilir.
2. Referans görseller: her karakter için boydan bir görsel, mekân için boş bir sahne görseli (Gemini görsel modeli
   ya da kullanıcının kendi görselleri). Her blok bu görsellerle Ref2VA olarak üretilir; kimliği görsel taşır.
3. Blok planı: `prompt_writer.plan_shots` karta göre çekimleri planlar, `block_request` + `rewrite` her bloğun H3
   prompt'unu yazar. "metin" kolu (görselsiz, eski yöntem) ve "ref" kolu (Ref2VA) aynı plandan üretilebilir.
"""

import json
import os
import re
import struct
import zlib

from . import config, prompt_writer as pw

MIN_TOPLAM, MAX_TOPLAM = 16, config.MAX_TOTAL_SECONDS
MAX_KARAKTER = 3
KOLLAR = ("metin", "ref")

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
- Turkish fields ("baslik", "ad", "mekan.ad", "metin") keep Turkish letters exactly (ı İ ş Ş ğ Ğ ç Ç ö Ö ü Ü):
  "Rıza", not "Riza"; "Sahaf Dükkânı", not "Sahaf Dukkani".
- Do not move the story to a specific named place (city, district, landmark) the idea does not name.
- "mekan.tarif" describes the set as it is BEFORE the first block starts: an object that a character brings, serves
  or places later in the story (a tea glass, a tray, a letter) must NOT be in it. Props that are already there at
  the start (used glasses waiting to be cleared, furniture) may be.
- Visual style of the video: {kind}."""

PORTRE = """A {kind} full-body character reference image of one person: {gorunum}. Wearing: {kiyafet}.
Standing in a relaxed neutral pose, facing three-quarters toward the viewer, the whole figure from head to feet,
in front of a plain light-grey background, even soft studio light. Exactly one person. {look}
No text, no letters, no logos, no watermark."""

MEKAN_GORSELI = """A {kind} wide establishing image of an empty place, ready for actors: {tarif}. {isik}.
Colour palette: {palet}. Eye-level camera, natural perspective. No people, no animals. {look}
No readable text, no signs, no letters, no logos, no watermark."""


def blok_sayisi(toplam):
    return -(-int(toplam) // config.MAX_SECONDS)


# ---------------- hikâye kartı ----------------

def kart_denetle(kart, toplam, fikir=""):
    """Kartın biçimini ve fikirdeki tırnak içi metinlerin korunmasını denetler; sorun listesi döner."""
    sorunlar = []
    if not isinstance(kart, dict):
        return ["Kart bir JSON nesnesi olmalı."]
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
        if not config.MIN_SECONDS <= s <= config.MAX_SECONDS:
            sorunlar.append(f"Blok {i}: süre {config.MIN_SECONDS}–{config.MAX_SECONDS} sn olmalı ({s}).")
        toplam_blok += s
        if int(b.get("blok", i)) != i:
            sorunlar.append(f"Blok numaraları 1'den başlayıp sırayla artmalı ({b.get('blok')}).")
        for r in b.get("replikler") or []:
            if r.get("konusmaci") not in konusmacilar:
                sorunlar.append(f"Blok {i}: replikteki konuşmacı ({r.get('konusmaci')}) karakterlerde yok.")
            kelime = len((r.get("metin") or "").split())
            if kelime > s * 2.5:
                sorunlar.append(f"Blok {i}: replik bloğa sığmayacak kadar uzun ({kelime} kelime).")
    if toplam_blok != int(toplam):
        sorunlar.append(f"Blok süreleri toplamı {toplam_blok} sn; {toplam} sn olmalı.")
    tum = pw._norm_quotes(json.dumps(kart, ensure_ascii=False))
    for lit in pw.literals(fikir or ""):
        if lit.strip() and pw._norm_quotes(lit.strip()) not in tum:
            sorunlar.append(f'Fikirdeki şu metin kartta yok: "{lit.strip()}"')
    return sorunlar


def kart_yaz(fikir, toplam, api_key, model=None, style=config.DEFAULT_STYLE, retries=1, log=print):
    """Fikir → hikâye kartı (Gemini). (kart, sorunlar) döner; sorun varsa Gemini'ye bir kez düzelttirilir."""
    n = blok_sayisi(toplam)
    sistem = KART_PROMPT.format(total=toplam, n=n, max_char=MAX_KARAKTER, kind=config.STYLES[style]["kind"])
    bas = f"Total duration: {toplam} seconds in {n} block(s).\n\nIdea:\n{fikir.strip()}"
    icerik, kart, sorunlar = [bas], None, ["Gemini yanıt vermedi."]
    for deneme in range(retries + 1):
        ham = pw._generate(api_key, model or config.GEMINI_MODEL, sistem, icerik, 0.6, log=log, step="hikâye kartı")
        try:
            kart = pw._parse_json(ham)
            sorunlar = kart_denetle(kart, toplam, fikir)
        except Exception as e:  # noqa: BLE001
            sorunlar = [f"Geçerli JSON değil: {e}"]
        if not sorunlar:
            break
        log(f"Kartta sorun ({deneme + 1}. deneme): " + " | ".join(sorunlar))
        icerik = [bas + f"\n\nYour previous answer:\n{ham}\n\nFix these problems and output ONLY valid JSON:\n- "
                  + "\n- ".join(sorunlar)]
    return kart, sorunlar


def dunya_capasi(kart):
    """Her blokta ve her kolda harfi harfine aynı kalacak dünya/karakter çapası (İngilizce, ses tarifleriyle)."""
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
                "Continuity across blocks: every block after the first OPENS with the same framing, camera position, "
                "character positions and light as the last shot of the previous block, continuing from its calm "
                "final moment, so the join plays like one continuous take; change shot size only after the "
                "block's first shot.",
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


# ---------------- köprü ----------------

KOPRU_KURALI = """Bridge rule: <Picture {n}> is the final frame of the previous block. The first 1.5 seconds of this
block continue EXACTLY from that frame: the same framing and camera position, the same body poses, every object in the
same hand or in the same place, the same light; nothing new appears and nothing moves to a new place. Only after
1.5 seconds does the block's first new action begin. Never jump straight into a later step of an action."""


def kopru_istegi(istek, n_gorsel):
    """Köprülü bir bloğun istek metni: önceki bloğun son karesi <Picture n_gorsel> olarak verilir; bloğun ilk 1,5 sn'si
    o kareyi birebir sürdürür. (18.11.2026 mutfak: Gemini blok 3'e kendiliğinden 2 sn sabit bekleme koyunca 30. sn
    kesintisiz oldu; blok 2'de koymayınca 15. sn'de hareket sıçradı.)"""
    return f"{istek.rstrip()}\n\n{KOPRU_KURALI.format(n=n_gorsel)}"


# ---------------- referans görseller ----------------

def gorsel_listesi(kart, dizin):
    """Ref2VA görselleri, sırasıyla: konuşan karakterler (S1, S2… — normalize_roles numarasıyla eşleşir),
    sessiz karakterler, en son mekân. [{'id','dosya','rol','ad'}]"""
    karakterler = sorted(kart["karakterler"], key=lambda k: (not k.get("konusmaci"), k.get("konusmaci") or "", k["id"]))
    liste = [{"id": k["id"], "dosya": os.path.join(dizin, f"{k['id']}.png"), "rol": pw.ROLE_CHARACTER, "ad": k["ad"]}
             for k in karakterler]
    liste.append({"id": "MEKAN", "dosya": os.path.join(dizin, "MEKAN.png"), "rol": pw.ROLE_SCENE,
                  "ad": kart["mekan"].get("ad", "")})
    return liste


def gorsel_metni(kart, kimlik, style=config.DEFAULT_STYLE):
    """Bir karakterin ya da mekânın (kimlik='MEKAN') referans görseli için Gemini'ye gidecek metin."""
    s = config.STYLES[style]
    look = f"Style: {s['look']}. Avoid: {s['avoid']}." if s.get("look") else "Photorealistic, natural skin texture."
    if kimlik == "MEKAN":
        m = kart["mekan"]
        return MEKAN_GORSELI.format(kind=s["kind"], tarif=m["tarif"], isik=kart.get("zaman_isik", ""),
                                    palet=kart.get("renk_paleti", ""), look=look)
    k = next(x for x in kart["karakterler"] if x["id"] == kimlik)
    return PORTRE.format(kind=s["kind"], gorunum=k["gorunum"], kiyafet=k["kiyafet"], look=look)


def gorsel_uret(metin, api_key, hedef, models=None):
    """Gemini görsel modeliyle tek görsel üretir ve `hedef`e yazar; kullanılan modeli döner."""
    from google.genai import types
    modeller = list(models or pw.image_models(api_key))
    if not modeller:
        raise RuntimeError("Bu anahtarla görsel üretebilen Gemini modeli yok.")
    client = pw._client(api_key, pw.IMAGE_TIMEOUT_MS)
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
                    os.makedirs(os.path.dirname(os.path.abspath(hedef)), exist_ok=True)
                    with open(hedef, "wb") as f:
                        f.write(part.inline_data.data)
                    return model
        hatalar.append(f"{model}: görsel dönmedi")
    raise RuntimeError("Görsel üretilemedi: " + " | ".join(hatalar))


# ---------------- plan ----------------

def planla(kart, api_key, gorseller=(), kollar=("ref",), model=None, style=config.DEFAULT_STYLE, fikir="", log=print):
    """Kart (+ görseller) → çekim planı → her kol için blok prompt'ları.
    (plan, {kol: [{'blok','sure','istek','prompt','sorunlar'}]}, sorunlar) döner."""
    model = model or config.GEMINI_MODEL
    yollar = [g["dosya"] for g in gorseller]
    roller = [{"role": g["rol"], "name": g["ad"]} for g in gorseller]
    ref_var = "ref" in kollar
    toplam = sum(int(b["sure"]) for b in kart["bloklar"])
    plan, psorun = pw.plan_shots(plan_fikri(kart), toplam, api_key, model, images=yollar if ref_var else (),
                                 style=style, log=log, roles=roller if ref_var else None)
    if psorun:
        return plan, {}, [f"çekim planı: {s}" for s in psorun]
    plan["world_anchor"] = dunya_capasi(kart)
    return plan, *_kol_promptlari(plan, kollar, yollar, roller, style, fikir,
                                  lambda istek, sn, imgs, rls: pw.rewrite(istek, sn, api_key, model, imgs, log=log,
                                                                          style=style, roles=rls))


def _kol_promptlari(plan, kollar, yollar, roller, style, fikir, yaz):
    sonuc, sorunlar = {}, []
    for kol in kollar:
        imgs, rls = (yollar, roller) if kol == "ref" else ((), None)
        bloklar = []
        for binfo in pw.blocks_from_plan(plan):
            istek = pw.block_request(binfo, style=style, idea=fikir)
            prompt, sorun = yaz(istek, binfo["seconds"], imgs, rls)
            bloklar.append({"blok": binfo["block"], "sure": binfo["seconds"], "istek": istek,
                            "prompt": prompt, "sorunlar": list(sorun)})
            sorunlar += [f"[{kol}] blok {binfo['block']}: {s}" for s in sorun]
        sonuc[kol] = bloklar
    return sonuc, sorunlar


# ---------------- test / kuru deneme yardımcıları (Gemini'siz) ----------------

def ornek_kart(fikir, toplam):
    """Gemini'siz deneme kartı: fikirdeki tırnak içi metinler sırayla bloklara dağıtılır."""
    lits = re.findall(r'"([^"]+)"', fikir or "") or ["Merhaba."]
    n = blok_sayisi(toplam)
    sureler = [toplam // n + (1 if i < toplam % n else 0) for i in range(n)]
    return {
        "baslik": "Deneme",
        "karakterler": [{"id": "K1", "ad": "Çaycı", "konusmaci": "S1", "gorunum": "a man in his fifties",
                         "kiyafet": "white apron", "ses": "warm deep voice"}],
        "mekan": {"ad": "Çay bahçesi", "tarif": "a seaside tea garden"},
        "zaman_isik": "golden hour", "renk_paleti": "amber, teal",
        "bloklar": [{"blok": i + 1, "sure": s, "ozet": "the tea seller serves tea",
                     "replikler": [{"konusmaci": "S1", "metin": lits[i]}] if i < len(lits) else []}
                    for i, s in enumerate(sureler)],
    }


def ornek_plan(kart):
    shots = []
    for b in kart["bloklar"]:
        yarim = b["sure"] / 2
        sesler = " ".join(f'"{r["metin"]}"' for r in b.get("replikler") or [])
        shots += [{"block": b["blok"], "shot": 1, "start_sec": 0.0, "duration": yarim, "framing": "wide",
                   "action": b["ozet"], "camera": "static", "sound": sesler or "ambience"},
                  {"block": b["blok"], "shot": 2, "start_sec": yarim, "duration": b["sure"] - yarim,
                   "framing": "medium", "action": "calm hold", "camera": "static", "sound": "ambience"}]
    return {"world_anchor": dunya_capasi(kart), "shots": shots}


def ornek_planla(kart, kollar=("ref",), gorseller=(), style=config.DEFAULT_STYLE, fikir=""):
    """planla()'nın Gemini'siz karşılığı (kuru deneme ve testler için)."""
    plan = ornek_plan(kart)
    return plan, *_kol_promptlari(plan, kollar, [g["dosya"] for g in gorseller],
                                  [{"role": g["rol"], "name": g["ad"]} for g in gorseller], style, fikir,
                                  lambda *a: (pw.EXAMPLE_OUTPUT, []))


def ornek_png(yol, renk=(200, 180, 150), boyut=(64, 96)):
    """Bağımlılıksız küçük bir PNG (yalnızca deneme)."""
    w, h = boyut
    ham = b"".join(b"\x00" + bytes(renk) * w for _ in range(h))

    def parca(tur, veri):
        return struct.pack(">I", len(veri)) + tur + veri + struct.pack(">I", zlib.crc32(tur + veri) & 0xFFFFFFFF)
    os.makedirs(os.path.dirname(os.path.abspath(yol)), exist_ok=True)
    with open(yol, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + parca(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
                + parca(b"IDAT", zlib.compress(ham)) + parca(b"IEND", b""))
