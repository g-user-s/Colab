#!/usr/bin/env python3
"""Testler için sahte `colab` komutu. Gerçek CLI'nın çıktı biçimlerini taklit eder.

Ortam değişkenleri:
  SAHTE_KOK      : sahte runtime'ın kök klasörü ("/content" bunun altında "content" olur)
  SAHTE_PLAN     : GPU davranışı, ör. "g4:503,h100:red,a100:ok" (ok | 503 | red | 411)
  SAHTE_PYTHON   : runtime'da kodu çalıştıracak python
  SAHTE_GPU      : nvidia-smi çıktısı, ör. "NVIDIA A100-SXM4-40GB, 40960"
Her çağrı SAHTE_KOK/cagrilar.jsonl dosyasına yazılır.
"""

import json
import os
import shutil
import subprocess
import sys

KOK = os.environ["SAHTE_KOK"]
DURUM = os.path.join(KOK, "durum_cli.json")


def oku():
    return json.load(open(DURUM)) if os.path.isfile(DURUM) else {"oturumlar": {}, "denemeler": {}, "bakiye": 300.0}


def kaydet(d):
    json.dump(d, open(DURUM, "w"))


def yerel(uzak):
    return os.path.join(KOK, uzak.lstrip("/"))


def secenek(args, ad):
    return args[args.index(ad) + 1] if ad in args else None


def main():
    args = sys.argv[1:]
    os.makedirs(KOK, exist_ok=True)
    with open(os.path.join(KOK, "cagrilar.jsonl"), "a") as f:
        f.write(json.dumps(args) + "\n")
    d = oku()
    komut = args[0]
    if komut == "new":
        ad, gpu = secenek(args, "-s"), secenek(args, "--gpu") or "cpu"
        plan = dict(p.split(":") for p in os.environ.get("SAHTE_PLAN", "g4:ok").split(","))
        davranis = plan.get(gpu, "red")
        d["denemeler"][gpu] = d["denemeler"].get(gpu, 0) + 1
        kaydet(d)
        print(f"[colab] Creating session '{ad}'...")
        if davranis == "503":
            print("ColabRequestError: Failed to issue request POST ...: Service Unavailable 503", file=sys.stderr)
            return 1
        if davranis == "411":
            print("ColabRequestError: 411 Length Required", file=sys.stderr)
            return 1
        if davranis == "red":
            print(f"[colab] Backend rejected accelerator '{gpu.upper()}'. You may not have quota or entitlement",
                  file=sys.stderr)
            return 1
        d["oturumlar"][ad] = gpu
        kaydet(d)
        print("[colab] Session READY.")
        return 0
    if komut == "exec" and int(os.environ.get("SAHTE_ASILMA", "0")) > d.get("asilma", 0) and "is_no" in open(secenek(args, "-f")).read() and "Popen" in open(secenek(args, "-f")).read():
        d["asilma"] = d.get("asilma", 0) + 1     # iş başlatma komutu takılır (rc 124, çıktı yok)
        kaydet(d)
        return 124
    if komut == "exec" and int(os.environ.get("SAHTE_ZAMAN_ASIMI", "0")) > d.get("zaman_asimi", 0):
        d["zaman_asimi"] = d.get("zaman_asimi", 0) + 1
        kaydet(d)
        print("requests.exceptions.ReadTimeout: HTTPSConnectionPool(host='x.colab.dev', port=443): "
              "Read timed out. (read timeout=10)", file=sys.stderr)
        return 1
    if komut == "exec":
        ad, dosya = secenek(args, "-s"), secenek(args, "-f")
        if ad not in d["oturumlar"]:
            print(f"[colab] Session '{ad}' appears to be lost (404/401). Cleaning up.")
            return 1
        kod = open(dosya).read().replace("/content", os.path.join(KOK, "content"))
        bin_dizin = os.path.join(KOK, "bin")
        os.makedirs(bin_dizin, exist_ok=True)
        smi = os.path.join(bin_dizin, "nvidia-smi")
        with open(smi, "w") as f:
            f.write(f"#!/bin/sh\necho '{os.environ.get('SAHTE_GPU', 'NVIDIA A100-SXM4-40GB, 40960')}'\n")
        os.chmod(smi, 0o755)
        env = dict(os.environ, PATH=bin_dizin + os.pathsep + os.environ["PATH"],
                   H3APP_WORK_DIR=os.path.join(KOK, "content"))
        r = subprocess.run([os.environ.get("SAHTE_PYTHON", sys.executable), "-c", kod], capture_output=True,
                           text=True, env=env, cwd=KOK)
        sys.stdout.write(r.stdout)
        sys.stdout.write(r.stderr)
        return 0   # gerçek CLI de Python hatasında 0 döner
    if komut == "upload":
        ad, kaynak, hedef = secenek(args, "-s"), args[-2], args[-1]
        os.makedirs(os.path.dirname(yerel(hedef)), exist_ok=True)
        shutil.copyfile(kaynak, yerel(hedef))
        print(f"[colab] Uploaded '{kaynak}' to '{hedef}'")
        return 0
    if komut == "download":
        kaynak, hedef = args[-2], args[-1]
        if not os.path.isfile(yerel(kaynak)):
            print(f"[colab] Download failed: File or directory not found: {kaynak}")
            return 1
        shutil.copyfile(yerel(kaynak), hedef)
        print(f"[colab] Downloaded '{kaynak}' to '{hedef}'")
        return 0
    if komut == "stop":
        ad = secenek(args, "-s")
        if ad not in d["oturumlar"]:
            print(f"[colab] Session '{ad}' not found.")
            return 0
        d["oturumlar"].pop(ad)
        d["bakiye"] -= 0.5
        kaydet(d)
        print(f"[colab] Stopping session '{ad}'...\n[colab] Session terminated.")
        return 0
    if komut == "sessions":
        if not d["oturumlar"]:
            print("[colab] No active sessions found on server.")
        for ad, gpu in d["oturumlar"].items():
            print(f"{ad}  {gpu.upper()}  GPU")
        return 0
    if komut == "usage":
        print(f"Current balance: {d['bakiye']:.2f} compute units\nUsage rate: 0.00/hr\n"
              f"Active assignments: {len(d['oturumlar'])}")
        return 0
    print(f"bilinmeyen komut {komut}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
