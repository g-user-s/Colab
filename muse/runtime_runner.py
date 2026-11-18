#!/usr/bin/env python3
"""Colab runtime'ında arka planda çalışır. Muse bunu elle çalıştırmaz; h3_uret.py yükler ve başlatır.

Girdi (DIZIN içinde): senaryo.json, gemini.key (isteğe bağlı), ref_1.png ... (isteğe bağlı)
Çıktı (DIZIN içinde): durum.json (sürekli güncellenir), gunluk.txt, teslim.tar (bitince)

Tek başına çalışır: yalnızca standart kütüphane + h3app (h3_uret.py'nin yüklediği h3app.tar'dan açılır).
Gemini anahtarı dosyadan okunur, okunduktan hemen sonra dosya silinir ve hiçbir yere yazılmaz.
"""

import argparse
import datetime
import hashlib
import json
import os
import subprocess
import sys
import tarfile
import traceback

PARCA_SINIRI = 40 * 1024 * 1024      # Colab dosya aktarımı istek başına ~50 MB
TEK_DOSYA_SINIRI = 47 * 1024 * 1024


def simdi():
    return datetime.datetime.now().isoformat(timespec="seconds")


class Durum:
    def __init__(self, dizin, anahtar=None):
        self.yol = os.path.join(dizin, "durum.json")
        self.anahtar = anahtar
        self.veri = {"asama": "basliyor", "baslangic": simdi(), "pid": os.getpid()}

    def temizle(self, metin):
        if self.anahtar and isinstance(metin, str):
            return metin.replace(self.anahtar, "***")
        return metin

    def yaz(self, **alanlar):
        self.veri.update({k: self.temizle(v) for k, v in alanlar.items()})
        self.veri["guncelleme"] = simdi()
        gecici = self.yol + ".tmp"
        with open(gecici, "w", encoding="utf-8") as f:
            json.dump(self.veri, f, ensure_ascii=False, indent=2)
        os.replace(gecici, self.yol)


def sha256(yol):
    h = hashlib.sha256()
    with open(yol, "rb") as f:
        for parca in iter(lambda: f.read(1 << 20), b""):
            h.update(parca)
    return h.hexdigest()


def h3app_ac(dizin, durum):
    """Yüklenen h3app.tar'ı DIZIN/repo altına açar (her seferinde temiz). Repo klasörünü döner."""
    repo = os.path.join(dizin, "repo")
    paket = os.path.join(dizin, "h3app.tar")
    if not os.path.isfile(paket):
        raise RuntimeError("h3app.tar yüklenmemiş.")
    durum.yaz(asama="kurulum", son_satir="h3app açılıyor")
    hedef = os.path.join(repo, "h3app")
    if os.path.isdir(hedef):
        import shutil
        shutil.rmtree(hedef)
    os.makedirs(repo, exist_ok=True)
    with tarfile.open(paket) as t:
        t.extractall(repo, filter="data")
    return repo


def teslim_paketi(dizin, dosyalar, temel):
    """Çıktıları en fazla ~40 MB'lık tar parçalarına koyar (Colab dosya aktarımı istek başına ~50 MB).
    Önce temel dosyalar (seçilen video, prompt'lar, bilgi, kontrol görselleri, günlük) girer; her parça sha256
    ile doğrulanır. 47 MB'tan büyük tek dosyalar pakete girmez, listede kalır."""
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
        yol = os.path.join(dizin, f"teslim_{i}.tar")
        with tarfile.open(yol, "w") as t:
            for d in g:
                t.add(d, arcname=os.path.basename(d))
        parcalar.append({"yol": yol, "boyut": os.path.getsize(yol), "sha256": sha256(yol),
                         "icerik": [os.path.basename(d) for d in g]})
    return {"parcalar": parcalar, "pakete_girmeyen": disarida}


class Gunluk:
    """Uzun video için günlük: her satır dosyaya ve durum.json'a yazılır."""

    def __init__(self, yol, durum):
        self.yol, self.durum, self.satirlar = yol, durum, []

    def __call__(self, mesaj):
        satir = self.durum.temizle(f"[{datetime.datetime.now():%H:%M:%S}] {mesaj}")
        self.satirlar.append(satir)
        with open(self.yol, "a", encoding="utf-8") as f:
            f.write(satir + "\n")
        self.durum.yaz(son_satir=satir, satir_sayisi=len(self.satirlar))


def tek_video(senaryo, dizin, anahtar, durum, gunluk_yol):
    """15 sn'ye kadar tek çekim: h3app'in kendi üretim akışı (_generate_job)."""
    from h3app import config, prompt_writer, ui
    refs = []
    for i, r in enumerate(senaryo.get("referanslar") or [], 1):
        refs.append(os.path.join(dizin, f"ref_{i}{os.path.splitext(r['dosya'])[1].lower() or '.png'}"))
    roller = [{"role": r["rol"], "name": r.get("ad", "")} for r in senaryo.get("referanslar") or []]
    prompt_writer.used_models.clear()
    prompt_writer.used_models.update(senaryo.get("modeller") or {})
    son, son_gunluk = (None, None, None, None, None), ""
    for son in ui._generate_job(senaryo["prompt"], [senaryo["yontem"]], senaryo["cozunurluk"], senaryo["sure"],
                                senaryo["seed"], senaryo["fikir"], senaryo["brief"], refs, senaryo["stil"],
                                None, None, roller or None, True, config.REVIEW_RETRIES, anahtar):
        gunluk = durum.temizle(son[0] or "")
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
    secim_satiri = [s.split("] ", 1)[-1] for s in (gunluk or "").splitlines() if "⭐ Seçilen:" in s]
    dosyalar = [d if isinstance(d, str) else getattr(d, "name", str(d)) for d in (dosyalar or [])]
    if not (secilen and os.path.isfile(secilen)):
        raise RuntimeError(hatalar[-1] if hatalar else "video üretilemedi")
    temel = [secilen] + [d for d in dosyalar if d.endswith(("_prompt.txt", "_bilgi.json"))
                         or (d.startswith(secilen[:-4]) and d.endswith(".jpg"))]
    return {"secilen": secilen, "dosyalar": dosyalar, "temel": temel,
            "ozet": {"secim": secim_satiri[-1] if secim_satiri else None}}


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--dizin", default="/content/h3muse")
    p.add_argument("--repo", help="h3app'i içeren klasör (verilmezse DIZIN/h3app.tar açılır)")
    a = p.parse_args(argv)
    dizin = a.dizin
    os.makedirs(dizin, exist_ok=True)

    anahtar = None
    anahtar_yol = os.path.join(dizin, "gemini.key")
    if os.path.isfile(anahtar_yol):
        anahtar = open(anahtar_yol, encoding="utf-8").read().strip() or None
        os.remove(anahtar_yol)
    durum = Durum(dizin, anahtar)
    durum.yaz()
    gunluk_yol = os.path.join(dizin, "gunluk.txt")
    open(gunluk_yol, "w", encoding="utf-8").close()

    try:
        senaryo_yol = os.path.join(dizin, "senaryo.json")
        senaryo = json.load(open(senaryo_yol, encoding="utf-8"))
        senaryo["_yol"] = senaryo_yol
        if senaryo.get("sahte"):
            os.environ["H3APP_FAKE"] = "1"
            if not os.environ.get("H3APP_FAKE_VIDEO"):   # Colab'de kuru deneme: örnek videoyu kendimiz üretiriz
                sure = max(b["sure"] for k in (senaryo.get("kollar") or {}).values() for b in k["bloklar"]) \
                    if senaryo.get("tur") == "uzun" else senaryo["sure"]
                ornek = os.path.join(dizin, "sahte_ornek.mp4")
                subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
                                f"testsrc=size=640x368:rate=24:duration={sure}", "-f", "lavfi", "-i",
                                f"sine=frequency=440:duration={sure}", "-shortest", "-c:v", "libx264",
                                "-pix_fmt", "yuv420p", "-c:a", "aac", ornek], check=True)
                os.environ["H3APP_FAKE_VIDEO"] = ornek
        repo = a.repo or h3app_ac(dizin, durum)
        sys.path.insert(0, repo)
        durum.yaz(asama="kurulum", son_satir="h3app yükleniyor")
        if not anahtar and not senaryo.get("sahte"):
            durum.yaz(uyari="Gemini anahtarı yok: otomatik izleme yapılmayacak")
        durum.yaz(asama="uretim", son_satir="üretim başladı")
        if senaryo.get("tur") == "uzun":
            from h3app import uzun
            refs = [os.path.join(dizin, f"ref_{i}{os.path.splitext(r['dosya'])[1].lower() or '.png'}")
                    for i, r in enumerate(senaryo.get("referanslar") or [], 1)]
            roller = [{"role": r["rol"], "name": r.get("ad", "")} for r in senaryo.get("referanslar") or []]
            sonuc = uzun.generate({k: v["bloklar"] for k, v in senaryo["kollar"].items()}, senaryo["yontem"],
                                  senaryo["cozunurluk"], senaryo["seed"], senaryo["stil"], refs=refs, roles=roller,
                                  bible=senaryo.get("hikaye"), api_key=anahtar,
                                  retries=senaryo.get("yeniden_uretim", 0), bridge=senaryo.get("kopru"),
                                  experiment=senaryo.get("deney"), log=Gunluk(gunluk_yol, durum))
        else:
            sonuc = tek_video(senaryo, dizin, anahtar, durum, gunluk_yol)
        secilen = sonuc["secilen"]
        durum.yaz(asama="paketleniyor", son_satir="teslim paketi hazırlanıyor")
        paket = teslim_paketi(dizin, sonuc["dosyalar"], sonuc["temel"])
        durum.yaz(asama="bitti", video=os.path.basename(secilen), video_sha256=sha256(secilen),
                  video_boyut=os.path.getsize(secilen), secim=sonuc["ozet"].get("secim"),
                  uzun_ozet=sonuc["ozet"] if senaryo.get("tur") == "uzun" else None,
                  teslim=paket, son_satir="bitti")
        return 0
    except Exception as e:  # noqa: BLE001
        durum.yaz(asama="hata", hata=f"{type(e).__name__}: {e}", iz=traceback.format_exc()[-3000:])
        try:   # hata durumunda da elde ne varsa paketlenir
            cikti_dizin = os.path.join(os.environ.get("H3APP_WORK_DIR", "/content"), "h3app_videolar")
            eldeki = []
            if os.path.isdir(cikti_dizin):
                eldeki = [os.path.join(cikti_dizin, d) for d in sorted(os.listdir(cikti_dizin))]
            durum.yaz(teslim=teslim_paketi(dizin, eldeki, []))
        except Exception as e2:  # noqa: BLE001
            durum.yaz(teslim_hatasi=str(e2))
        return 1


if __name__ == "__main__":
    sys.exit(main())
