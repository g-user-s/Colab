#!/usr/bin/env python3
"""Bir videoyu Gemini'ye BU MAKİNEDEN izletir (h3app.review.review_video ile aynı kontrol listesi).

Neden: Muse'un kasası makineye gerçek anahtar yerine bir yer tutucu koyar; Gemini istekleri ancak bu makineden
çıkarken gerçek anahtarla değişir. Colab runtime'ından yapılan izleme bu yüzden çalışmaz; izleme burada yapılır.

Kullanım:
  python muse/izle.py --video V.mp4 --senaryo senaryo.json [--cikti inceleme.json]
  python muse/izle.py --video V.mp4 --prompt-dosyasi V_prompt.txt
Uzun video için birleşik videonun sürekliliği:
  python muse/izle.py --video birlesik.mp4 --senaryo uzun_senaryo.json --sureklilik

Çıktı: JSON (verdict, defects[start_s,end_s,severity,category,description], summary, model) ve kısa Türkçe özet.
Çıkış kodları: 0 = izlendi, 1 = hata, 3 = hiçbir Gemini modeli izleyemedi.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ortak  # noqa: E402
from senaryo import h3_yukle  # noqa: E402


def main(argv=None):
    p = argparse.ArgumentParser(description="Videoyu Gemini'ye bu makineden izlet")
    p.add_argument("--video", required=True)
    p.add_argument("--senaryo", help="senaryo.json / uzun_senaryo.json (prompt, referanslar ve hikâye buradan)")
    p.add_argument("--prompt-dosyasi", help="Senaryo yoksa: üretimde kullanılan prompt dosyası")
    p.add_argument("--sureklilik", action="store_true", help="Uzun video: süreklilik puanı (1–10)")
    p.add_argument("--cikti", help="Sonucun yazılacağı JSON dosyası")
    p.add_argument("--anahtar", default="~/.config/h3muse/gemini.key")
    p.add_argument("--h3")
    a = p.parse_args(argv)
    if not os.path.isfile(a.video):
        raise SystemExit(f"Video yok: {a.video}")
    anahtar = ortak.anahtar_oku(a.anahtar)
    h3_yukle(a.h3)
    from h3app import review, uzun

    senaryo = ortak.json_oku(a.senaryo) if a.senaryo else {}
    if a.sureklilik:
        if senaryo.get("tur") != "uzun":
            raise SystemExit("--sureklilik için uzun_senaryo.json ver.")
        bloklar = next(iter(senaryo["kollar"].values()))["bloklar"]
        print("⏳ Gemini sürekliliği izliyor…", flush=True)
        sonuc = review.continuity_review(a.video, uzun.block_cuts(bloklar), senaryo.get("hikaye") or {}, anahtar,
                                         log=print)
        if not sonuc:
            print("❌ Hiçbir Gemini modeli izleyemedi.")
            return 3
        ozet = ", ".join(f"{k} {sonuc.get(k)}" for k in review.SURECLILIK_PUANLARI) + f" · ortalama {sonuc['ortalama']}"
    else:
        if a.prompt_dosyasi:
            prompt = open(a.prompt_dosyasi, encoding="utf-8").read()
        elif senaryo.get("prompt"):
            prompt = senaryo["prompt"]
        else:
            raise SystemExit("Prompt bulunamadı: --senaryo (tek video) ya da --prompt-dosyasi ver.")
        refs = [r["dosya"] for r in senaryo.get("referanslar") or [] if os.path.isfile(r["dosya"])]
        roller = [{"role": r["rol"], "name": r.get("ad", "")} for r in senaryo.get("referanslar") or []
                  if os.path.isfile(r["dosya"])] or None
        print("⏳ Gemini videoyu izliyor…", flush=True)
        sonuc = review.review_video(a.video, prompt, anahtar, refs, roller, log=print)
        if not sonuc:
            print("❌ Hiçbir Gemini modeli izleyemedi.")
            return 3
        ozet = review.summary(sonuc)
    if a.cikti:
        ortak.json_yaz(a.cikti, sonuc)
        print(f"Sonuç: {a.cikti}")
    print(ozet)
    return 0


if __name__ == "__main__":
    sys.exit(main())
