#!/usr/bin/env python3
"""Colab runtime'ında arka planda çalışır. Muse bunu elle çalıştırmaz; h3_uret.py yükler ve başlatır.

Girdi (DIZIN içinde): senaryo.json, gemini.key (isteğe bağlı), ref_1.png ... (isteğe bağlı)
Çıktı (DIZIN içinde): durum.json (sürekli güncellenir), gunluk.txt, teslim.tar (bitince)

Tek başına çalışır: yalnızca standart kütüphane + h3app (sabit commit'ten klonlanır).
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

H3_REPO = "https://github.com/orha9n/h3-video-studyosu"
TESLIM_SINIRI = 45 * 1024 * 1024   # Colab dosya aktarımı istek başına ~50 MB


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


def repo_hazirla(repo_dizin, commit, durum):
    """h3 deposunu sabit commit'e getirir (varsa yeniden kullanır)."""
    if not os.path.isdir(os.path.join(repo_dizin, ".git")):
        durum.yaz(asama="kurulum", son_satir="h3 deposu klonlanıyor")
        os.makedirs(repo_dizin, exist_ok=True)
        for komut in (["git", "init", "-q"], ["git", "remote", "add", "origin", H3_REPO]):
            subprocess.run(komut, cwd=repo_dizin, check=True)
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_dizin, capture_output=True, text=True).stdout.strip()
    if head != commit:
        subprocess.run(["git", "fetch", "-q", "--depth", "1", "origin", commit], cwd=repo_dizin, check=True)
        subprocess.run(["git", "checkout", "-q", "--detach", commit], cwd=repo_dizin, check=True)
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_dizin, capture_output=True, text=True).stdout.strip()
    if head != commit:
        raise RuntimeError(f"h3 deposu yanlış commit'te: {head}")


def teslim_paketi(dizin, dosyalar, secilen):
    """Çıktıları tek bir tar dosyasında toplar (sha256 ile doğrulanabilir tek indirme).
    Sınırı aşarsa yalnızca temel dosyalar konur, diğerleri listede kalır."""
    gunluk = os.path.join(dizin, "gunluk.txt")
    tum = [d for d in dosyalar if os.path.isfile(d)] + [gunluk]
    temel_uzanti = ("_prompt.txt", "_bilgi.json")
    temel = [d for d in tum if d == secilen or d.endswith(temel_uzanti) or d == gunluk
             or (secilen and d.startswith(secilen[:-4]) and d.endswith(".jpg"))]
    secim = tum if sum(os.path.getsize(d) for d in tum) <= TESLIM_SINIRI else temel
    tar_yol = os.path.join(dizin, "teslim.tar")
    with tarfile.open(tar_yol, "w") as t:
        for d in secim:
            t.add(d, arcname=os.path.basename(d))
    disarida = [d for d in tum if d not in secim]
    return {"yol": tar_yol, "boyut": os.path.getsize(tar_yol), "sha256": sha256(tar_yol),
            "icerik": [os.path.basename(d) for d in secim], "pakete_girmeyen": disarida}


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--dizin", default="/content/h3muse")
    p.add_argument("--repo", help="h3 deposu klasörü (varsayılan: DIZIN/repo)")
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
    son_gunluk = ""

    try:
        senaryo = json.load(open(os.path.join(dizin, "senaryo.json"), encoding="utf-8"))
        if senaryo.get("sahte"):
            os.environ["H3APP_FAKE"] = "1"
            if not os.environ.get("H3APP_FAKE_VIDEO"):   # Colab'de kuru deneme: örnek videoyu kendimiz üretiriz
                ornek = os.path.join(dizin, "sahte_ornek.mp4")
                subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
                                f"testsrc=size=640x368:rate=24:duration={senaryo['sure']}", "-f", "lavfi", "-i",
                                f"sine=frequency=440:duration={senaryo['sure']}", "-shortest", "-c:v", "libx264",
                                "-pix_fmt", "yuv420p", "-c:a", "aac", ornek], check=True)
                os.environ["H3APP_FAKE_VIDEO"] = ornek
        repo = a.repo or os.path.join(dizin, "repo")
        if not os.environ.get("H3APP_MUSE_REPO_HAZIR"):
            repo_hazirla(repo, senaryo["h3_commit"], durum)
        sys.path.insert(0, repo)
        durum.yaz(asama="kurulum", son_satir="h3app yükleniyor")
        from h3app import config, prompt_writer, ui

        refs = []
        for i, r in enumerate(senaryo.get("referanslar") or [], 1):
            uzanti = os.path.splitext(r["dosya"])[1].lower() or ".png"
            refs.append(os.path.join(dizin, f"ref_{i}{uzanti}"))
        roller = [{"role": r["rol"], "name": r.get("ad", "")} for r in senaryo.get("referanslar") or []]
        prompt_writer.used_models.clear()
        prompt_writer.used_models.update(senaryo.get("modeller") or {})
        if not anahtar and not senaryo.get("sahte"):
            durum.yaz(uyari="Gemini anahtarı yok: otomatik izleme yapılmayacak")

        durum.yaz(asama="uretim", son_satir="üretim başladı")
        son = (None, None, None, None, None)
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
        durum.yaz(asama="paketleniyor", son_satir="teslim paketi hazırlanıyor")
        paket = teslim_paketi(dizin, dosyalar, secilen)
        durum.yaz(asama="bitti", video=os.path.basename(secilen), video_sha256=sha256(secilen),
                  video_boyut=os.path.getsize(secilen), secim=secim_satiri[-1] if secim_satiri else None,
                  teslim=paket, son_satir="bitti")
        return 0
    except Exception as e:  # noqa: BLE001
        durum.yaz(asama="hata", hata=f"{type(e).__name__}: {e}", iz=traceback.format_exc()[-3000:])
        try:   # hata durumunda da elde ne varsa paketlenir
            cikti_dizin = os.path.join(os.environ.get("H3APP_WORK_DIR", "/content"), "h3app_videolar")
            eldeki = []
            if os.path.isdir(cikti_dizin):
                eldeki = [os.path.join(cikti_dizin, d) for d in sorted(os.listdir(cikti_dizin))]
            if not os.path.isfile(gunluk_yol):
                open(gunluk_yol, "w", encoding="utf-8").write(son_gunluk + "\n")
            durum.yaz(teslim=teslim_paketi(dizin, eldeki, None))
        except Exception as e2:  # noqa: BLE001
            durum.yaz(teslim_hatasi=str(e2))
        return 1


if __name__ == "__main__":
    sys.exit(main())
