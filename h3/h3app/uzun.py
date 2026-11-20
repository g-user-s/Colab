"""Uzun videonun GPU tarafı: hikâye kartından yazılmış blokları üretir, izler, birleştirir ve sürekliliği puanlar.

İki kullanım:
1. Parça parça (başsız ajan akışı, önerilen): `prepare` → her blok için `render_block` → `merge`. Gemini izlemesi,
   yeniden üretim kararı, süreklilik puanı ve köprü prompt'u çağıranın makinesinde yapılır; GPU makinesi Gemini'ye
   hiç gitmez (anahtar oraya taşınmaz).
2. Tek seferde: `generate` — hepsini aynı makinede yapar (Gemini anahtarı o makinede geçerliyse).

Kollar: ref (kimliği referans görseller taşır, Ref2VA) / metin (yalnızca dünya çapası metni, T2VA). Deneyde iki kol
aynı plan ve aynı seed'lerle üretilir. Köprü (deneysel): ref kolunda her bloğa önceki bloğun son karesi de sahne
görseli olarak verilir ve bloğun prompt'u o görselle yeniden yazılır.
"""

import json
import os
import shutil
import subprocess
import time

from . import assemble, comfy_client, config, graphs, prompt_writer as pw, qa, review, setup_env

_hazir = {}


def last_frame(video, dest):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-sseof", "-0.2", "-i", video, "-frames:v", "1", dest], check=True)
    return dest


def block_cuts(blocks):
    """Birleşik videoda blok sınırlarının zamanları (sn)."""
    cuts, t = [], 0.0
    for b in blocks[:-1]:
        t += config.frames_for(b["sure"]) / 24
        cuts.append(round(t, 2))
    return cuts


def _fake():
    return os.environ.get("H3APP_FAKE") == "1"


def prepare(method, with_refs=True, without_refs=False, log=print):
    """ComfyUI'yi ve gereken modelleri hazırlar (tekrar çağrılırsa hızlı geçer). Metin kodlayıcı rolünü döner."""
    if _fake():
        log("Test modu: kurulum atlandı.")
        return None
    key = (method, with_refs, without_refs)
    if key in _hazir:
        return _hazir[key]
    g = setup_env.gpu()
    if not g:
        raise RuntimeError("GPU yok.")
    log(f"GPU: {g[0]} ({g[1]} GB).")
    te = setup_env.text_encoder_role()
    setup_env.ensure_comfy(log=log)
    need = []
    for ref in ([True] if with_refs else []) + ([False] if without_refs else []):
        for r in setup_env.roles_for([method], te, ref):
            if r not in need:
                need.append(r)
    setup_env.ensure_models(need, log=log)
    comfy_client.start(log=log)
    _hazir[key] = te
    return te


def render_block(method, prompt, seed, seconds, resolution, style, name, refs=(), te=None, log=print, frames=None):
    """Bir bloğu üretir (refs verilirse Ref2VA; frames=(ilk, son) verilirse anahtar kareli FL2VA — biri None
    olabilir), sesi dengeler, otomatik kontrol yapar.
    {'yol','sure_sn','kontrol','temas','kirpinti'} döner."""
    width, height = config.RESOLUTIONS[resolution]
    out_dir = config.OUTPUT_DIR
    os.makedirs(out_dir, exist_ok=True)
    dest = os.path.join(out_dir, name)
    t0 = time.time()
    if _fake():
        time.sleep(0.2)
        shutil.copyfile(os.environ["H3APP_FAKE_VIDEO"], dest)
    else:
        names = []
        os.makedirs(os.path.join(config.COMFY_DIR, "input"), exist_ok=True)
        for p in refs:
            n = f"h3app_{os.path.basename(p)}"
            shutil.copyfile(p, os.path.join(config.COMFY_DIR, "input", n))
            names.append(n)
        kf = []
        for p in (frames or (None, None)):
            n = None
            if p:
                n = f"h3app_{os.path.basename(p)}"
                shutil.copyfile(p, os.path.join(config.COMFY_DIR, "input", n))
            kf.append(n)
        grf = graphs.build(method, prompt, seed, width, height, config.frames_for(seconds), te,
                           prefix=f"h3app/{name[:-4]}", ref_images=names, first_frame=kf[0], last_frame=kf[1])
        shown = 0
        for sec in comfy_client.run(grf, dest):
            if sec // 60 > shown:
                shown = sec // 60
                log(f"   … {shown} dk")
    qa.normalize_audio(dest)
    out = {"yol": dest, "sure_sn": int(time.time() - t0), "kontrol": None, "temas": None, "kirpinti": None}
    try:
        r = qa.check(dest, prompt, sheet=dest[:-4] + "_kontrol.jpg", crops=dest[:-4] + "_kirpinti.jpg", style=style)
        log("   " + qa.summary(r))
        out.update(kontrol={k: r[k] for k in ("kesmeler", "bulunamayan", "donmus", "lufs", "son_kayma")},
                   temas=r["temas"], kirpinti=r["kirpinti"])
    except Exception as e:  # noqa: BLE001
        log(f"   Kontrol yapılamadı: {e}")
    return out


def merge(files, dest, style, log=print):
    """Blokları kare-tam birleştirir (konuşmalı ses modu) ve birleşik videoyu kontrol eder."""
    res = assemble.assemble(list(files), dest, audio_mode="speech")
    out = {"yol": dest, "saniye": res.get("saniye"), "temas": None, "kirpinti": None}
    try:
        r = qa.check(dest, "", sheet=dest[:-4] + "_kontrol.jpg", crops=dest[:-4] + "_kirpinti.jpg", style=style)
        out.update(temas=r["temas"], kirpinti=r["kirpinti"])
    except Exception as e:  # noqa: BLE001
        log(f"   Birleşik kontrol yapılamadı: {e}")
    return out


def generate(arms, method, resolution, seed, style, refs=(), roles=None, bible=None, api_key=None, retries=0,
             bridge=False, experiment=False, log=print):
    """Hepsini tek makinede yapar. arms: {kol: [{'blok','sure','istek','prompt'}]}; refs: Ref2VA görsel yolları.
    {'secilen', 'dosyalar', 'temel', 'ozet'} döner."""
    fake = _fake()
    stamp = time.strftime("%Y%m%d_%H%M%S")
    out_dir = config.OUTPUT_DIR
    refs, roles = list(refs or []), list(roles or [])
    retries = max(0, min(3, int(retries)))
    watch = bool(api_key) and not fake
    bridge = bool(bridge) and (bool(api_key) or fake)
    te = prepare(method, with_refs="ref" in arms, without_refs=any(a != "ref" for a in arms), log=log)
    files, essential = [], []
    summary = {"deney": bool(experiment), "kollar": {}}
    mfile = config.METHODS[method]["file"]
    for arm, blocks in arms.items():
        use_refs = arm == "ref"
        log(f"━━ Kol: {arm} ({'görsel referanslı, Ref2VA' if use_refs else 'yalnızca metin çapası'}) ━━")
        a_imgs, a_roles = (refs, roles or None) if use_refs else ([], None)
        chosen, arm_summary = [], []
        for b in blocks:
            n, seconds = b["blok"], b["sure"]
            prompt, b_imgs, b_roles = b["prompt"], list(a_imgs), a_roles
            if bridge and use_refs and chosen and len(a_imgs) < config.MAX_REF_IMAGES:
                frame = last_frame(chosen[-1], os.path.join(out_dir, f"{stamp}_{arm}_blok{n}_kopru.png"))
                b_imgs = a_imgs + [frame]
                b_roles = (a_roles or []) + [{"role": pw.ROLE_SCENE, "name": "final frame of the previous block"}]
                log(f"🔗 Blok {n}: önceki bloğun son karesi sahne görseli olarak eklendi; prompt yeniden yazılıyor")
                if fake:
                    log("   Test modu: prompt yeniden yazılmadı.")
                else:
                    from . import hikaye
                    prompt, probs = pw.rewrite(hikaye.kopru_istegi(b["istek"], len(b_imgs)), seconds, api_key,
                                               config.GEMINI_MODEL, b_imgs, log=log,
                                               style=style, roles=b_roles)
                    if probs:
                        log(f"   ⚠️ Köprü prompt'unda uyarı: {' | '.join(probs)}")
                files.append(frame)
            pfile = os.path.join(out_dir, f"{stamp}_{arm}_blok{n}_prompt.txt")
            with open(pfile, "w", encoding="utf-8") as f:
                f.write(prompt.strip() + "\n")
            essential.append(pfile)
            cands = []
            for attempt in range(retries + 1):
                s = int(seed) + (n - 1) + 1000 * attempt
                name = f"{stamp}_{arm}_blok{n}_{mfile}_seed{s}.mp4"
                log(f"▶ [{arm}] Blok {n}/{len(blocks)} · {seconds} sn · seed {s}")
                r = render_block(method, prompt, s, seconds, resolution, style, name, b_imgs, te, log)
                files += [x for x in (r["yol"], r["temas"], r["kirpinti"]) if x]
                cand = {"dosya": name, "yol": r["yol"], "seed": s, "sure_sn": r["sure_sn"], "inceleme": None}
                if watch:
                    cand["inceleme"] = review.review_video(r["yol"], prompt, api_key, b_imgs, b_roles, log=log)
                    log("   " + review.summary(cand["inceleme"]))
                cands.append(cand)
                if not review.blocking(cand["inceleme"]):
                    break
                if attempt < retries:
                    log(f"🔁 Blok {n}: yüksek önemde kusur; yeni seed ile yeniden üretiliyor")
            best = min(cands, key=lambda c: review.score(c["inceleme"])) if watch else cands[-1]
            chosen.append(best["yol"])
            essential.append(best["yol"][:-4] + "_kontrol.jpg")
            arm_summary.append({"blok": n, "secilen": best["dosya"], "seed": best["seed"],
                                "inceleme": review.short(best["inceleme"]) if watch else "atlandı",
                                "adaylar": [{k: c.get(k) for k in ("dosya", "seed", "sure_sn", "inceleme")}
                                            for c in cands]})
        log(f"🎬 [{arm}] {len(chosen)} blok birleştiriliyor")
        m = merge(chosen, os.path.join(out_dir, f"{stamp}_{arm}_{mfile}_birlesik.mp4"), style, log)
        if m["temas"]:
            essential.append(m["temas"])
        if m["kirpinti"]:
            files.append(m["kirpinti"])
        cuts = block_cuts(blocks)
        cont = None
        if watch:
            log(f"🎞️ [{arm}] Süreklilik izleniyor")
            cont = review.continuity_review(m["yol"], cuts, bible or {}, api_key, log=log)
        essential.append(m["yol"])
        summary["kollar"][arm] = {"birlesik": os.path.basename(m["yol"]), "saniye": m["saniye"],
                                  "bloklar": arm_summary, "sureklilik": cont, "blok_kesmeleri": cuts}
    if experiment:
        summary["karsilastirma"] = {k: (v["sureklilik"] or {}).get("ortalama") for k, v in summary["kollar"].items()}
        log(f"⚖️ Deney sonucu (süreklilik ortalaması): {summary['karsilastirma']}")
    result_file = os.path.join(out_dir, f"{stamp}_uzun_sonuc.json")
    with open(result_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    essential.insert(0, result_file)
    main_arm = "ref" if "ref" in summary["kollar"] else next(iter(summary["kollar"]))
    return {"secilen": os.path.join(out_dir, summary["kollar"][main_arm]["birlesik"]), "dosyalar": files,
            "temel": essential, "ozet": summary}
