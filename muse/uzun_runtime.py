"""Uzun video üretimi (Colab runtime'ında, runtime_runner.py tarafından çağrılır).

Her kol (ref: kimliği görseller taşır / metin: yalnızca metin çapası) için bloklar sırayla üretilir:
  render → ses dengeleme → otomatik kontrol → Gemini izlemesi → (kusur varsa) yeni seed ile yeniden üretim
Sonra bloklar birleştirilir ve birleşik video bir "süreklilik" izlemesinden geçer: kimlik, kıyafet, mekân, ses
ve hikâye blok sınırlarında tutarlı mı (1–10 puan). Deneyde iki kol aynı plan ve aynı seed'lerle üretilir.

Yalnızca h3app'in kendi fonksiyonları kullanılır; h3app'te değişiklik yoktur.
"""

import json
import os
import shutil
import subprocess
import time

SURECLILIK = """You are a film continuity supervisor. The clip was generated in {n} separate blocks and joined at
these times (seconds): {cuts}. Watch the whole clip and LISTEN to it. Judge ONLY whether things that should stay the
same really stay the same across the block boundaries and through the clip, compared with the story bible below.
Score each from 1 (badly broken) to 10 (perfectly consistent):
- kimlik: each character is clearly the same person (face, age, hair, build)
- kiyafet: outfits, colours and accessories stay the same
- mekan: the place, its layout, props and light stay the same
- ses: each speaker keeps the same voice (timbre, pitch, accent); lines are spoken by the right person
- hikaye: the events and lines follow the story bible in order, and the joins feel like intended cuts
List concrete problems with timestamps. Do not invent problems. Answer ONLY with JSON:
{{"kimlik": int, "kiyafet": int, "mekan": int, "ses": int, "hikaye": int,
  "sorunlar": [{{"zaman_s": number, "alan": string, "aciklama": string}}], "ozet": string}}

Story bible:
{bible}"""
PUANLAR = ("kimlik", "kiyafet", "mekan", "ses", "hikaye")


def son_kare(video, hedef):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-sseof", "-0.2", "-i", video, "-frames:v", "1", hedef], check=True)
    return hedef


def sureklilik_izle(video, kesmeler, hikaye, anahtar, say):
    """Birleşik videoyu süreklilik açısından izletir. Gemini yanıt vermezse None."""
    from google.genai import types
    from h3app import config, prompt_writer as pw, review
    import tempfile
    sistem = SURECLILIK.format(n=len(kesmeler) + 1, cuts=", ".join(f"{k:.2f}" for k in kesmeler) or "none",
                               bible=json.dumps(hikaye, ensure_ascii=False, indent=1))
    with tempfile.TemporaryDirectory(prefix="h3muse_surek_") as tmp:
        veri = open(review._proxy(video, tmp), "rb").read()
    parcalar = [types.Part.from_bytes(data=veri, mime_type="video/mp4"), "Judge the continuity of this clip."]
    cfg = types.GenerateContentConfig(system_instruction=sistem, temperature=0.1,
                                      response_mime_type="application/json")
    for m in pw.available(config.REVIEW_MODELS):
        try:
            client = pw._client(anahtar, review.TIMEOUT_MS)
            sonuc = pw._parse_json(client.models.generate_content(model=m, contents=parcalar, config=cfg).text or "")
            for k in PUANLAR:
                sonuc[k] = max(1, min(10, int(sonuc.get(k) or 0))) if sonuc.get(k) is not None else None
            gecerli = [sonuc[k] for k in PUANLAR if sonuc.get(k)]
            sonuc["ortalama"] = round(sum(gecerli) / len(gecerli), 2) if gecerli else None
            sonuc["model"] = m
            return sonuc
        except Exception as e:  # noqa: BLE001
            if pw.gone(e):
                pw.mark_gone(m, say)
                continue
            say(f"   🎞️ {m} sürekliliği izleyemedi ({str(e)[:120]})")
    return None


def calistir(senaryo, anahtar, say):
    """Uzun videoyu üretir. {'secilen', 'dosyalar', 'temel', 'ozet'} döner."""
    from h3app import assemble, comfy_client, config, graphs, prompt_writer as pw, qa, review, setup_env
    fake = os.environ.get("H3APP_FAKE") == "1"
    yontem, stil = senaryo["yontem"], senaryo["stil"]
    width, height = config.RESOLUTIONS[senaryo["cozunurluk"]]
    stamp = time.strftime("%Y%m%d_%H%M%S")
    cikti = config.OUTPUT_DIR
    os.makedirs(cikti, exist_ok=True)
    kollar = senaryo["kollar"]
    dizin = os.path.dirname(os.path.abspath(senaryo["_yol"]))
    gorseller = []          # runtime'daki yollar, Ref2VA sırasıyla
    for i, r in enumerate(senaryo.get("referanslar") or [], 1):
        gorseller.append(os.path.join(dizin, f"ref_{i}{os.path.splitext(r['dosya'])[1].lower() or '.png'}"))
    roller = [{"role": r["rol"], "name": r.get("ad", "")} for r in senaryo.get("referanslar") or []]
    yeniden = max(0, min(3, int(senaryo.get("yeniden_uretim", 0))))
    kopru = bool(senaryo.get("kopru")) and (bool(anahtar) or fake)
    if senaryo.get("kopru") and not kopru:
        say("⚠️ Köprü için Gemini anahtarı gerekli; köprü kapalı.")
    dosyalar, temel = [], []

    te = None
    if fake:
        say("Test modu: kurulum atlandı.")
    else:
        g = setup_env.gpu()
        if not g:
            raise RuntimeError("GPU yok.")
        say(f"GPU: {g[0]} ({g[1]} GB).")
        te = setup_env.text_encoder_role()
        setup_env.ensure_comfy(log=say)
        roller_model = []
        for kol in kollar.values():
            for r in setup_env.roles_for([yontem], te, kol["ref"]):
                if r not in roller_model:
                    roller_model.append(r)
        setup_env.ensure_models(roller_model, log=say)
        comfy_client.start(log=say)

    def comfy_girdi(yol, ad):
        if fake:
            return ad
        os.makedirs(os.path.join(config.COMFY_DIR, "input"), exist_ok=True)
        shutil.copyfile(yol, os.path.join(config.COMFY_DIR, "input", ad))
        return ad

    ref_adlar = [comfy_girdi(p, f"h3muse_{stamp}_{i + 1}{os.path.splitext(p)[1]}") for i, p in enumerate(gorseller)]

    def render(prompt, seed, sure, ad, refs):
        hedef = os.path.join(cikti, ad)
        t0 = time.time()
        if fake:
            time.sleep(0.2)
            shutil.copyfile(os.environ["H3APP_FAKE_VIDEO"], hedef)
        else:
            grf = graphs.build(yontem, prompt, seed, width, height, config.frames_for(sure), te,
                               prefix=f"h3app/{ad[:-4]}", ref_images=refs)
            gosterilen = 0
            for sn in comfy_client.run(grf, hedef):
                if sn // 60 > gosterilen:
                    gosterilen = sn // 60
                    say(f"   … {gosterilen} dk")
        qa.normalize_audio(hedef)
        return hedef, int(time.time() - t0)

    ozet = {"deney": bool(senaryo.get("deney")), "kollar": {}}
    for kol_ad, kol in kollar.items():
        say(f"━━ Kol: {kol_ad} ({'görsel referanslı, Ref2VA' if kol['ref'] else 'yalnızca metin çapası'}) ━━")
        k_gorsel = gorseller if kol["ref"] else []
        k_rol = roller if kol["ref"] else None
        k_ref = ref_adlar if kol["ref"] else []
        secilenler, kol_ozet = [], []
        for b in kol["bloklar"]:
            n, sure = b["blok"], b["sure"]
            prompt, b_gorsel, b_rol, b_ref = b["prompt"], list(k_gorsel), k_rol, list(k_ref)
            if kopru and kol["ref"] and secilenler and len(k_gorsel) < config.MAX_REF_IMAGES:
                kare = son_kare(secilenler[-1], os.path.join(cikti, f"{stamp}_{kol_ad}_blok{n}_kopru.png"))
                b_gorsel = k_gorsel + [kare]
                b_rol = (k_rol or []) + [{"role": "arka_plan", "name": "final frame of the previous block (continuity)"}]
                b_ref = k_ref + [comfy_girdi(kare, os.path.basename(kare))]
                say(f"🔗 Blok {n}: önceki bloğun son karesi sahne görseli olarak eklendi; prompt yeniden yazılıyor")
                if fake:
                    say("   Test modu: prompt yeniden yazılmadı.")
                else:
                    prompt, sorun = pw.rewrite(b["istek"], sure, anahtar, config.GEMINI_MODEL, b_gorsel, log=say,
                                               style=stil, roles=b_rol)
                    if sorun:
                        say(f"   ⚠️ Köprü prompt'unda uyarı: {' | '.join(sorun)}")
                dosyalar.append(kare)
            pfile = os.path.join(cikti, f"{stamp}_{kol_ad}_blok{n}_prompt.txt")
            open(pfile, "w", encoding="utf-8").write(prompt.strip() + "\n")
            temel.append(pfile)
            adaylar = []
            for deneme in range(yeniden + 1):
                seed = int(senaryo["seed"]) + (n - 1) + 1000 * deneme
                ad = f"{stamp}_{kol_ad}_blok{n}_{config.METHODS[yontem]['file']}_seed{seed}.mp4"
                say(f"▶ [{kol_ad}] Blok {n}/{len(kol['bloklar'])} · {sure} sn · seed {seed}")
                hedef, sure_sn = render(prompt, seed, sure, ad, b_ref)
                dosyalar.append(hedef)
                aday = {"dosya": ad, "yol": hedef, "seed": seed, "sure_sn": sure_sn, "inceleme": None}
                try:
                    r = qa.check(hedef, prompt, sheet=hedef[:-4] + "_kontrol.jpg", crops=hedef[:-4] + "_kirpinti.jpg",
                                 style=stil)
                    say("   " + qa.summary(r))
                    aday["kontrol"] = {k: r[k] for k in ("kesmeler", "bulunamayan", "donmus", "lufs", "son_kayma")}
                    dosyalar += [r["temas"], r["kirpinti"]]
                except Exception as e:  # noqa: BLE001
                    say(f"   Kontrol yapılamadı: {e}")
                if anahtar and not fake:
                    aday["inceleme"] = review.review_video(hedef, prompt, anahtar, b_gorsel, b_rol, log=say)
                    say("   " + review.summary(aday["inceleme"]))
                adaylar.append(aday)
                if not review.blocking(aday["inceleme"]):
                    break
                if deneme < yeniden:
                    say(f"🔁 Blok {n}: yüksek önemde kusur; yeni seed ile yeniden üretiliyor")
            en_iyi = min(adaylar, key=lambda c: review.score(c["inceleme"])) if anahtar and not fake else adaylar[-1]
            secilenler.append(en_iyi["yol"])
            temel.append(en_iyi["yol"][:-4] + "_kontrol.jpg")
            kol_ozet.append({"blok": n, "secilen": en_iyi["dosya"], "seed": en_iyi["seed"],
                             "inceleme": review.short(en_iyi["inceleme"]) if anahtar and not fake else "atlandı",
                             "adaylar": [{k: c.get(k) for k in ("dosya", "seed", "sure_sn", "inceleme")}
                                         for c in adaylar]})
        birlesik = os.path.join(cikti, f"{stamp}_{kol_ad}_{config.METHODS[yontem]['file']}_birlesik.mp4")
        say(f"🎬 [{kol_ad}] {len(secilenler)} blok birleştiriliyor")
        res = assemble.assemble(secilenler, birlesik, audio_mode="speech")
        kesmeler, t = [], 0.0
        for b in kol["bloklar"][:-1]:
            t += config.frames_for(b["sure"]) / 24
            kesmeler.append(round(t, 2))
        surek = None
        try:
            r = qa.check(birlesik, "", sheet=birlesik[:-4] + "_kontrol.jpg", crops=birlesik[:-4] + "_kirpinti.jpg",
                         style=stil)
            temel += [r["temas"]]
            dosyalar.append(r["kirpinti"])
        except Exception as e:  # noqa: BLE001
            say(f"   Birleşik kontrol yapılamadı: {e}")
        if anahtar and not fake:
            say(f"🎞️ [{kol_ad}] Süreklilik izleniyor")
            surek = sureklilik_izle(birlesik, kesmeler, senaryo.get("hikaye") or {}, anahtar, say)
            if surek:
                say(f"   Süreklilik [{kol_ad}]: " + ", ".join(f"{k} {surek.get(k)}" for k in PUANLAR)
                    + f" · ortalama {surek.get('ortalama')}")
        temel.append(birlesik)
        ozet["kollar"][kol_ad] = {"birlesik": os.path.basename(birlesik), "saniye": res.get("saniye"),
                                  "bloklar": kol_ozet, "sureklilik": surek, "blok_kesmeleri": kesmeler}
    if ozet["deney"]:
        puan = {k: (v["sureklilik"] or {}).get("ortalama") for k, v in ozet["kollar"].items()}
        ozet["karsilastirma"] = puan
        say(f"⚖️ Deney sonucu (süreklilik ortalaması): {puan}")
    sonuc_yol = os.path.join(cikti, f"{stamp}_uzun_sonuc.json")
    with open(sonuc_yol, "w", encoding="utf-8") as f:
        json.dump(ozet, f, ensure_ascii=False, indent=2)
    temel.insert(0, sonuc_yol)
    secilen_kol = "ref" if "ref" in ozet["kollar"] else next(iter(ozet["kollar"]))
    secilen = os.path.join(cikti, ozet["kollar"][secilen_kol]["birlesik"])
    return {"secilen": secilen, "dosyalar": dosyalar, "temel": temel, "ozet": ozet}
