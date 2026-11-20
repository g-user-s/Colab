#!/usr/bin/env python3
"""Colab runtime'ında arka planda çalışır; her çağrıda TEK bir GPU işi yapar. Muse bunu elle çalıştırmaz;
h3_uret.py yükler, başlatır, yoklar, sonucu indirir.

Gemini'ye hiç gitmez: izleme, yeniden üretim kararı, süreklilik puanı ve köprü prompt'u Muse'un makinesinde yapılır
(Muse'un kasası anahtarı yalnızca o makineden çıkan isteklerde gerçek anahtarla değiştirir).

Girdi (DIZIN içinde): h3app.tar, senaryo.json, is.json, ref_*.png / kopru_*.png / kare_*.png
  is.json türleri:
    {"no": n, "tur": "tek", "seed": s}                       tek video (h3app.ui._generate_job, izlemesiz)
    {"no": n, "tur": "blok", "kol", "blok", "sure", "prompt", "seed", "refs": [dosya adları]}
        isteğe bağlı "kareler": [ilk, son] (dosya adı ya da null) — anahtar kareli FL2VA, refs boş olmalı
    {"no": n, "tur": "birlestir", "kol", "dosyalar": [dosya adları]}
Çıktı (DIZIN içinde): durum.json (sürekli güncellenir; "is_no" alanı), gunluk.txt, teslim_<no>_<i>.tar (bitince)
"""

import argparse
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import traceback

PARCA_SINIRI = 40 * 1024 * 1024      # Colab dosya aktarımı istek başına ~50 MB
TEK_DOSYA_SINIRI = 47 * 1024 * 1024


def simdi():
    return datetime.datetime.now().isoformat(timespec="seconds")


class Durum:
    def __init__(self, dizin, is_no=None):
        self.yol = os.path.join(dizin, "durum.json")
        self.veri = {"asama": "basliyor", "baslangic": simdi(), "pid": os.getpid(), "is_no": is_no}

    def yaz(self, **alanlar):
        self.veri.update(alanlar)
        self.veri["guncelleme"] = simdi()
        gecici = self.yol + ".tmp"
        with open(gecici, "w", encoding="utf-8") as f:
            json.dump(self.veri, f, ensure_ascii=False, indent=2)
        os.replace(gecici, self.yol)


class Gunluk:
    """Her satır gunluk.txt'ye eklenir ve durum.json'a son satır olarak yazılır."""

    def __init__(self, yol, durum):
        self.yol, self.durum, self.n = yol, durum, 0

    def __call__(self, mesaj):
        satir = f"[{datetime.datetime.now():%H:%M:%S}] {mesaj}"
        self.n += 1
        with open(self.yol, "a", encoding="utf-8") as f:
            f.write(satir + "\n")
        self.durum.yaz(son_satir=satir, satir_sayisi=self.n)


def sha256(yol):
    h = hashlib.sha256()
    with open(yol, "rb") as f:
        for parca in iter(lambda: f.read(1 << 20), b""):
            h.update(parca)
    return h.hexdigest()


def h3app_ac(dizin):
    """Yüklenen h3app.tar'ı DIZIN/repo altına açar (tar değiştiyse yeniden). Repo klasörünü döner."""
    repo = os.path.join(dizin, "repo")
    paket = os.path.join(dizin, "h3app.tar")
    if not os.path.isfile(paket):
        raise RuntimeError("h3app.tar yüklenmemiş.")
    imza = os.path.join(repo, ".tar_sha256")
    yeni = sha256(paket)
    if not (os.path.isfile(imza) and open(imza).read() == yeni):
        shutil.rmtree(os.path.join(repo, "h3app"), ignore_errors=True)
        os.makedirs(repo, exist_ok=True)
        with tarfile.open(paket) as t:
            t.extractall(repo, filter="data")
        open(imza, "w").write(yeni)
    return repo


def teslim_paketi(dizin, dosyalar, temel, no=0):
    """Çıktıları en fazla ~40 MB'lık tar parçalarına koyar; önce temel dosyalar. Her parça sha256 ile doğrulanır.
    47 MB'tan büyük tek dosyalar pakete girmez, listede kalır."""
    gunluk = os.path.join(dizin, "gunluk.txt")
    sira, gorulen = [], set()
    for d in list(temel or []) + [gunluk] + list(dosyalar or []):
        if d and d not in gorulen and os.path.isfile(d):
            gorulen.add(d)
            sira.append(d)
    for eski in os.listdir(dizin):
        if eski.startswith("teslim_") and eski.endswith(".tar"):
            os.remove(os.path.join(dizin, eski))
    gruplar, disarida, grup, boyut = [], [], [], 0
    for d in sira:
        s = os.path.getsize(d)
        if s > TEK_DOSYA_SINIRI:
            disarida.append(os.path.basename(d))
            continue
        if grup and boyut + s > PARCA_SINIRI:
            gruplar.append(grup)
            grup, boyut = [], 0
        grup.append(d)
        boyut += s
    if grup:
        gruplar.append(grup)
    parcalar = []
    for i, g in enumerate(gruplar, 1):
        yol = os.path.join(dizin, f"teslim_{no}_{i}.tar")
        with tarfile.open(yol, "w") as t:
            for d in g:
                t.add(d, arcname=os.path.basename(d))
        parcalar.append({"yol": yol, "boyut": os.path.getsize(yol), "sha256": sha256(yol),
                         "icerik": [os.path.basename(d) for d in g]})
    return {"parcalar": parcalar, "pakete_girmeyen": disarida}


def ornek_video(dizin, sure):
    """Kuru deneme: sahte modda kullanılacak örnek video (Colab'de ffmpeg ile üretilir)."""
    ornek = os.path.join(dizin, f"sahte_ornek_{sure}.mp4")
    if not os.path.isfile(ornek):
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
                        f"testsrc=size=640x368:rate=24:duration={sure}", "-f", "lavfi", "-i",
                        f"sine=frequency=440:duration={sure}", "-shortest", "-c:v", "libx264",
                        "-pix_fmt", "yuv420p", "-c:a", "aac", ornek], check=True)
    return ornek


def is_tek(senaryo, is_, dizin, durum, gunluk_yol):
    """Tek video: h3app'in kendi üretim akışı, izleme kapalı (izleme Muse'un makinesinde yapılır)."""
    from h3app import ui
    refs = [os.path.join(dizin, f"ref_{i}{os.path.splitext(r['dosya'])[1].lower() or '.png'}")
            for i, r in enumerate(senaryo.get("referanslar") or [], 1)]
    roller = [{"role": r["rol"], "name": r.get("ad", "")} for r in senaryo.get("referanslar") or []]
    son, son_gunluk = (None, None, None, None, None), ""
    for son in ui._generate_job(senaryo["prompt"], [senaryo["yontem"]], senaryo["cozunurluk"], senaryo["sure"],
                                is_["seed"], senaryo["fikir"], senaryo["brief"], refs, senaryo["stil"],
                                None, None, roller or None, False, 0, None):
        gunluk = son[0] or ""
        if gunluk != son_gunluk:
            with open(gunluk_yol, "w", encoding="utf-8") as f:
                f.write(gunluk + "\n")
            son_gunluk = gunluk
            satirlar = [s for s in gunluk.splitlines() if s.strip()]
            durum.yaz(son_satir=satirlar[-1] if satirlar else "", satir_sayisi=len(satirlar))
        else:
            durum.yaz()
    gunluk, v_sol, v_sag, dosyalar, _ = son
    secilen = v_sol or v_sag
    hatalar = [s.split("] ", 1)[-1] for s in (gunluk or "").splitlines() if "❌" in s]
    dosyalar = [d if isinstance(d, str) else getattr(d, "name", str(d)) for d in (dosyalar or [])]
    if not (secilen and os.path.isfile(secilen)):
        raise RuntimeError(hatalar[-1] if hatalar else "video üretilemedi")
    temel = [secilen] + [d for d in dosyalar if d.endswith(("_prompt.txt", "_bilgi.json"))
                         or (d.startswith(secilen[:-4]) and d.endswith(".jpg"))]
    return {"video": secilen, "dosyalar": dosyalar, "temel": temel}


def is_blok(senaryo, is_, dizin, log):
    from h3app import config, uzun
    te = uzun.prepare(senaryo["yontem"], with_refs=bool(is_.get("refs")), without_refs=not is_.get("refs"), log=log)
    ad = f"{is_['kol']}_blok{is_['blok']}_{config.METHODS[senaryo['yontem']]['file']}_seed{is_['seed']}.mp4"
    log(f"▶ [{is_['kol']}] Blok {is_['blok']} · {is_['sure']} sn · seed {is_['seed']}")
    kareler = [os.path.join(dizin, x) if x else None for x in is_.get("kareler") or []] or None
    r = uzun.render_block(senaryo["yontem"], is_["prompt"], is_["seed"], is_["sure"], senaryo["cozunurluk"],
                          senaryo["stil"], ad, [os.path.join(dizin, x) for x in is_.get("refs") or []], te, log,
                          frames=kareler)
    pfile = r["yol"][:-4] + "_prompt.txt"
    open(pfile, "w", encoding="utf-8").write(is_["prompt"].strip() + "\n")
    temel = [x for x in (r["yol"], pfile, r["temas"]) if x]
    return {"video": r["yol"], "dosyalar": [x for x in (r["kirpinti"],) if x], "temel": temel,
            "sure_sn": r["sure_sn"], "kontrol": r["kontrol"]}


def is_birlestir(senaryo, is_, dizin, log):
    from h3app import config, uzun
    mfile = config.METHODS[senaryo["yontem"]]["file"]
    dosyalar = [os.path.join(config.OUTPUT_DIR, x) for x in is_["dosyalar"]]
    log(f"🎬 [{is_['kol']}] {len(dosyalar)} blok birleştiriliyor")
    m = uzun.merge(dosyalar, os.path.join(config.OUTPUT_DIR, f"{is_['kol']}_{mfile}_birlesik.mp4"), senaryo["stil"], log)
    return {"video": m["yol"], "dosyalar": [x for x in (m["kirpinti"],) if x],
            "temel": [x for x in (m["yol"], m["temas"]) if x], "saniye": m["saniye"]}


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--dizin", default="/content/h3muse")
    a = p.parse_args(argv)
    dizin = a.dizin
    os.makedirs(dizin, exist_ok=True)
    is_ = json.load(open(os.path.join(dizin, "is.json"), encoding="utf-8"))
    no = is_.get("no", 0)
    durum = Durum(dizin, no)
    durum.yaz(tur=is_.get("tur"))
    gunluk_yol = os.path.join(dizin, "gunluk.txt")
    open(gunluk_yol, "w", encoding="utf-8").close()
    log = Gunluk(gunluk_yol, durum)
    try:
        senaryo = json.load(open(os.path.join(dizin, "senaryo.json"), encoding="utf-8"))
        if senaryo.get("sahte"):
            os.environ["H3APP_FAKE"] = "1"
            if not os.environ.get("H3APP_FAKE_VIDEO"):
                os.environ["H3APP_FAKE_VIDEO"] = ornek_video(dizin, is_.get("sure") or senaryo.get("sure") or 5)
        durum.yaz(asama="kurulum", son_satir="h3app açılıyor")
        sys.path.insert(0, h3app_ac(dizin))
        durum.yaz(asama="uretim", son_satir="iş başladı")
        if is_["tur"] == "tek":
            sonuc = is_tek(senaryo, is_, dizin, durum, gunluk_yol)
        elif is_["tur"] == "blok":
            sonuc = is_blok(senaryo, is_, dizin, log)
        elif is_["tur"] == "birlestir":
            sonuc = is_birlestir(senaryo, is_, dizin, log)
        else:
            raise RuntimeError(f"Bilinmeyen iş türü: {is_['tur']}")
        durum.yaz(asama="paketleniyor", son_satir="teslim paketi hazırlanıyor")
        paket = teslim_paketi(dizin, sonuc["dosyalar"], sonuc["temel"], no)
        v = sonuc["video"]
        durum.yaz(asama="bitti", video=os.path.basename(v), video_sha256=sha256(v), video_boyut=os.path.getsize(v),
                  ek={k: sonuc[k] for k in ("sure_sn", "kontrol", "saniye") if k in sonuc},
                  teslim=paket, son_satir="bitti")
        return 0
    except Exception as e:  # noqa: BLE001
        durum.yaz(asama="hata", hata=f"{type(e).__name__}: {e}", iz=traceback.format_exc()[-3000:])
        try:
            durum.yaz(teslim=teslim_paketi(dizin, [], [], no))   # en azından günlük
        except Exception as e2:  # noqa: BLE001
            durum.yaz(teslim_hatasi=str(e2))
        return 1


if __name__ == "__main__":
    sys.exit(main())
