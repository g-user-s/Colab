"""Gemini/Gemma hız testi: anahtarın görebildiği tüm metin modellerine (Gemini + Gemma) aynı kısa isteği gönderir ve her biri için
ilk parçanın kaç saniyede geldiğini (uygulamanın 20 sn sınırının ölçtüğü şey) ve yanıtın kaç saniyede
bittiğini tablo olarak gösterir.

Kullanım:
    python tools/gemini_hiz_testi.py                 # anahtar: GEMINI / GEMINI_API_KEY ortam değişkeni
    python tools/gemini_hiz_testi.py --key-file anahtar.txt
    python tools/gemini_hiz_testi.py --limit 30 --paralel 4 --json sonuc.json
    python tools/gemini_hiz_testi.py --filtre gemma         # yalnızca adında "gemma" geçenler

Anahtar ekrana ya da dosyaya yazılmaz.
"""

import argparse
import concurrent.futures as cf
import json
import os
import queue
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from h3app import config, prompt_writer  # noqa: E402

PROMPT = ("Kapadokya'da akşamüstü küçük bir çay ocağını, bir film sahnesi gibi İngilizce olarak tek paragrafta "
          "(yaklaşık 80 kelime) anlat.")


def olc(key, model, limit):
    """(model, durum, ilk_parca_sn, toplam_sn, karakter). Süre `limit` sn'yi aşarsa 'zaman aşımı'."""
    from google.genai import types
    q, bitti = queue.Queue(), object()
    t0 = time.perf_counter()

    def work():
        try:
            client = prompt_writer._client(key, timeout_ms=int(limit * 1000) + 5000)
            cfg = types.GenerateContentConfig(temperature=0.3)
            for chunk in client.models.generate_content_stream(model=model, contents=[PROMPT], config=cfg):
                q.put((time.perf_counter(), getattr(chunk, "text", None) or ""))
        except Exception as e:
            q.put(e)
        finally:
            q.put(bitti)

    threading.Thread(target=work, daemon=True).start()
    ilk, metin, son = None, [], t0 + limit
    while True:
        try:
            item = q.get(timeout=max(0.05, son - time.perf_counter()))
        except queue.Empty:
            durum = "zaman aşımı (ilk parça yok)" if ilk is None else "zaman aşımı (yarım)"
            return model, durum, ilk, None, len("".join(metin))
        if item is bitti:
            break
        if isinstance(item, Exception):
            msg = str(item).replace("\n", " ")
            kod = next((c for c in ("429", "503", "404", "400", "403", "500", "504") if c in msg), "")
            return model, f"hata {kod}".strip() + f": {msg[:70]}", ilk, None, 0
        ts, txt = item
        if ilk is None and txt:
            ilk = ts - t0
        metin.append(txt)
    toplam = time.perf_counter() - t0
    n = len("".join(metin))
    return model, ("tamam" if n else "boş yanıt"), ilk, toplam, n


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--key-file", help="anahtarın tek satır olarak durduğu dosya")
    ap.add_argument("--limit", type=float, default=30.0, help="model başına en uzun bekleme (sn, varsayılan 30)")
    ap.add_argument("--paralel", type=int, default=4, help="aynı anda test edilen model sayısı (varsayılan 4)")
    ap.add_argument("--json", help="sonuçları bu dosyaya da yaz")
    ap.add_argument("--gemini-only", action="store_true", help="Gemma modellerini atla")
    ap.add_argument("--filtre", help="yalnızca adında bu metin geçen modeller (ör. gemma); her test günlük kotadan yer")
    a = ap.parse_args()

    key = (open(a.key_file, encoding="utf-8").read().strip() if a.key_file
           else (os.environ.get("GEMINI") or os.environ.get("GEMINI_API_KEY") or "").strip())
    if not key:
        sys.exit("Anahtar yok: GEMINI ortam değişkenini ayarlayın ya da --key-file verin.")

    modeller = prompt_writer.gemini_models(key)
    if not a.gemini_only:   # Gemma modelleri de aynı API'den sunulur; kotaları Gemini'den ayrıdır
        client = prompt_writer._client(key)
        modeller += sorted({(m.name or "").removeprefix("models/") for m in client.models.list()
                            if (m.name or "").removeprefix("models/").startswith("gemma")
                            and "generateContent" in (m.supported_actions or [])})
    if a.filtre:
        modeller = [m for m in modeller if a.filtre.lower() in m.lower()]
    print(f"{len(modeller)} model test ediliyor (model başına en fazla {a.limit:g} sn, {a.paralel} paralel)…\n",
          flush=True)
    sonuc = []
    with cf.ThreadPoolExecutor(max_workers=max(1, a.paralel)) as ex:
        for r in cf.as_completed([ex.submit(olc, key, m, a.limit) for m in modeller]):
            sonuc.append(r.result())
            m, durum, ilk, toplam, _ = sonuc[-1]
            print(f"  · {m}: {durum}" + (f" (ilk parça {ilk:.1f} sn)" if ilk is not None else ""), flush=True)

    calisan = sorted([r for r in sonuc if r[1] == "tamam"], key=lambda r: r[2])
    diger = sorted([r for r in sonuc if r[1] != "tamam"], key=lambda r: r[0])
    sinir = config.FIRST_CHUNK_SECONDS
    print(f"\n{'Model':<36} {'İlk parça':>10} {'Toplam':>8} {'Karakter':>9}  Durum")
    print("-" * 90)
    for m, durum, ilk, toplam, n in calisan + diger:
        f = lambda v: f"{v:.1f} sn" if v is not None else "—"
        isaret = "" if durum != "tamam" else ("  ✓" if ilk <= sinir else f"  > {sinir} sn sınırı")
        varsayilan = "  ← varsayılan" if m == config.GEMINI_MODEL else ""
        yedek = "  ← yedek" if m in config.GEMINI_FALLBACK_MODELS else ""
        print(f"{m:<36} {f(ilk):>10} {f(toplam):>8} {n:>9}  {durum}{isaret}{varsayilan}{yedek}")
    print(f"\nÇalışan: {len(calisan)}/{len(sonuc)} · uygulamanın ilk-parça sınırı: {sinir} sn")
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump([dict(zip(("model", "durum", "ilk_parca_sn", "toplam_sn", "karakter"), r)) for r in sonuc],
                      fh, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
