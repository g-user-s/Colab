"""Arka planda çalışan ComfyUI sunucusu ve iş kuyruğu."""

import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

from . import config

API = f"http://127.0.0.1:{config.COMFY_PORT}"
_server = None


def _get(path, timeout=10):
    return json.load(urllib.request.urlopen(API + path, timeout=timeout))


def _post(path, body):
    req = urllib.request.Request(API + path, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        return json.load(urllib.request.urlopen(req, timeout=60))
    except urllib.error.HTTPError as e:
        raise RuntimeError("ComfyUI isteği reddetti:\n" + e.read().decode()[:3000]) from None


def running():
    try:
        _get("/system_stats", timeout=2)
        return True
    except Exception:
        return False


def start(log=print):
    global _server
    if running():
        return
    log("ComfyUI sunucusu başlatılıyor…")
    out = open(os.path.join(config.WORK_DIR, "h3app_comfyui.log"), "w")
    _server = subprocess.Popen([sys.executable, "main.py", "--listen", "127.0.0.1", "--port", str(config.COMFY_PORT)],
                               cwd=config.COMFY_DIR, stdout=out, stderr=subprocess.STDOUT)
    for _ in range(300):
        if running():
            log("ComfyUI sunucusu hazır.")
            return
        if _server.poll() is not None:
            break
        time.sleep(2)
    tail = open(os.path.join(config.WORK_DIR, "h3app_comfyui.log")).read()[-3000:]
    raise RuntimeError("ComfyUI başlamadı:\n" + tail)


def run(graph, dest, poll=5):
    """Grafiği kuyruğa koyar, bitene kadar her `poll` saniyede geçen süreyi verir (generator),
    sonunda videoyu `dest`e kopyalar ve yolunu döndürür (StopIteration.value)."""
    pid = _post("/prompt", {"prompt": graph})["prompt_id"]
    t0 = time.time()
    while True:
        h = _get(f"/history/{pid}")
        if pid in h and h[pid].get("status", {}).get("completed") is not None:
            break
        yield int(time.time() - t0)
        time.sleep(poll)
    st = h[pid]["status"]
    if st.get("status_str") != "success":
        msgs = [m for m in st.get("messages", []) if m and m[0] == "execution_error"]
        raise RuntimeError("Üretim başarısız: " + json.dumps(msgs[-1][1] if msgs else st)[:2000])
    files = [v for o in h[pid]["outputs"].values() for k in ("images", "videos", "gifs") for v in o.get(k, [])]
    src = os.path.join(config.COMFY_DIR, "output", files[0]["subfolder"], files[0]["filename"])
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    shutil.copyfile(src, dest)
    return dest
