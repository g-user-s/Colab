"""Gradio arayüzü: fikir → Gemini ile H3 prompt'u → Pika H3 Flex / MiniMax-H3 videosu."""

import copy
import datetime
import json
import os
import queue
import re
import shutil
import tempfile
import threading
import time

import gradio as gr

from . import assemble, comfy_client, config, graphs, prompt_writer, qa, setup_env

FAKE = os.environ.get("H3APP_FAKE") == "1"   # yerel arayüz testi: GPU ve Gemini olmadan
# H3APP_FAKE=1 ile birlikte H3APP_REAL_GEMINI=1: video sahte, Gemini gerçek (yerel prompt denemesi)
REAL_GEMINI = os.environ.get("H3APP_REAL_GEMINI") == "1"


def _fake_gemini(key):
    return FAKE and not (REAL_GEMINI and key)
_lock = threading.Lock()
_state = {"secret_key": None, "drive_dir": None}
STAMP_RE = re.compile(r"^(\d{8}_\d{6})_")


def _to_pil(path):
    """Galeri bileşenlerinde proxyPort(7860) iç adres sorununu önlemek için görseli PIL.Image olarak yükler."""
    if not isinstance(path, str) or not os.path.isfile(path):
        return path
    try:
        from PIL import Image
        with Image.open(path) as im:
            im.load()
            return im.copy()
    except Exception:
        return os.path.abspath(path)


def _preview_refs(files):
    """Yüklenen referans görsellerini galeri önizlemesi için PIL.Image listesine çevirir."""
    return [_to_pil(p) for p in _paths(files)]


def _pair_videos(vdict):
    """Sol oynatıcıda taslak (Pika veya Turbo), sağ oynatıcıda final (H3; yoksa ikinci taslak) gösterilir."""
    if vdict.get("turbo") and vdict.get("pika") and not vdict.get("h3"):
        return vdict["turbo"], vdict["pika"]
    return vdict.get("pika") or vdict.get("turbo"), vdict.get("h3")


def _write_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    return path


def _sync_to_drive(paths, say=None):
    """Verilen dosya veya dosya listesini Drive klasörü açıksa anında oraya kopyalar (kesinti koruması)."""
    drive_dir = _state.get("drive_dir")
    if not drive_dir:
        return
    os.makedirs(drive_dir, exist_ok=True)
    if isinstance(paths, str):
        paths = [paths]
    copied = []
    for p in paths:
        if p and isinstance(p, str) and os.path.isfile(p):
            shutil.copyfile(p, os.path.join(drive_dir, os.path.basename(p)))
            copied.append(os.path.basename(p))
    if copied and say:
        say(f"   💾 Drive'a anında kaydedildi ({drive_dir}): {', '.join(copied)}")


def _colab_secret(name):
    try:
        from google.colab import userdata
        val = userdata.get(name)
        if val:
            return val
    except Exception:
        pass
    return (os.environ.get(name) or "").strip() or None


def _key(typed):
    return (typed or "").strip() or _state["secret_key"]


def _status_line():
    g = setup_env.gpu()
    gpu = f"{g[0]} · {g[1]} GB" if g else "GPU yok (Çalışma zamanı → türünü değiştir → G4 GPU seçin)"
    key = "Colab Secrets'tan alındı" if _state["secret_key"] else "girilmedi"
    drive = _state["drive_dir"] or "kapalı ⚠️ (bağlantı koparsa videolar kaybolur)"
    models = (f"Drive'a da kaydedilir ({config.MODEL_SAVE_DIR})" if config.MODEL_SAVE_DIR
              else ("Drive'da aranır, kaydedilmez" if config.MODEL_SOURCE_DIRS else "her oturumda indirilir"))
    return (f"**GPU:** {gpu} &nbsp;·&nbsp; **Gemini anahtarı:** {key} &nbsp;·&nbsp; **Drive'a kayıt:** {drive}"
            f" &nbsp;·&nbsp; **Modeller:** {models}")


def list_models(typed_key):
    key = _key(typed_key)
    if _fake_gemini(key):
        return gr.update(choices=["gemini-test-pro"], value="gemini-test-pro"), "Model listesi alındı (test modu)."
    if not key:
        return gr.update(), "Önce Gemini API anahtarını girin ya da Colab Secrets'a GEMINI adıyla ekleyin."
    try:
        names = prompt_writer.gemini_models(key)
    except Exception as e:
        return gr.update(), f"Gemini model listesi alınamadı: {e}"
    if not names:
        return gr.update(), "Bu anahtarla kullanılabilen Gemini metin modeli bulunamadı."
    return gr.update(choices=names, value=names[0]), f"{len(names)} model bulundu; en yenisi seçildi: {names[0]}"


def _paths(files):
    return [f if isinstance(f, str) else f.name for f in (files or [])][:config.MAX_REF_IMAGES]


def _refs(refs, style, picks, styled):
    """Kullanılacak referans görseller, yükleme sırasıyla. Çizgi/3D stilde bir görsel için işaretli stil çizimi
    varsa ("Görsel N · A/B") o kullanılır, yoksa yüklenen görsel; böylece sıra ve roller hiç kaymaz."""
    paths = _paths(refs)
    if style == config.DEFAULT_STYLE or not picks:
        return paths
    out = []
    for i, src in enumerate(paths, 1):
        chosen = next((styled[l] for l in picks if l.startswith(f"Görsel {i} ·") and l in (styled or {})), None)
        out.append(chosen or src)
    return out


ROLE_CHOICES = [("Karakter", prompt_writer.ROLE_CHARACTER), ("Arka plan / mekân", prompt_writer.ROLE_SCENE),
                ("Nesne / eşya", prompt_writer.ROLE_OBJECT)]


def _roles(ref_roles, refs):
    """Arayüzdeki rol listesini yüklenen görsel sayısına göre hizalar (eksikler karakter sayılır)."""
    n = len(_paths(refs))
    return prompt_writer.normalize_roles(list(ref_roles or [])[:n], n) if n else []


def _role_caption(i, spec):
    name = f" — {spec['name']}" if spec.get("name") else ""
    if spec["role"] == prompt_writer.ROLE_SCENE:
        return f"Görsel {i} · Arka plan{name}"
    if spec["role"] == prompt_writer.ROLE_OBJECT:
        return f"Görsel {i} · Nesne{name}"
    return f"Görsel {i} · Karakter {spec['char']} (S{spec['char']}){name}"


def roles_summary(ref_roles, refs):
    """Kullanıcıya gösterilen tek satırlık özet: hangi görsel ne olarak kullanılacak."""
    specs = _roles(ref_roles, refs)
    return " · ".join(_role_caption(i, sp) for i, sp in enumerate(specs, 1))


def _on_refs(files):
    """Görsel yüklenince: numaralı önizleme, her görsel için rol satırı (varsayılan karakter) ve rol durumu."""
    paths = _paths(files)
    roles = [{"role": prompt_writer.ROLE_CHARACTER, "name": ""} for _ in paths]
    specs = prompt_writer.normalize_roles(roles, len(paths))
    gallery = [(_to_pil(p), _role_caption(i, sp)) for i, (p, sp) in enumerate(zip(paths, specs), 1)]
    rows = [gr.update(visible=i < len(paths)) for i in range(config.MAX_REF_IMAGES)]
    dds = [gr.update(value=prompt_writer.ROLE_CHARACTER,
                     label=f"Görsel {i + 1} rolü" + (f" ({os.path.basename(paths[i])})" if i < len(paths) else ""))
           for i in range(config.MAX_REF_IMAGES)]
    names = [gr.update(value="") for _ in range(config.MAX_REF_IMAGES)]
    return (gallery or None, *rows, *dds, *names, roles)


def _collect_roles(files, *vals):
    """Rol açılır menüleri ve ad kutularından rol listesi + güncel numaralı önizleme."""
    n = len(_paths(files))
    dds, names = vals[:config.MAX_REF_IMAGES], vals[config.MAX_REF_IMAGES:]
    roles = [{"role": dds[i] or prompt_writer.ROLE_CHARACTER, "name": (names[i] or "").strip()} for i in range(n)]
    specs = prompt_writer.normalize_roles(roles, n)
    gallery = [(_to_pil(p), _role_caption(i, sp)) for i, (p, sp) in enumerate(zip(_paths(files), specs), 1)]
    return roles, (gallery or None)


def do_stylize(refs, style, typed_key, idea="", ref_roles=None):
    """Yüklenen her referansı seçilen stilde 2 kez yeniden çizdirir: (galeri, seçim kutusu, eşlem, mesaj)."""
    none = (None, gr.update(choices=[], value=[]), {})
    images = _paths(refs)
    if style == config.DEFAULT_STYLE:
        return *none, "Gerçek dünya stilinde görseller olduğu gibi kullanılır."
    if not images:
        return *none, "Önce bir karakter / referans görseli yükleyin."
    key = _key(typed_key)
    use_fake = _fake_gemini(key)
    if not key and not use_fake:
        return *none, "❌ Gemini API anahtarı yok."
    dest = os.path.join(config.OUTPUT_DIR, "stil_referans")
    styled, labels, gallery = {}, [], []
    try:
        model = None if use_fake else (prompt_writer.image_models(key) or [None])[0]
        if not use_fake and not model:
            return *none, "❌ Bu anahtarla görsel üretebilen Gemini modeli bulunamadı."
        specs = _roles(ref_roles, refs)
        for i, src in enumerate(images, 1):
            if use_fake:
                os.makedirs(dest, exist_ok=True)
                outs = []
                for v in "AB":
                    outs.append(os.path.join(dest, f"test_{i}_{v}{os.path.splitext(src)[1]}"))
                    shutil.copyfile(src, outs[-1])
            else:
                outs = prompt_writer.stylize_reference(src, style, key, model, dest, idea=idea or "",
                                                       role=specs[i - 1]["role"] if specs else None)
            for j, path in enumerate(outs):
                label = f"Görsel {i} · {chr(65 + j)}"
                styled[label] = path
                labels.append(label)
                gallery.append((_to_pil(path), label))
    except Exception as e:
        return *none, f"❌ Görsel stile çevrilemedi: {e}"
    first = [l for l in labels if l.endswith("· A")]
    name = config.STYLES[style]["label"]
    return (gallery, gr.update(choices=labels, value=first), styled,
            f"✅ {len(images)} görsel {name} stilinde çizildi{'' if use_fake else f' ({model})'}. "
            "Her görsel için birini işaretleyin; Ref2VA'ya işaretlenenler verilir.")


def _ready(typed_key, model):
    """(anahtar, kullanılacak model, hata). Model seçilmemişse anahtarla görülen en yeni model seçilir."""
    key = _key(typed_key)
    if _fake_gemini(key):
        return key, model, None
    if not key:
        return None, model, "❌ Gemini API anahtarı yok."
    if not model or model == "gemini-test-pro":
        try:
            names = prompt_writer.gemini_models(key)
            if names:
                model = names[0]
        except Exception:
            pass
    if not model or model == "gemini-test-pro":
        return None, model, "❌ Önce 'Modelleri listele' ile bir Gemini modeli seçin."
    return key, model, None


def _used_model(notes, model):
    """Yedek modele geçildiyse metni gerçekten yazan model; yoksa seçili model."""
    return next((n.rsplit(": ", 1)[1] for n in reversed(notes) if n.startswith("↪️")), model)


def do_expand(idea, seconds, model, typed_key, refs, style, picks, styled, ref_roles=None):
    if not (idea or "").strip():
        return gr.update(), "Önce kısa fikri yazın."
    key, model, err = _ready(typed_key, model)
    if err:
        return gr.update(), err
    if _fake_gemini(key):
        time.sleep(1)
        return prompt_writer.BRIEF_EXAMPLES[1][1], "✅ Test modu: örnek brief yüklendi."
    try:
        notes = []
        brief = prompt_writer.expand(idea, int(seconds), key, model, _refs(refs, style, picks, styled),
                                     roles=_roles(ref_roles, refs),
                                     log=notes.append, style=style)
    except Exception as e:
        return gr.update(), f"❌ Gemini hatası: {e}"
    missing = [l for l in prompt_writer.literals(idea)
               if prompt_writer._norm_quotes(l.strip()) not in prompt_writer._norm_quotes(brief)]
    if missing:
        return brief, "⚠️ Brief'te şu metinler birebir yok, düzeltin: " + ", ".join(f'"{m}"' for m in missing)
    return brief, (f"✅ Detaylı brief hazır ({_used_model(notes, model)}). İsterseniz düzenleyin, sonra H3 prompt'una çevirin."
                   + "".join("\n\n" + n for n in notes))


def do_rewrite(idea, brief, seconds, model, typed_key, refs, style, picks, styled, ref_roles=None):
    request = (brief or "").strip() or (idea or "").strip()
    if not request:
        return gr.update(), "Önce fikri ya da brief'i yazın."
    key, model, err = _ready(typed_key, model)
    if err:
        return gr.update(), err
    images = _refs(refs, style, picks, styled)
    if _fake_gemini(key):
        time.sleep(1)
        return prompt_writer.EXAMPLE_OUTPUT, "✅ Test modu: örnek prompt yüklendi."
    notes = []
    try:
        prompt, problems = prompt_writer.rewrite(request, int(seconds), key, model, images, log=notes.append,
                                                 roles=_roles(ref_roles, refs),
                                                 style=style)
    except Exception as e:
        return gr.update(), f"❌ Gemini hatası: {e}"
    if problems:
        return prompt, "⚠️ Gemini çıktısında hâlâ sorun var, prompt'u elle düzeltin:\n- " + "\n- ".join(problems)
    lits = prompt_writer.literals(request)
    kept = f" Tırnak içindeki {len(lits)} metin harfi harfine korundu." if lits else ""
    mode = f" Referanslı mod: {roles_summary(ref_roles, refs)}." if images else ""
    mode += f" Stil: {config.STYLES[style]['label']}."
    return prompt, f"✅ H3 prompt'u hazır ({_used_model(notes, model)}).{kept}{mode}" + "".join("\n\n" + n for n in notes)


BLOCK_SEP_RE = re.compile(r"^===\s*BLOK\s*(\d+)\s*(?:\((\d+)\s*sn\))?\s*===\s*$", re.I | re.M)


def _format_block_prompts(blocks_out):
    """[{'block', 'seconds', 'prompt'}] listesini tek metin kutusunda düzenlenebilir biçime çevirir."""
    parts = []
    for b in blocks_out:
        parts.append(f"=== BLOK {b['block']} ({b['seconds']} sn) ===\n{(b.get('prompt') or '').strip()}")
    return "\n\n".join(parts)


def _parse_block_prompts(text, fallback_blocks=None):
    """Metin kutusundaki `=== BLOK N (S sn) ===` bölümlerini [{'block', 'seconds', 'prompt'}] listesine ayrıştırır."""
    text = (text or "").strip()
    if not text:
        return []
    matches = list(BLOCK_SEP_RE.finditer(text))
    if not matches:
        sec = (fallback_blocks[0]["seconds"] if fallback_blocks else 15)
        return [{"block": 1, "seconds": sec, "prompt": text}]
    sec_map = {b["block"]: b["seconds"] for b in (fallback_blocks or [])}
    out = []
    for idx, m in enumerate(matches):
        bnum = int(m.group(1))
        sec = int(m.group(2)) if m.group(2) else sec_map.get(bnum, 15)
        start = m.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        if body:
            out.append({"block": bnum, "seconds": sec, "prompt": body})
    return out


def do_plan_shots(idea, total_seconds, audio_mode, model, typed_key, refs, style, picks, styled, ref_roles=None):
    """Kısa fikir + toplam süre → ortak dünya çapası + düzenlenebilir blok/çekim tablosu."""
    if not (idea or "").strip():
        return gr.update(), gr.update(), "Önce kısa fikri yazın."
    key, model, err = _ready(typed_key, model)
    if err:
        return gr.update(), gr.update(), err
    images = _refs(refs, style, picks, styled)
    total_sec = int(round(float(total_seconds)))
    if _fake_gemini(key):
        time.sleep(0.5)
        n_blocks = max(1, (total_sec + 14) // 15)
        per_block = total_sec // n_blocks
        anchor = ("A woman in a red wool coat and silver scarf with flat leather boots in the vaulted Grand Bazaar "
                  "at midday; warm lantern light and shafts of dusty sunlight; no written signs in the background.")
        shots = []
        for b in range(1, n_blocks + 1):
            d1 = round(per_block * 0.5, 1)
            d2 = round(per_block - d1, 1)
            shots += [
                {"block": b, "shot": 1, "start_sec": 0.0, "duration": d1, "framing": "Wide full-body shot, 28mm",
                 "action": f"Block {b} opening: she walks forward through the bazaar aisle.",
                 "camera": "Smooth backward steadicam tracking", "sound": "Ambient bazaar murmur"},
                {"block": b, "shot": 2, "start_sec": d1, "duration": d2, "framing": "Medium shot, 50mm",
                 "action": f"Block {b} close: she pauses by copper lanterns and holds a calm gaze for 0.5s.",
                 "camera": "Gentle push-in settling to a still hold", "sound": "Soft footsteps and copper clink"},
            ]
        return anchor, prompt_writer.shots_to_rows(shots), f"✅ Test modu: {n_blocks} blok ({total_sec} sn) planlandı."
    notes = []
    try:
        plan, problems = prompt_writer.plan_shots(idea, total_sec, key, model, images=images, style=style,
                                                  roles=_roles(ref_roles, refs),
                                                  audio_mode=audio_mode, log=notes.append)
    except Exception as e:
        return gr.update(), gr.update(), f"❌ Gemini planlama hatası: {e}"
    rows = prompt_writer.shots_to_rows(plan.get("shots") or [])
    anchor = plan.get("world_anchor") or ""
    blocks = prompt_writer.blocks_from_plan(plan)
    if problems:
        return anchor, rows, "⚠️ Planda uyarı var (tabloda düzeltebilirsiniz):\n- " + "\n- ".join(problems)
    return anchor, rows, (f"✅ {len(blocks)} blok · {len(rows)} çekim ({total_sec} sn) planlandı ({_used_model(notes, model)}). "
                          "Tabloyu inceleyin veya düzenleyin, ardından '2 · Blokların H3 Prompt'larını Hazırla' düğmesine basın."
                          + "".join("\n\n" + n for n in notes))


def do_rewrite_blocks(idea, world_anchor, shot_rows, audio_mode, model, typed_key, refs, style, picks, styled,
                      ref_roles=None):
    """Düzenlenmiş dünya çapası + çekim tablosu → her blok için H3 prompt'u."""
    shots = prompt_writer.rows_to_shots(shot_rows)
    if not shots:
        return gr.update(), gr.update(), "Önce '1 · Blok ve Çekim Tablosu Planla' ile çekim tablosunu oluşturun."
    key, model, err = _ready(typed_key, model)
    if err:
        return gr.update(), gr.update(), err
    images = _refs(refs, style, picks, styled)
    plan = {"world_anchor": (world_anchor or "").strip(), "shots": shots}
    blocks = prompt_writer.blocks_from_plan(plan)
    if _fake_gemini(key):
        time.sleep(0.5)
        fake_out = []
        for b in blocks:
            p = prompt_writer.EXAMPLE_OUTPUT
            if audio_mode == "music":
                p = re.sub(r"<d>.*?</d>", "", p)
                p = p.replace("overall_soundscape:", f"overall_soundscape: {prompt_writer._MUSIC_SILENT};")
            fake_out.append({"block": b["block"], "seconds": b["seconds"], "prompt": p, "problems": []})
        choices = [b["block"] for b in blocks]
        return (_format_block_prompts(fake_out), gr.update(choices=choices, value=choices[0]),
                f"✅ Test modu: {len(blocks)} blok için H3 prompt'u hazır.")
    notes = []
    try:
        out = prompt_writer.rewrite_blocks(plan, key, model, images=images, style=style, audio_mode=audio_mode,
                                           roles=_roles(ref_roles, refs),
                                           idea=idea or "", log=notes.append)
    except Exception as e:
        return gr.update(), gr.update(), f"❌ Gemini blok prompt hatası: {e}"
    all_probs = [f"Blok {b['block']}: {' | '.join(b['problems'])}" for b in out if b.get("problems")]
    choices = [b["block"] for b in out]
    text = _format_block_prompts(out)
    if all_probs:
        return (text, gr.update(choices=choices, value=choices[0]),
                "⚠️ Bazı blok prompt'larında uyarı var:\n- " + "\n- ".join(all_probs))
    return (text, gr.update(choices=choices, value=choices[0]),
            f"✅ {len(out)} blok için H3 prompt'ları hazır ({_used_model(notes, model)}). İsterseniz düzenleyip üretime geçin."
            + "".join("\n\n" + n for n in notes))


def _assemble_method(bstate, method, audio_mode, music_file, keep_ambient, say):
    """Belirli bir yöntem ('turbo', 'pika' veya 'h3') için tamamlanmış blok videolarını kare-tam birleştirir."""
    blocks_dict = bstate.get("blocks") or {}
    ordered = [blocks_dict[k] for k in sorted(blocks_dict) if blocks_dict[k].get(method)]
    if not ordered:
        return None
    clips = [b[method] for b in ordered]
    stamp = bstate.get("stamp") or f"{datetime.datetime.now():%Y%m%d_%H%M%S}"
    dest = os.path.join(config.OUTPUT_DIR, f"{stamp}_{config.METHODS[method]['file']}_birlesik.mp4")
    music_path = music_file if isinstance(music_file, str) else getattr(music_file, "name", None)
    res = assemble.assemble(clips, dest, audio_mode=audio_mode, music_path=music_path, keep_ambient=bool(keep_ambient))
    lufs_str = f", ses: {res['lufs']:.1f} LUFS".replace(".", ",") if res.get("lufs") is not None else ""
    trims = res.get("kirpilan_son_kareler") or []
    trim_str = f", sonda kırpılan kareler: {trims}" if any(trims) else ""
    say(f"🎬 Birleştirildi ({config.METHODS[method]['file']}): {os.path.basename(dest)} "
        f"({res['blok_sayisi']} blok, {res['saniye']:.2f} sn, {res['kare']} kare{lufs_str}{trim_str})")
    bstate.setdefault("finals", {})[method] = dest
    info_path = os.path.join(config.OUTPUT_DIR, f"{stamp}_bilgi.json")
    _write_json(info_path, bstate)
    _sync_to_drive([dest, info_path])
    return dest


def _generate_long_job(block_prompts_text, world_anchor, shot_rows, audio_mode, music_file, keep_ambient,
                  methods, resolution, seed, idea, refs, style=config.DEFAULT_STYLE, picks=None, styled=None,
                  ref_roles=None):
    """Çok çekimli uzun video üretici: her bloğu sırayla üretir, anında diske/Drive'a yazar ve birleştirir."""
    log, finals, files, sheets, bvideos = [], {m: None for m in config.METHODS}, [], [], []
    bstate = {}

    def say(msg):
        log.append(f"[{datetime.datetime.now():%H:%M:%S}] {msg}")

    def out():
        v_left, v_right = _pair_videos(finals)
        return "\n".join(log), v_left, v_right, bvideos or None, files or None, sheets or None, bstate

    shots = prompt_writer.rows_to_shots(shot_rows)
    fallback = prompt_writer.blocks_from_plan({"world_anchor": world_anchor, "shots": shots}) if shots else None
    blocks = _parse_block_prompts(block_prompts_text, fallback_blocks=fallback)
    if not blocks:
        say("❌ Önce blok H3 prompt'larını oluşturun.")
        yield out(); return
    if not methods:
        say("❌ En az bir yöntem seçin.")
        yield out(); return
    if audio_mode == "music" and not music_file:
        say("⚠️ Müzikli mod seçildi ancak müzik dosyası yüklenmedi; video ortam sesiyle/sessiz birleştirilecek.")
    if not _lock.acquire(blocking=False):
        say("❌ Başka bir üretim sürüyor; bitmesini bekleyin.")
        yield out(); return
    try:
        width, height = config.RESOLUTIONS[resolution]
        stamp = f"{datetime.datetime.now():%Y%m%d_%H%M%S}"
        os.makedirs(config.OUTPUT_DIR, exist_ok=True)
        images = _refs(refs, style, picks, styled)
        ref_names = []
        if FAKE:
            say(f"Test modu: {len(blocks)} blok üretimi başlıyor.")
        else:
            g = setup_env.gpu()
            if not g:
                raise RuntimeError("GPU yok. Çalışma zamanı → Çalışma zamanı türünü değiştir → G4 GPU.")
            say(f"GPU: {g[0]} ({g[1]} GB).")
            yield out()
            te = setup_env.text_encoder_role()
            yield from _heartbeat(lambda: setup_env.ensure_comfy(log=say), out)
            yield from _heartbeat(lambda: setup_env.ensure_models(setup_env.roles_for(methods, te, bool(images)),
                                                                  log=say), out)
            yield from _heartbeat(lambda: comfy_client.start(log=say), out)
            for i, src in enumerate(images):
                name = f"h3app_{stamp}_{i + 1}{os.path.splitext(src)[1].lower() or '.png'}"
                os.makedirs(os.path.join(config.COMFY_DIR, "input"), exist_ok=True)
                shutil.copyfile(src, os.path.join(config.COMFY_DIR, "input", name))
                ref_names.append(name)

        info_file = os.path.join(config.OUTPUT_DIR, f"{stamp}_bilgi.json")
        bstate = {
            "uzun_video": True, "stamp": stamp, "resolution": resolution, "style": style, "audio_mode": audio_mode,
            "fikir": idea, "world_anchor": world_anchor or "", "shots": shots,
            "ref_names": ref_names, "images": images, "roller": _roles(ref_roles, refs),
            "methods": list(methods), "blocks": {}, "finals": {},
        }
        _write_json(info_file, bstate)
        files.append(info_file)
        _sync_to_drive(info_file)

        active_methods = [m for m in config.METHODS if m in methods]
        for b in blocks:
            bnum, bsec, bprompt = b["block"], b["seconds"], b["prompt"]
            frames = config.frames_for(bsec)
            bseed = int(seed) + bnum - 1
            bstate["blocks"][bnum] = {"seconds": bsec, "prompt": bprompt, "seed": bseed}
            pfile = os.path.join(config.OUTPUT_DIR, f"{stamp}_blok{bnum}_prompt.txt")
            open(pfile, "w", encoding="utf-8").write(bprompt + "\n")
            files.append(pfile)
            _write_json(info_file, bstate)
            _sync_to_drive([pfile, info_file])
            for method in active_methods:
                name = f"{stamp}_blok{bnum}_{config.METHODS[method]['file']}_seed{bseed}.mp4"
                dest = os.path.join(config.OUTPUT_DIR, name)
                say(f"▶ Blok {bnum}/{len(blocks)} · {config.METHODS[method]['label']} ({bsec} sn, {frames} kare, seed {bseed})")
                yield out()
                t0 = time.time()
                if FAKE:
                    time.sleep(0.3)
                    shutil.copyfile(os.environ["H3APP_FAKE_VIDEO"], dest)
                else:
                    te = setup_env.text_encoder_role()
                    grf = graphs.build(method, bprompt, bseed, width, height, frames, te,
                                       prefix=f"h3app/{stamp}_b{bnum}_{method}", ref_images=ref_names)
                    shown = 0
                    for sec in comfy_client.run(grf, dest):
                        if sec // 60 > shown:
                            shown = sec // 60
                            say(f"   … {shown} dk geçti")
                        yield out()
                took = int(time.time() - t0)
                qa.normalize_audio(dest)
                bstate["blocks"][bnum][method] = dest
                files.append(dest)
                say(f"✅ Blok {bnum} bitti: {name} ({took} sn)")
                to_sync = [dest]
                try:
                    stem = dest[:-4]
                    ref_v = (bstate["blocks"][bnum].get("pika") or bstate["blocks"][bnum].get("turbo")) if method == "h3" else None
                    r = qa.check(dest, bprompt, sheet=stem + "_kontrol.jpg", crops=stem + "_kirpinti.jpg",
                                 style=style, ref_video=ref_v)
                    say("   " + qa.summary(r))
                    sheets += [(_to_pil(r["temas"]), f"Blok {bnum} · {config.METHODS[method]['file']} · anlar"),
                               (_to_pil(r["kirpinti"]), f"Blok {bnum} · {config.METHODS[method]['file']} · %100 kırpıntı")]
                    files += [r["temas"], r["kirpinti"]]
                    to_sync += [r["temas"], r["kirpinti"]]
                except Exception as e:
                    say(f"   Kontrol yapılamadı: {e}")
                _write_json(info_file, bstate)
                to_sync.append(info_file)
                _sync_to_drive(to_sync, say=say)
                bvideos = [(bstate["blocks"][k].get(active_methods[0]), f"Blok {k}")
                           for k in sorted(bstate["blocks"]) if bstate["blocks"][k].get(active_methods[0])]
                yield out()

        for method in active_methods:
            merged = _assemble_method(bstate, method, audio_mode, music_file, keep_ambient, say)
            if merged:
                finals[method] = merged
                files.append(merged)
        yield out()
    except Exception as e:
        say(f"❌ Hata: {e}")
    finally:
        _lock.release()
    yield out()


def _reroll_job(block_num, new_seed, method, block_prompts_text, audio_mode, music_file, keep_ambient, bstate):
    """Yalnızca seçilen bloğu yeni seed ile yeniden üretir ve diğer bloklarla anında yeniden birleştirir."""
    log, finals, files, sheets, bvideos = [], {m: None for m in config.METHODS}, [], [], []

    def say(msg):
        log.append(f"[{datetime.datetime.now():%H:%M:%S}] {msg}")

    def out():
        v_left, v_right = _pair_videos(finals)
        return "\n".join(log), v_left, v_right, bvideos or None, files or None, sheets or None, bstate

    if not bstate or not bstate.get("blocks"):
        say("❌ Önce '3 · Tüm Blokları Üret ve Birleştir' ile blokları üretin.")
        yield out(); return
    bnum = int(block_num or 1)
    if bnum not in bstate["blocks"]:
        say(f"❌ Blok {bnum} mevcut üretimde bulunamadı.")
        yield out(); return
    if not _lock.acquire(blocking=False):
        say("❌ Başka bir üretim sürüyor; bitmesini bekleyin.")
        yield out(); return
    try:
        parsed = {b["block"]: b["prompt"] for b in _parse_block_prompts(block_prompts_text)}
        binfo = bstate["blocks"][bnum]
        if bnum in parsed and parsed[bnum].strip():
            binfo["prompt"] = parsed[bnum].strip()
        bsec = binfo["seconds"]
        bprompt = binfo["prompt"]
        bseed = int(new_seed)
        binfo["seed"] = bseed
        frames = config.frames_for(bsec)
        width, height = config.RESOLUTIONS[bstate["resolution"]]
        stamp = bstate["stamp"]
        info_file = os.path.join(config.OUTPUT_DIR, f"{stamp}_bilgi.json")
        name = f"{stamp}_blok{bnum}_{config.METHODS[method]['file']}_seed{bseed}.mp4"
        dest = os.path.join(config.OUTPUT_DIR, name)
        say(f"🔄 Blok {bnum} yeniden üretiliyor ({config.METHODS[method]['label']}, seed {bseed})…")
        yield out()
        if FAKE:
            time.sleep(0.3)
            shutil.copyfile(os.environ["H3APP_FAKE_VIDEO"], dest)
        else:
            te = setup_env.text_encoder_role()
            yield from _heartbeat(lambda: comfy_client.start(log=say), out)
            grf = graphs.build(method, bprompt, bseed, width, height, frames, te,
                               prefix=f"h3app/{stamp}_b{bnum}_{method}_s{bseed}",
                               ref_images=bstate.get("ref_names") or [])
            for _ in comfy_client.run(grf, dest):
                yield out()
        qa.normalize_audio(dest)
        binfo[method] = dest
        files.append(dest)
        say(f"✅ Blok {bnum} yenilendi: {name}")
        to_sync = [dest]
        try:
            stem = dest[:-4]
            ref_v = (binfo.get("pika") or binfo.get("turbo")) if method == "h3" else None
            r = qa.check(dest, bprompt, sheet=stem + "_kontrol.jpg", crops=stem + "_kirpinti.jpg",
                         style=bstate.get("style"), ref_video=ref_v)
            say("   " + qa.summary(r))
            sheets += [(_to_pil(r["temas"]), f"Blok {bnum} (seed {bseed}) · anlar"),
                       (_to_pil(r["kirpinti"]), f"Blok {bnum} (seed {bseed}) · %100 kırpıntı")]
            files += [r["temas"], r["kirpinti"]]
            to_sync += [r["temas"], r["kirpinti"]]
        except Exception as e:
            say(f"   Kontrol yapılamadı: {e}")
        _write_json(info_file, bstate)
        to_sync.append(info_file)
        _sync_to_drive(to_sync, say=say)

        for m in config.METHODS:
            if any(bstate["blocks"][k].get(m) for k in bstate["blocks"]):
                merged = _assemble_method(bstate, m, audio_mode, music_file, keep_ambient, say)
                if merged:
                    finals[m] = merged
                    files.append(merged)
        primary = method if any(bstate["blocks"][k].get(method) for k in bstate["blocks"]) else next(
            (m for m in config.METHODS if any(bstate["blocks"][k].get(m) for k in bstate["blocks"])), "pika"
        )
        bvideos = [(bstate["blocks"][k].get(primary), f"Blok {k}")
                   for k in sorted(bstate["blocks"]) if bstate["blocks"][k].get(primary)]
    except Exception as e:
        say(f"❌ Hata: {e}")
    finally:
        _lock.release()
    yield out()


def reassemble_blocks(audio_mode, music_file, keep_ambient, bstate):
    """Üretilmiş mevcut blokları (ör. yeni müzik veya ses moduyla) yeniden üretmeden 1-2 saniyede birleştirir."""
    log, finals, files = [], {m: None for m in config.METHODS}, []

    def say(msg):
        log.append(f"[{datetime.datetime.now():%H:%M:%S}] {msg}")

    if not bstate or not bstate.get("blocks"):
        say("❌ Birleştirilecek hazır blok bulunamadı.")
        return "\n".join(log), None, None, None
    try:
        for m in config.METHODS:
            if any(bstate["blocks"][k].get(m) for k in bstate["blocks"]):
                merged = _assemble_method(bstate, m, audio_mode, music_file, keep_ambient, say)
                if merged:
                    finals[m] = merged
                    files.append(merged)
    except Exception as e:
        say(f"❌ Birleştirme hatası: {e}")
    v_left, v_right = _pair_videos(finals)
    return "\n".join(log), v_left, v_right, files or None


def _generate_job(h3_prompt, methods, resolution, seconds, seed, idea, brief, refs, style=config.DEFAULT_STYLE,
             picks=None, styled=None, ref_roles=None):
    """Generator: (günlük, taslak video, final video, indirilecek dosyalar, kontrol görselleri)."""
    log, videos, files, sheets = [], {m: None for m in config.METHODS}, [], []

    def say(msg):
        log.append(f"[{datetime.datetime.now():%H:%M:%S}] {msg}")

    def out():
        v_left, v_right = _pair_videos(videos)
        return "\n".join(log), v_left, v_right, files or None, sheets or None

    if not (h3_prompt or "").strip():
        say("❌ Önce H3 prompt'unu oluşturun ya da yazın.")
        yield out(); return
    if not methods:
        say("❌ En az bir yöntem seçin.")
        yield out(); return
    request = (brief or "").strip() or (idea or "").strip()
    images = _refs(refs, style, picks, styled)
    problems = prompt_writer.check(h3_prompt, request, len(images), style, roles=_roles(ref_roles, refs))
    if problems:
        say("⚠️ Prompt uyarısı (yine de devam ediliyor): " + " | ".join(problems))
    if not _lock.acquire(blocking=False):
        say("❌ Başka bir üretim sürüyor; bitmesini bekleyin.")
        yield out(); return
    try:
        width, height = config.RESOLUTIONS[resolution]
        frames = config.frames_for(seconds)
        stamp = f"{datetime.datetime.now():%Y%m%d_%H%M%S}"
        base = os.path.join(config.OUTPUT_DIR, stamp)
        os.makedirs(config.OUTPUT_DIR, exist_ok=True)
        prompt_file = base + "_prompt.txt"
        info_file = base + "_bilgi.json"
        open(prompt_file, "w", encoding="utf-8").write(h3_prompt.strip() + "\n")
        info = {"stil": config.STYLES[style]["label"], "fikir": idea, "brief": brief,
                "roller": _roles(ref_roles, refs),
                "referanslar": [os.path.basename(p) for p in images],
                "yontemler": methods, "seed": int(seed), "boyut": [width, height],
                "kare": frames, "saniye": round(frames / 24, 2), "videolar": {}}
        ref_names = []
        if FAKE:
            say("Test modu: kurulum atlandı.")
        else:
            g = setup_env.gpu()
            if not g:
                raise RuntimeError("GPU yok. Çalışma zamanı → Çalışma zamanı türünü değiştir → G4 GPU.")
            say(f"GPU: {g[0]} ({g[1]} GB).")
            yield out()
            te = setup_env.text_encoder_role()
            yield from _heartbeat(lambda: setup_env.ensure_comfy(log=say), out)
            yield from _heartbeat(lambda: setup_env.ensure_models(setup_env.roles_for(methods, te, bool(images)),
                                                                  log=say), out)
            yield from _heartbeat(lambda: comfy_client.start(log=say), out)
            for i, src in enumerate(images):
                name = f"h3app_{stamp}_{i + 1}{os.path.splitext(src)[1].lower() or '.png'}"
                os.makedirs(os.path.join(config.COMFY_DIR, "input"), exist_ok=True)
                shutil.copyfile(src, os.path.join(config.COMFY_DIR, "input", name))
                ref_names.append(name)
            if images:
                say(f"Referanslı mod (Ref2VA): {len(images)} görsel <Picture 1…{len(images)}> olarak verildi — "
                    f"{roles_summary(ref_roles, refs)}.")
        kept_refs = []
        for i, src in enumerate(images):   # referans görseller de sonuçla birlikte saklanır
            kept = f"{base}_referans{i + 1}{os.path.splitext(src)[1].lower() or '.png'}"
            shutil.copyfile(src, kept)
            info["referanslar"][i] = os.path.basename(kept)
            kept_refs.append(kept)
        # Kesinti koruması: üretim başlamadan önce prompt, bilgi ve referansları diske ve Drive'a yaz
        _write_json(info_file, info)
        files += [prompt_file, info_file]
        _sync_to_drive([prompt_file, info_file] + kept_refs)
        yield out()
        for method in [m for m in config.METHODS if m in methods]:
            name = f"{stamp}_{config.METHODS[method]['file']}_seed{int(seed)}.mp4"
            dest = os.path.join(config.OUTPUT_DIR, name)
            say(f"▶ {config.METHODS[method]['label']} başladı ({width}×{height}, {frames} kare).")
            yield out()
            t0 = time.time()
            if FAKE:
                for _ in range(3):
                    time.sleep(1)
                    yield out()
                shutil.copyfile(os.environ["H3APP_FAKE_VIDEO"], dest)
            else:
                te = setup_env.text_encoder_role()
                g = graphs.build(method, h3_prompt.strip(), seed, width, height, frames, te,
                                 prefix=f"h3app/{stamp}_{method}", ref_images=ref_names)
                shown = 0
                for sec in comfy_client.run(g, dest):
                    if sec // 60 > shown:
                        shown = sec // 60
                        say(f"   … {shown} dk geçti")
                    yield out()
            took = int(time.time() - t0)
            norm = qa.normalize_audio(dest)
            if norm:
                say(f"   🔊 Ses dengelendi: {norm[0]:.1f} → {norm[1]:.1f} LUFS".replace(".", ","))
            videos[method] = dest
            files.append(dest)
            info["videolar"][method] = {"dosya": name, "sure_sn": took}
            say(f"✅ Bitti: {name} ({took} sn, {os.path.getsize(dest) / 1e6:.1f} MB)")
            to_sync = [dest]
            try:   # GPU'suz kontrol: kesmeler prompt'la karşılaştırılır, temas sayfası ve kırpıntılar çıkarılır
                stem = dest[:-4]
                ref_v = (videos.get("pika") or videos.get("turbo")) if method == "h3" else None
                r = qa.check(dest, h3_prompt, sheet=stem + "_kontrol.jpg", crops=stem + "_kirpinti.jpg",
                             style=style, ref_video=ref_v)
                say("   " + qa.summary(r))
                info["videolar"][method]["kontrol"] = {
                    k: r[k] for k in ("kesmeler", "beklenen", "bulunamayan", "beklenmeyen", "donmus",
                                      "lufs", "ses", "son_kayma", "stil_kontrol")
                }
                sheets += [(_to_pil(r["temas"]), f"{config.METHODS[method]['file']} · anlar"),
                           (_to_pil(r["kirpinti"]), f"{config.METHODS[method]['file']} · %100 kırpıntı")]
                files += [r["temas"], r["kirpinti"]]
                to_sync += [r["temas"], r["kirpinti"]]
            except Exception as e:
                say(f"   Kontrol yapılamadı: {e}")
            # Her yöntem biter bitmez bilgi.json ve çıktı dosyalarını anında diske ve Drive'a kaydet
            _write_json(info_file, info)
            to_sync += [prompt_file, info_file]
            _sync_to_drive(to_sync, say=say)
            yield out()
        say(f"Tamamlandı. Dosyalar: {config.OUTPUT_DIR}")
    except Exception as e:
        say(f"❌ Hata: {e}")
    finally:
        _lock.release()
    yield out()


COMFY_OUT_RE = re.compile(r"^(\d{8}_\d{6})_(?:b(\d+)_)?(turbo|pika|h3)(?:_s(\d+))?_\d+_?\.mp4$")


def _recover_comfy_outputs(stamp, info):
    """ComfyUI'nin bitirip uygulamanın kopyalayamadığı videoları (ör. Python çekirdeği yeniden başladı)
    ComfyUI/output/h3app altından OUTPUT_DIR'e uygulamanın adlandırmasıyla alır. Alınan dosya adlarını döner."""
    src_dir = os.path.join(config.COMFY_DIR, "output", "h3app")
    if not os.path.isdir(src_dir):
        return []
    found = {}
    for fn in sorted(os.listdir(src_dir)):   # aynı önekte birden fazla sayaç varsa sonuncusu kalır
        m = COMFY_OUT_RE.match(fn)
        if not m or m.group(1) != stamp:
            continue
        block, method, rseed = m.group(2), m.group(3), m.group(4)
        mfile = config.METHODS[method]["file"]
        if block:
            binfo = (info.get("blocks") or {}).get(block) or (info.get("blocks") or {}).get(int(block)) or {}
            seed = rseed or binfo.get("seed")
            if seed is None:
                continue
            name = f"{stamp}_blok{block}_{mfile}_seed{seed}.mp4"
        else:
            seed = info.get("seed")
            if seed is None:
                continue
            name = f"{stamp}_{mfile}_seed{seed}.mp4"
        found[name] = os.path.join(src_dir, fn)
    recovered = []
    for name, src in found.items():
        dest = os.path.join(config.OUTPUT_DIR, name)
        if not os.path.isfile(dest):
            shutil.copyfile(src, dest)
            recovered.append(name)
    if recovered:
        _sync_to_drive([os.path.join(config.OUTPUT_DIR, n) for n in recovered])
    return recovered


def load_last_outputs():
    """Tarayıcı bağlantısı kopup yeniden bağlanıldığında OUTPUT_DIR içindeki son tamamlanmış üretimleri arayüze geri yükler."""
    noop = (gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update())
    if not os.path.isdir(config.OUTPUT_DIR):
        return "📂 Henüz kaydedilmiş bir üretim klasörü bulunamadı.", None, None, None, None, *noop
    entries = sorted(os.listdir(config.OUTPUT_DIR))
    stamps = sorted({m.group(1) for name in entries if (m := STAMP_RE.match(name))}, reverse=True)
    if not stamps:
        return "📂 Henüz tamamlanmış bir üretim bulunamadı.", None, None, None, None, *noop

    stamp = stamps[0]
    prefix = f"{stamp}_"
    info_path = os.path.join(config.OUTPUT_DIR, f"{stamp}_bilgi.json")
    info = {}
    if os.path.isfile(info_path):
        try:
            info = json.load(open(info_path, encoding="utf-8"))
        except Exception:
            info = {}
    recovered = []
    if not job_running():
        try:
            recovered = _recover_comfy_outputs(stamp, info)
        except Exception:
            recovered = []
        if recovered:
            entries = sorted(os.listdir(config.OUTPUT_DIR))
    session_files = [os.path.join(config.OUTPUT_DIR, f) for f in entries
                     if f.startswith(prefix) and os.path.isfile(os.path.join(config.OUTPUT_DIR, f))]

    videos = {m: None for m in config.METHODS}
    sheets = []
    log = [f"📂 Son üretim diskten geri yüklendi (oturum: {stamp})."]
    if recovered:
        log.append("   ♻️ ComfyUI çıktısından kurtarıldı: " + ", ".join(recovered))

    is_long = bool(info.get("uzun_video")) or any(f"_{ 'blok' }" in os.path.basename(p) for p in session_files)
    if is_long:
        raw_blocks = info.get("blocks") or {}
        blocks = {int(k): v for k, v in raw_blocks.items()}
        for p in session_files:
            bn = os.path.basename(p)
            m_blk = re.match(rf"^{re.escape(stamp)}_blok(\d+)_(.+)_seed(\d+)\.mp4$", bn)
            if m_blk:
                bnum, mfile, bseed = int(m_blk.group(1)), m_blk.group(2), int(m_blk.group(3))
                mkey = next((k for k, v in config.METHODS.items() if v["file"] == mfile), None)
                if mkey:
                    blocks.setdefault(bnum, {"seconds": 15, "prompt": "", "seed": bseed})[mkey] = p
        for bnum in sorted(blocks):
            pfile = os.path.join(config.OUTPUT_DIR, f"{stamp}_blok{bnum}_prompt.txt")
            if not blocks[bnum].get("prompt") and os.path.isfile(pfile):
                blocks[bnum]["prompt"] = open(pfile, encoding="utf-8").read().strip()

        for mkey, mmeta in config.METHODS.items():
            merged = os.path.join(config.OUTPUT_DIR, f"{stamp}_{mmeta['file']}_birlesik.mp4")
            if os.path.isfile(merged):
                videos[mkey] = merged
                log.append(f"   🎬 Birleşik video: {os.path.basename(merged)}")
            elif blocks:
                first_blk = next((blocks[k].get(mkey) for k in sorted(blocks) if blocks[k].get(mkey)), None)
                if first_blk:
                    videos[mkey] = first_blk

        for p in session_files:
            bn = os.path.basename(p)
            if bn.endswith("_kontrol.jpg"):
                sheets.append((_to_pil(p), bn[len(prefix):-len("_kontrol.jpg")] + " · anlar"))
            elif bn.endswith("_kirpinti.jpg"):
                sheets.append((_to_pil(p), bn[len(prefix):-len("_kirpinti.jpg")] + " · %100 kırpıntı"))

        bstate = dict(info) if info else {"stamp": stamp}
        bstate["blocks"] = blocks
        bprompts_txt = _format_block_prompts([
            {"block": k, "seconds": blocks[k].get("seconds", 15), "prompt": blocks[k].get("prompt", "")}
            for k in sorted(blocks)
        ]) if blocks else gr.update()
        anchor_upd = info.get("world_anchor") or gr.update()
        shots_upd = prompt_writer.shots_to_rows(info["shots"]) if info.get("shots") else gr.update()
        primary = next((m for m in config.METHODS if any(blocks[k].get(m) for k in blocks)), "pika")
        bvideos = [(blocks[k].get(primary), f"Blok {k}") for k in sorted(blocks) if blocks[k].get(primary)]
        log.append(f"   ✅ {len(blocks)} blok ve {len(session_files)} dosya yüklendi.")
        v_left, v_right = _pair_videos(videos)
        return ("\n".join(log), v_left, v_right, session_files or None, sheets or None,
                gr.update(), bprompts_txt, anchor_upd, shots_upd, bvideos or None, bstate)

    # Tekil video oturumu
    prompt_file = os.path.join(config.OUTPUT_DIR, f"{stamp}_prompt.txt")
    prompt_upd = open(prompt_file, encoding="utf-8").read().strip() if os.path.isfile(prompt_file) else gr.update()
    for mkey, mmeta in config.METHODS.items():
        for p in session_files:
            bn = os.path.basename(p)
            if bn.startswith(f"{stamp}_{mmeta['file']}_seed") and bn.endswith(".mp4"):
                videos[mkey] = p
                log.append(f"   🎬 Video ({mmeta['label']}): {bn}")
    for p in session_files:
        bn = os.path.basename(p)
        if bn.endswith("_kontrol.jpg"):
            sheets.append((_to_pil(p), bn[len(prefix):-len("_kontrol.jpg")] + " · anlar"))
        elif bn.endswith("_kirpinti.jpg"):
            sheets.append((_to_pil(p), bn[len(prefix):-len("_kirpinti.jpg")] + " · %100 kırpıntı"))
    log.append(f"   ✅ Toplam {len(session_files)} dosya geri yüklendi ({config.OUTPUT_DIR}).")
    v_left, v_right = _pair_videos(videos)
    return ("\n".join(log), v_left, v_right, session_files or None, sheets or None,
            prompt_upd, gr.update(), gr.update(), gr.update(), gr.update(), gr.update())


# ---------------------------------------------------------------------------------------------------------
# Arka plan işi: üretim Gradio isteğinden bağımsız bir iş parçacığında koşar. Tarayıcı sekmesi kapanır ya da
# Colab bağlantısı koparsa Gradio kendi generator'ını durdurur; iş parçacığı ise ComfyUI'yi beklemeye, videoyu
# kopyalamaya, kontrol etmeye, birleştirmeye ve Drive'a yazmaya devam eder. Yeniden bağlanınca
# "Son Üretimleri Yükle" süren işi izler, bitince sonuçları diskten yükler.
_DONE = object()
_job = {"name": None, "thread": None, "last": None}


def job_running():
    t = _job.get("thread")
    return bool(t and t.is_alive())


def _freeze(snap):
    """İş parçacığı listeleri/sözlükleri değiştirmeye devam ederken arayüze o anın kopyası gider."""
    out = []
    for x in snap:
        if isinstance(x, list):
            x = list(x)
        elif isinstance(x, dict):
            x = copy.deepcopy(x)
        out.append(x)
    return tuple(out)


HEARTBEAT_SECONDS = 1.5   # Colab'in colab.dev proxy'si akışı tamponluyor: sık güncelleme tamponu boşaltır


def _heartbeat(fn, out, every=2.0):
    """Uzun ve sessiz bir adımı (kurulum, model indirme) ayrı iş parçacığında çalıştırır; bu sırada `every` sn'de
    bir güncel günlüğü verir (generator). Adımın hatası aynen yükseltilir."""
    box = {}

    def run():
        try:
            box["value"] = fn()
        except BaseException as e:   # noqa: BLE001 - hata çağırana aynen taşınır
            box["error"] = e

    t = threading.Thread(target=run, daemon=True, name="h3app-step")
    t.start()
    while t.is_alive():
        t.join(timeout=every)
        yield out()
    if "error" in box:
        raise box["error"]
    return box.get("value")


def _in_background(job_fn, name):
    def runner(*args, **kwargs):
        q = queue.Queue()
        attached = {"on": True}
        owner = not job_running()   # süren bir iş varken yeni tıklama yalnızca "meşgul" mesajını üretir

        def work():
            try:
                for snap in job_fn(*args, **kwargs):
                    snap = _freeze(snap)
                    if owner:
                        _job["last"] = snap
                    if attached["on"]:
                        q.put(snap)
            except Exception as e:   # iş fonksiyonları hatalarını kendileri yakalar; bu son güvence
                print(f"h3app arka plan işi hatası ({name}): {e}")
            finally:
                q.put(_DONE)

        t = threading.Thread(target=work, name=f"h3app-{name}", daemon=True)
        if owner:
            _job.update(name=name, thread=t, last=None)
        t.start()
        last = None
        try:
            while True:
                try:
                    snap = q.get(timeout=HEARTBEAT_SECONDS)
                except queue.Empty:
                    if last is not None:
                        yield last   # yeni bir şey yok: son durumu tekrarla (proxy tamponu dolsun, ekrana düşsün)
                    continue
                if snap is _DONE:
                    return
                last = snap
                yield snap
        finally:
            attached["on"] = False   # sekme kapandı: iş sürer, yalnızca arayüze akış durur

    runner.__name__ = job_fn.__name__.strip("_").replace("_job", "")
    runner.__doc__ = job_fn.__doc__
    return runner


# ---------------------------------------------------------------------------------------------------------
# Hızlı üretim: tek düğmeyle fikir → brief → H3 prompt'u → video. Hem insanlar hem tarayıcı kullanan ajanlar
# (ör. kişisel asistan botlar) için: birkaç kutu, tek düğme ve tek satırlık açık bir durum yazısı.
QUICK_METHODS = [(config.METHODS[k]["label"], k) for k in ("pika", "turbo", "h3")]


def _quick_job(idea, seconds, style, method, resolution, seed, model, typed_key, refs=None, ref_roles=None,
               picks=None, styled=None):
    """Generator: (durum, brief, H3 prompt'u, video, indirilecek dosyalar, ayrıntılı günlük)."""
    state = {"status": "", "brief": "", "prompt": "", "video": None, "files": None, "log": ""}

    def out(status=None):
        if status is not None:
            state["status"] = status
        return (state["status"], state["brief"], state["prompt"], state["video"], state["files"], state["log"])

    idea = (idea or "").strip()
    style = style or config.DEFAULT_STYLE
    method = method if method in config.METHODS else "pika"
    resolution = resolution if resolution in config.RESOLUTIONS else list(config.RESOLUTIONS)[0]
    seconds = int(min(config.MAX_SECONDS, max(config.MIN_SECONDS, int(seconds or 10))))
    if not idea:
        yield out("❌ Hata: önce fikri yazın.")
        return
    key, model, err = _ready(typed_key, model)
    if err:
        yield out(err)
        return
    images = _refs(refs, style, picks, styled)
    roles = _roles(ref_roles, refs)
    notes = []
    try:
        yield out("⏳ 1/3 Gemini detaylı brief'i yazıyor…")
        if _fake_gemini(key):
            state["brief"] = prompt_writer.BRIEF_EXAMPLES[1][1]
        else:
            state["brief"] = prompt_writer.expand(idea, seconds, key, model, images, log=notes.append, style=style,
                                                  roles=roles)
        yield out("⏳ 2/3 Gemini H3 prompt'unu yazıyor…")
        problems = []
        if _fake_gemini(key):
            state["prompt"] = prompt_writer.EXAMPLE_OUTPUT
        else:
            state["prompt"], problems = prompt_writer.rewrite(state["brief"], seconds, key, model, images,
                                                              log=notes.append, style=style, roles=roles)
        if not state["prompt"].strip():
            yield out("❌ Hata: Gemini prompt yazamadı. Biraz sonra tekrar deneyin.")
            return
    except Exception as e:
        state["log"] = "\n".join(notes)
        yield out(f"❌ Hata (Gemini): {e}")
        return
    pre = "\n".join(notes + ([f"⚠️ Prompt uyarısı: {' | '.join(problems)}"] if problems else []))
    label = config.METHODS[method]["label"].split(" (")[0]
    yield out(f"⏳ 3/3 Video üretiliyor ({label}, {seconds} sn)… İlk üretimde model indirme ~6 dk sürer.")
    last_log = ""
    for log, v_left, v_right, files, _sheets in _generate_job(state["prompt"], [method], resolution, seconds, seed,
                                                            idea, state["brief"], refs, style, picks, styled,
                                                            ref_roles):
        last_log = log or ""
        state["log"] = (pre + "\n" + last_log).strip()
        state["files"] = files
        state["video"] = v_left or v_right
        tail = [ln for ln in last_log.splitlines() if ln.strip()]
        step = tail[-1].split("] ", 1)[-1].strip() if tail else ""
        if state["video"]:
            yield out(f"⏳ 3/3 Video hazır, kontrol ediliyor… {step}")
        else:
            yield out(f"⏳ 3/3 Video üretiliyor ({label})… {step}")
    errors = [ln.split("] ", 1)[-1] for ln in last_log.splitlines() if "❌" in ln]
    if state["video"] and os.path.isfile(state["video"]):
        where = f" · Drive: {_state['drive_dir']}" if _state.get("drive_dir") else ""
        yield out(f"✅ Hazır: {os.path.basename(state['video'])}{where}")
    else:
        yield out(errors[-1] if errors else "❌ Hata: video üretilemedi; ayrıntılı günlüğe bakın.")


generate = _in_background(_generate_job, "generate")
quick_generate = _in_background(_quick_job, "quick_generate")
generate_long = _in_background(_generate_long_job, "generate_long")
reroll_block = _in_background(_reroll_job, "reroll_block")


def load_or_follow(poll=3):
    """Süren bir üretim varsa günlüğünü canlı gösterir; iş bitince (ya da hiç yoksa) son üretimi diskten yükler."""
    keep = tuple(gr.update() for _ in range(10))
    while job_running():
        last = _job.get("last")
        log = last[0] if last else ""
        yield ("⏳ Arka planda süren üretim izleniyor (sekme kapansa da çalışmaya devam eder)…\n\n" + log,) + keep
        _job["thread"].join(timeout=poll)
    yield load_last_outputs()


class ColabProxyHost:
    """ASGI ara katmanı: Colab'in `*.colab.dev` proxy'si (kernel.proxyPort) isteği VM'in iç adresine
    (`http://…internal:8007`) iletir ve `x-forwarded-host` eklemez; Gradio da video/görsel adreslerini bu iç
    adresle üretir, tarayıcı onlara ulaşamaz. Tarayıcının kendi gönderdiği Origin/Referer başlığındaki dış adres
    `*.colab.dev` ise onu `x-forwarded-host` (https) olarak ekler. Başka hiçbir isteğe dokunmaz."""

    SUFFIX = ".colab.dev"

    def __init__(self, app):
        self.app = app

    @classmethod
    def external_host(cls, headers):
        h = {k.lower(): v for k, v in headers}
        if b"x-forwarded-host" in h:
            return None
        from urllib.parse import urlsplit
        for key in (b"origin", b"referer"):
            raw = h.get(key)
            if not raw:
                continue
            parts = urlsplit(raw.decode("latin-1"))
            if parts.scheme == "https" and (parts.hostname or "").endswith(cls.SUFFIX):
                return parts.netloc
        return None

    async def __call__(self, scope, receive, send):
        if scope.get("type") in ("http", "websocket"):
            host = self.external_host(scope.get("headers") or [])
            if host:
                scope = dict(scope)
                scope["headers"] = list(scope["headers"]) + [(b"x-forwarded-host", host.encode("latin-1")),
                                                              (b"x-forwarded-proto", b"https")]
        await self.app(scope, receive, send)


CSS = """
.h3-title h1 {margin-bottom: 0}
.h3-note {opacity: .8; font-size: .9em}
"""


def build():
    with gr.Blocks(title="H3 Video Stüdyosu") as demo:
        gr.Markdown("# H3 Video Stüdyosu\nKısa fikrinizi yazın → Gemini detaylı brief'e ve MiniMax-H3'ün resmi prompt yapısına "
                    "çevirsin → isterseniz bir karakter görseliyle MiniMax-H3 Turbo, Pika H3 Flex ve/veya MiniMax-H3 ile video üretin.", elem_classes="h3-title")
        status = gr.Markdown(_status_line())

        with gr.Group(elem_id="hizli-uretim"):
            gr.Markdown("## ⚡ Hızlı üretim (tek düğme)\nFikri yazın, süreyi, stili ve yöntemi seçin ve "
                        "**Fikirden videoya: hepsini yap** düğmesine basın: brief, H3 prompt'u ve video sırayla yapılır, "
                        "durum aşağıda tek satırda yazar. Karakter / arka plan görseli kullanmak için 1. bölüme yükleyip "
                        "rollerini seçin; hızlı üretim onları da kullanır.", elem_classes="h3-note")
            q_idea = gr.Textbox(label="Fikir (replikleri ve ekran yazılarını tırnak içinde yazın)", lines=3,
                                elem_id="hizli-fikir",
                                placeholder='Örn: Kapadokya\'da bir çay ocağında yaşlı çaycı gence çay uzatıp '
                                            '"Buyur evlat, taze demlendi." diyor.')
            with gr.Row():
                q_seconds = gr.Slider(config.MIN_SECONDS, config.MAX_SECONDS, value=10, step=1, label="Süre (saniye)",
                                      elem_id="hizli-sure")
                q_style = gr.Radio([(v["label"], k) for k, v in config.STYLES.items()], value=config.DEFAULT_STYLE,
                                   label="Stil", elem_id="hizli-stil")
                q_method = gr.Radio(QUICK_METHODS, value="pika", label="Yöntem", elem_id="hizli-yontem")
            q_btn = gr.Button("Fikirden videoya: hepsini yap", variant="primary", elem_id="hizli-uret")
            q_status = gr.Textbox(label="Durum", interactive=False, lines=1, elem_id="hizli-durum")
            q_video = gr.Video(label="Video", interactive=False, elem_id="hizli-video")
            q_files = gr.File(label="İndir (video, prompt, bilgi, kontrol)", file_count="multiple", interactive=False,
                              elem_id="hizli-dosyalar")
            with gr.Accordion("Ayrıntılı günlük", open=False):
                q_log = gr.Textbox(lines=8, interactive=False, show_label=False, elem_id="hizli-gunluk")

        gr.Markdown("## 1 · Fikir")
        idea = gr.Textbox(label="Kısa fikir (herhangi bir dilde; ekranda görünecek yazıları ve replikleri tırnak içinde yazın)",
                          lines=4, placeholder='Örn: Gece yağmurlu bir İstanbul sokağı, neon tabelada "DUR, BİR BAK!" yazıyor…')
        with gr.Row():
            refs = gr.File(label=f"Karakter / referans görselleri (isteğe bağlı, en fazla {config.MAX_REF_IMAGES})",
                           file_count="multiple", file_types=["image"], scale=2)
            ref_preview = gr.Gallery(label="Önizleme (numara ve rol)", columns=3, height=180, scale=1,
                                     interactive=False)
        with gr.Accordion("Görsel rolleri: hangi görsel kim ya da ne?", open=True):
            gr.Markdown("Her görsel için rol seçin. **Karakter**ler yükleme sırasıyla Karakter 1, 2… olur ve "
                        "konuşurlarsa S1, S2… konuşmacısıdır. **Arka plan / mekân** görselinden kişi çıkarılmaz, sahne "
                        "o mekânda geçer. **Nesne** bir eşyadır. İsterseniz ad verin (ör. Çaycı Ahmet) ve fikirde bu "
                        "adla anın.", elem_classes="h3-note")
            role_rows, role_dds, role_names = [], [], []
            for i in range(config.MAX_REF_IMAGES):
                with gr.Row(visible=False) as row:
                    role_dds.append(gr.Dropdown(ROLE_CHOICES, value=prompt_writer.ROLE_CHARACTER,
                                                label=f"Görsel {i + 1} rolü", scale=1))
                    role_names.append(gr.Textbox(label=f"Görsel {i + 1} adı (isteğe bağlı)",
                                                 placeholder="ör. Çaycı Ahmet", scale=2))
                role_rows.append(row)
            ref_roles = gr.State([])
        style = gr.Radio([(v["label"], k) for k, v in config.STYLES.items()], value=config.DEFAULT_STYLE,
                         label="Stil (prompt'tan önce seçin)")
        with gr.Accordion("Çizgi / 3D stilde karakter görseli", open=False):
            gr.Markdown("Anime, Disney Pixar ya da Suluboya seçtiyseniz görselleri önce o stilde çizdirin: Gemini "
                        "karakterleri baştan ayağa fikirdeki kıyafetle, arka planı insansız bir mekân olarak, nesneyi "
                        "tek başına çizer; her görsel için 2 seçenek gelir, birini işaretleyin. İşaretlenmeyen "
                        "görselin yerine yüklenen hâli kullanılır; sıra ve roller değişmez.", elem_classes="h3-note")
            stylize_btn = gr.Button("Görselleri seçilen stilde çizdir")
            styled_gallery = gr.Gallery(label="Stilde çizilen görseller", columns=4, height=220, interactive=False)
            picks = gr.CheckboxGroup([], label="Kullanılacak görseller")
            stylize_msg = gr.Markdown()
            styled = gr.State({})
        with gr.Row():
            seconds = gr.Slider(config.MIN_SECONDS, config.MAX_SECONDS, value=15, step=1, label="Süre (saniye)")
            model = gr.Dropdown(label="Gemini modeli", choices=[], allow_custom_value=True)
        with gr.Row():
            key = gr.Textbox(label="Gemini API anahtarı", type="password", scale=3,
                             placeholder="Colab Secrets'ta GEMINI varsa boş bırakın")
            list_btn = gr.Button("Modelleri listele", scale=1)
        expand_btn = gr.Button("Gemini ile detaylandır (brief)", variant="primary")
        brief = gr.Textbox(label="Detaylı brief (Gemini yazar; düzenleyebilir ya da doğrudan kendi brief'inizi yazabilirsiniz)",
                           lines=8)
        rewrite_btn = gr.Button("H3 prompt'una çevir", variant="primary")
        rewrite_msg = gr.Markdown()

        gr.Markdown("## 2 · H3 prompt'u\nResmi H3 yapısında prompt; görsel yüklendiyse altı bölümlü referans (Ref2VA) yapısı. "
                    "Üretmeden önce düzenleyebilirsiniz.", elem_classes="h3-note")
        h3_prompt = gr.Textbox(label="H3 prompt'u", lines=14)

        gr.Markdown("## 3 · Üretim")
        with gr.Row():
            methods = gr.CheckboxGroup([(v["label"], k) for k, v in config.METHODS.items()], value=["pika"],
                                       label="Yöntem", scale=3)
            with gr.Column(scale=2):
                resolution = gr.Dropdown(list(config.RESOLUTIONS), value=list(config.RESOLUTIONS)[0], label="Boyut")
                seed = gr.Number(value=22, precision=0, label="Seed")
        with gr.Row():
            gen_btn = gr.Button("Video üret", variant="primary", scale=3)
            load_btn = gr.Button("📂 Son Üretimleri Yükle (Bağlantı Koptuysa)", scale=1)

        gr.Markdown("## 4 · Sonuç")
        logbox = gr.Textbox(label="Durum", lines=10, autoscroll=True, interactive=False)
        with gr.Row():
            pika_video = gr.Video(label="Pika H3 Flex / H3 Turbo (Taslak)", interactive=False)
            h3_video = gr.Video(label="MiniMax-H3 (Final)", interactive=False)
        checks = gr.Gallery(label="Kontrol: videonun anları ve %100 kırpıntılar (eller, yüz, yazı)", columns=2,
                            height=360, interactive=False)
        files = gr.File(label="İndir (videolar, prompt, bilgi, kontrol)", file_count="multiple", interactive=False)

        with gr.Accordion("🎬 Uzun Video · Çok Çekimli Kurgu (15–60 sn)", open=False):
            gr.Markdown(
                "15 saniyeden uzun videolar **15 saniyelik çok çekimli bloklar** halinde üretilir ve `ffmpeg` ile kare-tam birleştirilir. "
                "Her blok kendi içinde `[Shot N] At 00:SS.000` ile 2–4 çekim içerir; blok sınırlarında sonda kaymayı önlemek için "
                "her blok ~0,5 sn sakin bir duruşla biter.", elem_classes="h3-note"
            )
            with gr.Row():
                total_seconds = gr.Slider(15, config.MAX_TOTAL_SECONDS, value=30, step=5,
                                          label="Toplam süre (saniye, 15 sn'lik bloklara bölünür)")
                audio_mode = gr.Radio([(v, k) for k, v in config.AUDIO_MODES.items()],
                                      value=config.DEFAULT_AUDIO_MODE, label="Ses modu")
            with gr.Row():
                music_file = gr.Audio(label="Telifsiz müzik dosyası (Müzikli mod için)", type="filepath", scale=3)
                keep_ambient = gr.Checkbox(value=False, label="Müzik altında blok ortam sesini (-12 dB) koru", scale=1)
            plan_btn = gr.Button("1 · Blok ve Çekim Tablosu Planla (Gemini)", variant="primary")
            long_msg = gr.Markdown()
            world_anchor = gr.Textbox(
                label="Ortak Karakter ve Dünya Çapası (tüm blokların prompt'una birebir girer)", lines=3
            )
            shot_table = gr.Dataframe(
                headers=["Blok", "Çekim", "Başlangıç (sn)", "Süre (sn)", "Kadraj / Plan", "Eylem", "Kamera", "Ses / Replik"],
                datatype=["number", "number", "number", "number", "str", "str", "str", "str"],
                interactive=True, label="Blok ve Çekim Tablosu (düzenleyebilirsiniz)",
            )
            blocks_prompts_btn = gr.Button("2 · Blokların H3 Prompt'larını Hazırla", variant="primary")
            block_prompts_box = gr.Textbox(
                label="Blok H3 Prompt'ları (`=== BLOK N (S sn) ===` ile ayrılır, üretmeden önce düzenleyebilirsiniz)",
                lines=12,
            )
            gen_blocks_btn = gr.Button("3 · Tüm Blokları Üret ve Birleştir", variant="primary")
            gr.Markdown("### Blok Bazlı Tekil Yeniden Üretim (Seçmeli Re-roll) ve Yeniden Birleştirme\n"
                        "Beğenmediğiniz tek bir bloğu farklı bir Seed ile yeniden üretip diğer bloklara dokunmadan birleştirebilirsiniz.",
                        elem_classes="h3-note")
            with gr.Row():
                reroll_block_num = gr.Dropdown(choices=[1, 2, 3, 4], value=1, label="Blok No")
                reroll_seed = gr.Number(value=42, precision=0, label="Yeni Seed")
                reroll_method = gr.Dropdown([(v["label"], k) for k, v in config.METHODS.items()],
                                            value="pika", label="Yöntem")
                reroll_btn = gr.Button("Seçili Bloğu Yeniden Üret ve Birleştir")
                reassemble_btn = gr.Button("Mevcut Blokları Yeniden Birleştir")
            block_videos_gallery = gr.Gallery(label="Üretilen Blok Önizlemeleri (Blok 1..N)", columns=4, height=220,
                                              interactive=False)
            blocks_state = gr.State({})

        list_btn.click(list_models, [key], [model, rewrite_msg])
        key.submit(list_models, [key], [model, rewrite_msg])
        key.blur(list_models, [key], [model, rewrite_msg])
        refs.change(_on_refs, [refs], [ref_preview, *role_rows, *role_dds, *role_names, ref_roles])
        for comp in [*role_dds, *role_names]:
            comp.change(_collect_roles, [refs, *role_dds, *role_names], [ref_roles, ref_preview])
        stylize_btn.click(do_stylize, [refs, style, key, idea, ref_roles], [styled_gallery, picks, styled, stylize_msg])
        style.change(lambda: (None, gr.update(choices=[], value=[]), {}), None, [styled_gallery, picks, styled])
        expand_btn.click(do_expand, [idea, seconds, model, key, refs, style, picks, styled, ref_roles],
                         [brief, rewrite_msg])
        rewrite_btn.click(do_rewrite, [idea, brief, seconds, model, key, refs, style, picks, styled, ref_roles],
                          [h3_prompt, rewrite_msg])
        gen_btn.click(generate, [h3_prompt, methods, resolution, seconds, seed, idea, brief, refs, style, picks, styled,
                                 ref_roles],
                      [logbox, pika_video, h3_video, files, checks], concurrency_limit=1)
        load_btn.click(
            load_or_follow,
            None,
            [logbox, pika_video, h3_video, files, checks, h3_prompt,
             block_prompts_box, world_anchor, shot_table, block_videos_gallery, blocks_state],
        )
        plan_btn.click(do_plan_shots, [idea, total_seconds, audio_mode, model, key, refs, style, picks, styled,
                                       ref_roles],
                       [world_anchor, shot_table, long_msg])
        blocks_prompts_btn.click(
            do_rewrite_blocks,
            [idea, world_anchor, shot_table, audio_mode, model, key, refs, style, picks, styled, ref_roles],
            [block_prompts_box, reroll_block_num, long_msg],
        )
        gen_blocks_btn.click(
            generate_long,
            [block_prompts_box, world_anchor, shot_table, audio_mode, music_file, keep_ambient,
             methods, resolution, seed, idea, refs, style, picks, styled, ref_roles],
            [logbox, pika_video, h3_video, block_videos_gallery, files, checks, blocks_state],
            concurrency_limit=1,
        )
        reroll_btn.click(
            reroll_block,
            [reroll_block_num, reroll_seed, reroll_method, block_prompts_box, audio_mode, music_file, keep_ambient, blocks_state],
            [logbox, pika_video, h3_video, block_videos_gallery, files, checks, blocks_state],
            concurrency_limit=1,
        )
        reassemble_btn.click(
            reassemble_blocks,
            [audio_mode, music_file, keep_ambient, blocks_state],
            [logbox, pika_video, h3_video, files],
        )
        q_btn.click(quick_generate,
                    [q_idea, q_seconds, q_style, q_method, resolution, seed, model, key, refs, ref_roles, picks, styled],
                    [q_status, brief, h3_prompt, q_video, q_files, q_log], concurrency_limit=1)
        # Stil seçimi iki yerde: kullanıcı hangisini değiştirirse öbürü de aynı olur (yalnızca elle değişimde)
        q_style.input(lambda v: v, q_style, style)
        style.input(lambda v: v, style, q_style)
        demo.load(lambda: _status_line(), None, status)
        if _state["secret_key"] or FAKE:
            demo.load(list_models, [key], [model, rewrite_msg])
    return demo


def launch(drive_dir=None, model_dirs=None, model_save_dir=None, **kwargs):
    """Colab'de: hücrenin altında açılır ve arka planda çalışmaya devam eder.
    model_dirs: model dosyalarının Hugging Face'ten önce aranacağı klasörler (ör. Drive'daki kopyalar).
    model_save_dir: verilirse Drive'da olmayan modeller indirildikten sonra arka planda buraya da kaydedilir."""
    _state["secret_key"] = _colab_secret("GEMINI") or _colab_secret("GEMINI_API_KEY")
    _state["drive_dir"] = drive_dir
    config.MODEL_SOURCE_DIRS = [d for d in (model_dirs or []) if d]
    config.MODEL_SAVE_DIR = model_save_dir or None
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    demo = build()
    demo.queue(default_concurrency_limit=1)
    # share=False: Gradio Colab'de aksi halde herkese açık bir gradio.live bağlantısı açar; uygulama
    # yalnızca Colab'in kendi (oturum açmış kullanıcıya özel) proxy'si üzerinden görünsün.
    allowed = list({os.path.abspath(config.OUTPUT_DIR), os.path.abspath(config.WORK_DIR), tempfile.gettempdir()})
    from starlette.middleware import Middleware
    opts = dict(share=False, inline=True, prevent_thread_lock=True, height=1400, allowed_paths=allowed,
                css=CSS, theme=gr.themes.Soft(), show_error=True,
                app_kwargs={"middleware": [Middleware(ColabProxyHost)]})
    opts.update(kwargs)
    return demo.launch(**opts)
