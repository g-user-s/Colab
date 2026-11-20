"""Anahtar kare yöntemi (FL2VA): her çekimin ilk ve son karesi önceden görsel olarak üretilir, H3 iki kare arasını
doldurur. Kompozisyon, kimlik ve kamera açısı görselden gelir; çekimler kısa (5-15 sn) ve tek çekimdir.

Kaynak: MiniMax H3 resmî rehberi (base-en, FL2VA: ilk satır hizalama talimatı, ardından üç bölüm; tek çekim önerilir)
ve ComfyUI `MiniMaxH3ImageToVideo` düğümü (first_frame tuvale gerilir, last_frame ortalanıp kırpılır; bu yüzden kareler
önceden tam çözünürlüğe kırpılır). Son kare ipucu: son kare sıfırdan üretilmez, ilk kare taban verilip yalnızca
değişen şey tarif edilir; böylece kamera açısı kilitli kalır.

Görsel üretimi çağıranın makinesinde (Gemini), video üretimi GPU'da yapılır.
"""

import mimetypes
import os
import re
import subprocess

from . import config, prompt_writer as pw

ALANLAR = ("integrated_multimodal_description:", "overall_soundscape:", "non_diegetic_music:")

KARE_KURALI = """You are a film still photographer. Produce ONE {kind} 16:9 landscape film frame (a single frame from
a feature film, not a poster): natural light, real lens perspective, film grain, no frame border.
{look}
Identity rules: every named person must match the reference image given for them exactly (face, age, beard, hair,
clothing, armour, colours, horse). People who have no reference image are ordinary background extras.
No readable text, letters, calligraphy, logos, subtitles or watermark anywhere. No blood, wounds or corpses."""

TABAN_KURALI = """The image labelled BASE FRAME is the first frame of the same continuous shot. Keep EXACTLY its camera
position, lens, height, framing, horizon, lighting, colours, place and the identity and clothing of every person;
change ONLY what is described below, as it looks a few seconds later in the same shot."""

ANA_KURALI = """The image labelled MASTER PLATE is the canonical view of this place for the whole film. Keep its
architecture EXACTLY: the shape, size, materials, banding, damage and decoration of every wall, arch, tower and house,
the fresco, the paving, the colours of the banners and the positions of the cordon and the crowd. Only the camera
position and the people may differ, exactly as described below; never redesign the place."""

KOMPOZISYON_KURALI = """The image labelled COMPOSITION is a reference for the layout only (camera angle, where the
main figures stand, what fills the background). Recreate that arrangement as a real photograph of the people and the
place in the other references. Do not copy its painting style, brushwork, colours or any detail that the description
below does not mention; never copy dead, wounded or lying bodies."""


def hizala(kaynak, hedef, genislik, yukseklik):
    """Görseli tam çözünürlüğe ortadan kırpar (H3 ilk kareyi orantısız gerer)."""
    os.makedirs(os.path.dirname(os.path.abspath(hedef)) or ".", exist_ok=True)
    vf = f"scale={genislik}:{yukseklik}:force_original_aspect_ratio=increase,crop={genislik}:{yukseklik}"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", kaynak, "-vf", vf, "-frames:v", "1", hedef], check=True)
    return hedef


def kare_metni(tarif, style=config.DEFAULT_STYLE, taban=False, kompozisyon=False, ana=False):
    s = config.STYLES[style]
    look = f"Style: {s['look']}. Avoid: {s['avoid']}." if s.get("look") else "Photorealistic, natural skin texture."
    parcalar = [KARE_KURALI.format(kind=s["kind"], look=look)]
    if taban:
        parcalar.append(TABAN_KURALI)
    if ana:
        parcalar.append(ANA_KURALI)
    if kompozisyon:
        parcalar.append(KOMPOZISYON_KURALI)
    parcalar.append("The frame:\n" + tarif.strip())
    return "\n\n".join(parcalar)


def kare_uret(metin, api_key, hedef, girdiler=(), boyut=(1344, 768), models=None):
    """Gemini görsel modeliyle bir anahtar kare üretir, `boyut`a kırpıp `hedef`e (PNG) yazar; kullanılan modeli döner.
    girdiler: [(etiket, yol)] — 'BASE FRAME', 'COMPOSITION' ya da kişinin/mekânın adı."""
    from google.genai import types
    icerik = [metin]
    for etiket, yol in girdiler:
        icerik.append(f"Reference image — {etiket}:")
        icerik.append(types.Part.from_bytes(data=open(yol, "rb").read(),
                                            mime_type=mimetypes.guess_type(yol)[0] or "image/png"))
    modeller = list(models or pw.image_models(api_key))
    if not modeller:
        raise RuntimeError("Bu anahtarla görsel üretebilen Gemini modeli yok.")
    client = pw._client(api_key, pw.IMAGE_TIMEOUT_MS)
    hatalar = []
    for model in modeller[:2]:
        for oran in (True, False):
            kw = {"image_config": types.ImageConfig(aspect_ratio="16:9")} if oran else {}
            cfg = types.GenerateContentConfig(response_modalities=["IMAGE", "TEXT"], temperature=1.0, **kw)
            try:
                resp = client.models.generate_content(model=model, contents=icerik, config=cfg)
            except Exception as e:  # noqa: BLE001
                hatalar.append(f"{model}{'' if oran else ' (oransız)'}: {str(e)[:150]}")
                continue
            for cand in resp.candidates or []:
                for part in (cand.content.parts if cand.content else None) or []:
                    if getattr(part, "inline_data", None) and part.inline_data.data:
                        ham = hedef[:-4] + "_ham" + (mimetypes.guess_extension(part.inline_data.mime_type or "")
                                                     or ".png")
                        os.makedirs(os.path.dirname(os.path.abspath(hedef)), exist_ok=True)
                        with open(ham, "wb") as f:
                            f.write(part.inline_data.data)
                        hizala(ham, hedef, *boyut)
                        return model
            hatalar.append(f"{model}: görsel dönmedi")
            break
    raise RuntimeError("Kare üretilemedi: " + " | ".join(hatalar))


def sure_sn(saniye):
    """Çekimin gerçek süresi (kare ızgarasına yuvarlanmış)."""
    return config.frames_for(saniye) / 24


def hizalama_satiri(saniye, ilk=True, son=True):
    """Rehberin FL2VA / I2VA / L2VA talimat satırı (prompt'un ilk satırı). Görsel sırası: ilk, son."""
    t = f"{sure_sn(saniye):.2f}"
    if ilk and son:
        return ("How the reference pictures align with the target video — Picture 1 (from Shot 1) aligns with the "
                f"0.00-second mark of the target video; Picture 2 (from Shot 1) aligns with the {t}-second mark of "
                "the target video.")
    if ilk:
        return "For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced."
    if son:
        return f"How the reference pictures align with the target video — <Picture 1> (from [Shot 1]) aligns with the {t}-second mark of the target video."
    return ""


def prompt_kur(saniye, aciklama, ses, muzik="N/A", ilk=True, son=True):
    satir = hizalama_satiri(saniye, ilk, son)
    govde = (f"integrated_multimodal_description: {aciklama.strip()}\n\noverall_soundscape: {ses.strip()}\n\n"
             f"non_diegetic_music: {muzik.strip() or 'N/A'}")
    return (satir + "\n\n" + govde) if satir else govde


def kontrol(prompt, saniye, ilk=True, son=True, replikler=()):
    """FL2VA prompt'unun rehbere uygunluğu; boş liste = kullanılabilir."""
    sorun = []
    satir = hizalama_satiri(saniye, ilk, son)
    if satir and not prompt.startswith(satir + "\n\n"):
        sorun.append("İlk satır rehberin hizalama talimatı olmalı ve ardından bir boş satır gelmeli.")
    poz = [prompt.find(a) for a in ALANLAR]
    if any(p < 0 for p in poz):
        sorun.append("Eksik bölüm: " + ", ".join(a for a, p in zip(ALANLAR, poz) if p < 0))
    elif poz != sorted(poz):
        sorun.append("Bölümlerin sırası yanlış.")
    govde = prompt[poz[0]:poz[1]] if all(p >= 0 for p in poz) else prompt
    if "[Shot 1]" not in govde:
        sorun.append("Açıklama [Shot 1] ile başlamalı.")
    if re.search(r"\[Shot (?:[2-9]|1\d)\]", prompt):
        sorun.append("Anahtar kare yönteminde her çekim tek çekimdir; [Shot 2] olmamalı.")
    for z in re.findall(r"At (\d\d):(\d\d)\.(\d\d\d)", govde):
        if int(z[0]) * 60 + int(z[1]) + int(z[2]) / 1000 > sure_sn(saniye):
            sorun.append(f"Zaman damgası çekim süresini aşıyor: {':'.join(z)}")
    for r in replikler:
        if r and r not in prompt:
            sorun.append(f'Replik harfi harfine yok: "{r}"')
    for d in re.findall(r"<d>(.*?)</d>", prompt, re.S):
        if not re.match(r"\[[A-Za-z]+\] ", d):
            sorun.append("Her <d> bloğu [Dil] etiketiyle başlamalı.")
    if config.frames_for(saniye) < 124:
        sorun.append(f"Çekim çok kısa ({saniye} sn); H3'ün eğitildiği aralık 124-362 kare (~5,2-15 sn).")
    if "```" in prompt:
        sorun.append("Kod bloğu işareti var.")
    return sorun


def kare_denetle(kareler, mekan_etiketi="MEKAN"):
    """Kare listesinin tutarlılık sorunları (boş liste = iyi):
    - taban/ana önce üretilmiş olmalı;
    - mekânı gören kareler mekânı birbirinden bağımsız çizmemeli. 20.11.2026 Fatih kare: her kare mekân görselinden
      ayrı ayrı çizilince kapı her çekimde başka bir yapıya dönüştü. Mekânı gören her kare ya bir tabandan ya da bir
      ana kareden (plaka) türetilmeli; bağımsız çizilen en fazla bir kök olabilir (o da ana kare olmalı)."""
    sorun, sira = [], {k["id"]: i for i, k in enumerate(kareler)}
    for k in kareler:
        for alan in ("taban", "ana"):
            x = k.get(alan)
            if x and x not in sira:
                sorun.append(f"{k['id']}: {alan} '{x}' listede yok.")
            elif x and sira[x] > sira[k["id"]]:
                sorun.append(f"{k['id']}: {alan} '{x}' ondan sonra üretiliyor; önce gelmeli.")
    kokler = [k["id"] for k in kareler if not k.get("taban") and not k.get("ana")
              and any(mekan_etiketi in str(g.get("etiket", "")) or os.path.basename(str(g.get("dosya", ""))).startswith(mekan_etiketi)
                      for g in k.get("girdiler") or [])]
    if len(kokler) > 1:
        sorun.append("Mekânı birbirinden bağımsız çizen kareler: " + ", ".join(kokler) + ". Mekân her seferinde farklı "
                     "çizilir; bir ana kare (\"plaka\": true) üretip bu karelere \"ana\" ya da \"taban\" olarak ver.")
    return sorun
