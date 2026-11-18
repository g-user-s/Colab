"""Uzun videonun GPU tarafı: hikâye kartından yazılmış blokları üretir, izler, birleştirir ve sürekliliği puanlar.

Her kol (ref: kimliği referans görseller taşır, Ref2VA / metin: yalnızca dünya çapası metni, T2VA) için bloklar
sırayla: render → ses dengeleme → otomatik kontrol → Gemini izlemesi → kusur varsa yeni seed ile yeniden üretim.
Sonra bloklar kare-tam birleştirilir ve birleşik video `review.continuity_review` ile puanlanır.
Deneyde iki kol aynı plan ve aynı seed'lerle üretilir; fark yalnızca yöntemdir.

Köprü (deneysel): ref kolunda her bloğa önceki bloğun son karesi de sahne görseli olarak verilir ve bloğun prompt'u
o görselle yeniden yazılır.
"""

import json
import os
import shutil
import subprocess
import time

from . import assemble, comfy_client, config, graphs, prompt_writer as pw, qa, review, setup_env


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


def generate(arms, method, resolution, seed, style, refs=(), roles=None, bible=None, api_key=None, retries=0,
             bridge=False, experiment=False, log=print):
    """arms: {kol: [{'blok','sure','istek','prompt'}]}; refs: referans görsel yolları (Ref2VA sırasıyla).
    {'secilen', 'dosyalar', 'temel', 'ozet'} döner: secilen = ref kolunun (yoksa ilk kolun) birleşik videosu,
    temel = her durumda teslim edilmesi gereken dosyalar."""
    fake = os.environ.get("H3APP_FAKE") == "1"
    width, height = config.RESOLUTIONS[resolution]
    stamp = time.strftime("%Y%m%d_%H%M%S")
    out_dir = config.OUTPUT_DIR
    os.makedirs(out_dir, exist_ok=True)
    refs, roles = list(refs or []), list(roles or [])
    retries = max(0, min(3, int(retries)))
    watch = bool(api_key) and not fake
    bridge = bool(bridge) and (bool(api_key) or fake)
    files, essential = [], []

    te = None
    if fake:
        log("Test modu: kurulum atlandı.")
    else:
        g = setup_env.gpu()
        if not g:
            raise RuntimeError("GPU yok.")
        log(f"GPU: {g[0]} ({g[1]} GB).")
        te = setup_env.text_encoder_role()
        setup_env.ensure_comfy(log=log)
        need = []
        for arm in arms:
            for r in setup_env.roles_for([method], te, arm == "ref"):
                if r not in need:
                    need.append(r)
        setup_env.ensure_models(need, log=log)
        comfy_client.start(log=log)

    def to_comfy(path, name):
        if not fake:
            os.makedirs(os.path.join(config.COMFY_DIR, "input"), exist_ok=True)
            shutil.copyfile(path, os.path.join(config.COMFY_DIR, "input", name))
        return name

    ref_names = [to_comfy(p, f"h3app_{stamp}_{i + 1}{os.path.splitext(p)[1]}") for i, p in enumerate(refs)]

    def render(prompt, s, seconds, name, ref_imgs):
        dest = os.path.join(out_dir, name)
        t0 = time.time()
        if fake:
            time.sleep(0.2)
            shutil.copyfile(os.environ["H3APP_FAKE_VIDEO"], dest)
        else:
            grf = graphs.build(method, prompt, s, width, height, config.frames_for(seconds), te,
                               prefix=f"h3app/{name[:-4]}", ref_images=ref_imgs)
            shown = 0
            for sec in comfy_client.run(grf, dest):
                if sec // 60 > shown:
                    shown = sec // 60
                    log(f"   … {shown} dk")
        qa.normalize_audio(dest)
        return dest, int(time.time() - t0)

    summary = {"deney": bool(experiment), "kollar": {}}
    mfile = config.METHODS[method]["file"]
    for arm, blocks in arms.items():
        use_refs = arm == "ref"
        log(f"━━ Kol: {arm} ({'görsel referanslı, Ref2VA' if use_refs else 'yalnızca metin çapası'}) ━━")
        a_imgs, a_roles, a_names = (refs, roles or None, ref_names) if use_refs else ([], None, [])
        chosen, arm_summary = [], []
        for b in blocks:
            n, seconds = b["blok"], b["sure"]
            prompt, b_imgs, b_roles, b_names = b["prompt"], list(a_imgs), a_roles, list(a_names)
            if bridge and use_refs and chosen and len(a_imgs) < config.MAX_REF_IMAGES:
                frame = last_frame(chosen[-1], os.path.join(out_dir, f"{stamp}_{arm}_blok{n}_kopru.png"))
                b_imgs = a_imgs + [frame]
                b_roles = (a_roles or []) + [{"role": pw.ROLE_SCENE, "name": "final frame of the previous block"}]
                b_names = a_names + [to_comfy(frame, os.path.basename(frame))]
                log(f"🔗 Blok {n}: önceki bloğun son karesi sahne görseli olarak eklendi; prompt yeniden yazılıyor")
                if fake:
                    log("   Test modu: prompt yeniden yazılmadı.")
                else:
                    prompt, probs = pw.rewrite(b["istek"], seconds, api_key, config.GEMINI_MODEL, b_imgs, log=log,
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
                dest, took = render(prompt, s, seconds, name, b_names)
                files.append(dest)
                cand = {"dosya": name, "yol": dest, "seed": s, "sure_sn": took, "inceleme": None}
                try:
                    r = qa.check(dest, prompt, sheet=dest[:-4] + "_kontrol.jpg", crops=dest[:-4] + "_kirpinti.jpg",
                                 style=style)
                    log("   " + qa.summary(r))
                    cand["kontrol"] = {k: r[k] for k in ("kesmeler", "bulunamayan", "donmus", "lufs", "son_kayma")}
                    files += [r["temas"], r["kirpinti"]]
                except Exception as e:  # noqa: BLE001
                    log(f"   Kontrol yapılamadı: {e}")
                if watch:
                    cand["inceleme"] = review.review_video(dest, prompt, api_key, b_imgs, b_roles, log=log)
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
        merged = os.path.join(out_dir, f"{stamp}_{arm}_{mfile}_birlesik.mp4")
        log(f"🎬 [{arm}] {len(chosen)} blok birleştiriliyor")
        res = assemble.assemble(chosen, merged, audio_mode="speech")
        cuts = block_cuts(blocks)
        try:
            r = qa.check(merged, "", sheet=merged[:-4] + "_kontrol.jpg", crops=merged[:-4] + "_kirpinti.jpg",
                         style=style)
            essential.append(r["temas"])
            files.append(r["kirpinti"])
        except Exception as e:  # noqa: BLE001
            log(f"   Birleşik kontrol yapılamadı: {e}")
        cont = None
        if watch:
            log(f"🎞️ [{arm}] Süreklilik izleniyor")
            cont = review.continuity_review(merged, cuts, bible or {}, api_key, log=log)
            if cont:
                log(f"   Süreklilik [{arm}]: " + ", ".join(f"{k} {cont.get(k)}" for k in review.SURECLILIK_PUANLARI)
                    + f" · ortalama {cont.get('ortalama')}")
        essential.append(merged)
        summary["kollar"][arm] = {"birlesik": os.path.basename(merged), "saniye": res.get("saniye"),
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
