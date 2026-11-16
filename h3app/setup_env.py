"""Colab runtime hazırlığı: ComfyUI kurulumu ve model dosyalarının indirilip doğrulanması."""

import hashlib
import os
import queue
import shutil
import subprocess
import sys
import threading
import time

from . import config


def gpu():
    """(ad, bellek GB, blackwell_mi). GPU yoksa None."""
    try:
        import torch
    except ImportError:
        return None
    if not torch.cuda.is_available():
        return None
    p = torch.cuda.get_device_properties(0)
    return p.name, round(p.total_memory / 1e9), torch.cuda.get_device_capability(0)[0] >= 10


def text_encoder_role():
    """NVFP4 metin kodlayıcı Blackwell (ör. G4 / RTX PRO 6000) ister; diğer GPU'larda int8 sürümü."""
    g = gpu()
    return "te_nvfp4" if g and g[2] else "te_int8"


def ensure_comfy(log=print):
    if not os.path.isdir(os.path.join(config.COMFY_DIR, ".git")):
        log("ComfyUI indiriliyor…")
        subprocess.run(["git", "clone", "-q", config.COMFY_REPO, config.COMFY_DIR], check=True)
    subprocess.run(["git", "-C", config.COMFY_DIR, "fetch", "-q", "--all"], check=False)
    subprocess.run(["git", "-C", config.COMFY_DIR, "checkout", "-q", config.COMFY_COMMIT], check=True)
    stamp = os.path.join(config.COMFY_DIR, ".h3app_requirements")
    if not os.path.isfile(stamp):
        log("ComfyUI bağımlılıkları kuruluyor (~1 dk)…")
        r = subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r",
                            os.path.join(config.COMFY_DIR, "requirements.txt")], capture_output=True, text=True)
        if r.returncode:
            raise RuntimeError("ComfyUI kurulamadı:\n" + r.stderr[-2000:])
        open(stamp, "w").write(config.COMFY_COMMIT)
    log(f"ComfyUI hazır ({config.COMFY_COMMIT}).")


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(64 << 20), b""):
            h.update(b)
    return h.hexdigest()


def _index_dirs(dirs):
    """Kaynak klasörlerdeki dosyalar: ad -> yollar (Drive'da 01/03 notebook'larının indirdiği kopyalar)."""
    idx = {}
    for root in dirs or ():
        if not os.path.isdir(root):
            continue
        for dp, _, names in os.walk(root):
            for n in names:
                idx.setdefault(n, []).append(os.path.join(dp, n))
    return idx


def _copy_verified(src, dst, size, sha, log):
    """Kaynaktan yerel diske kopyalar ve boyut + SHA-256 doğrular; tutmazsa siler ve False döner."""
    part = dst + ".part"
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    try:
        shutil.copyfile(src, part)
        if os.path.getsize(part) == size and _sha256(part) == sha:
            os.replace(part, dst)
            return True
        log(f"Drive kopyası doğrulanamadı, Hugging Face'ten indirilecek: {os.path.basename(dst)}")
    except OSError as e:
        log(f"Drive'dan kopyalanamadı ({e}); Hugging Face'ten indirilecek.")
    if os.path.exists(part):
        os.remove(part)
    return False


_save_queue = queue.Queue()
_save_worker = None
_save_pending = []


def _save_loop():
    while True:
        job = _save_queue.get()
        try:
            _save_one(*job)
        finally:
            _save_queue.task_done()


def _save_one(src, dest, size, log):
    """Doğrulanmış yerel model dosyasını Drive'a kopyalar (.part → ad). Yer yoksa ya da hata olursa atlar."""
    name = os.path.basename(dest)
    try:
        if os.path.isfile(dest) and os.path.getsize(dest) == size:
            return
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        free = shutil.disk_usage(os.path.dirname(dest)).free
        if free < size * 1.02:
            log(f"💾 Drive'da yer yok ({free / 1e9:.1f} GB boş, {size / 1e9:.1f} GB gerekli); "
                f"{name} Drive'a kaydedilmedi.")
            return
        part = dest + ".part"
        shutil.copyfile(src, part)
        if os.path.getsize(part) != size:
            os.remove(part)
            log(f"💾 Drive kopyası eksik çıktı, silindi: {name}")
            return
        os.replace(part, dest)
        log(f"💾 Drive'a kaydedildi: {name} (sonraki oturumda buradan alınır)")
    except OSError as e:
        if os.path.exists(dest + ".part"):
            try:
                os.remove(dest + ".part")
            except OSError:
                pass
        log(f"💾 {name} Drive'a kaydedilemedi ({e}); üretim etkilenmez.")


def queue_model_save(src, dest, size, log=print):
    """Kopyayı arka plandaki tek işçiye sıraya koyar; üretim beklemez."""
    global _save_worker
    if _save_worker is None or not _save_worker.is_alive():
        _save_worker = threading.Thread(target=_save_loop, daemon=True, name="h3app-model-save")
        _save_worker.start()
    _save_pending.append(dest)
    _save_queue.put((src, dest, size, log))


def wait_model_saves(timeout=None):
    """Sıradaki Drive kopyalarının bitmesini bekler (testler ve kapanış için). Bittiyse True."""
    t0 = time.time()
    while _save_queue.unfinished_tasks:
        if timeout is not None and time.time() - t0 > timeout:
            return False
        time.sleep(0.05)
    return True


def ensure_models(roles, log=print, source_dirs=None, save_dir=None):
    """Eksik modelleri önce `source_dirs` (varsayılan config.MODEL_SOURCE_DIRS, ör. Drive) içindeki doğrulanmış
    kopyalardan, yoksa sabit Hugging Face revizyonundan alır. Her dosya boyut + SHA-256 ile doğrulanır.
    `save_dir` (varsayılan config.MODEL_SAVE_DIR) verilmişse Drive'da bulunmayan her model, doğrulandıktan sonra
    arka planda oraya da kopyalanır (`save_dir/<alt klasör>/<ad>`), böylece sonraki oturum Drive'dan alır."""
    source_dirs = config.MODEL_SOURCE_DIRS if source_dirs is None else source_dirs
    save_dir = config.MODEL_SAVE_DIR if save_dir is None else save_dir
    idx = None
    for role in roles:
        rel, sub, size, sha = config.MODELS[role]
        name = os.path.basename(rel)
        dst = os.path.join(config.COMFY_DIR, "models", sub, name)
        if idx is None and (save_dir or not (os.path.isfile(dst) and os.path.getsize(dst) == size)):
            idx = _index_dirs(list(source_dirs or []) + ([save_dir] if save_dir else []))
        on_drive = idx is not None and any(os.path.getsize(p) == size for p in idx.get(name, []))
        if not (os.path.isfile(dst) and os.path.getsize(dst) == size):
            src = next((p for p in (idx or {}).get(name, []) if os.path.getsize(p) == size), None)
            if src:
                log(f"Drive'dan kopyalanıyor: {name} ({size / 1e9:.1f} GB)…")
                if _copy_verified(src, dst, size, sha, log):
                    log(f"Doğrulandı: {name}")
                    continue
            from huggingface_hub import hf_hub_download
            log(f"İndiriliyor: {name} ({size / 1e9:.1f} GB)…")
            p = hf_hub_download(config.HF_REPO, rel, revision=config.HF_REVISION,
                                local_dir=os.path.join(config.WORK_DIR, "h3app_hf"))
            if os.path.getsize(p) != size or _sha256(p) != sha:
                os.remove(p)
                raise RuntimeError(f"Bozuk indirme: {rel}")
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            os.replace(p, dst)
            log(f"Doğrulandı: {name}")
        if save_dir and not on_drive:
            log(f"💾 {name} arka planda Drive'a da kaydedilecek ({size / 1e9:.1f} GB).")
            queue_model_save(dst, os.path.join(save_dir, sub, name), size, log)


def roles_for(methods, te_role, ref=False):
    roles = ["unet_ref" if ref else "unet", te_role, "vae_video", "vae_audio"]
    if "turbo" in methods:
        roles.append("turbo_lora_ref" if ref else "turbo_lora")
    if "pika" in methods:
        roles.append("pika_lora_ref" if ref else "pika_lora")
    return roles
