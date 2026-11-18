#!/usr/bin/env python3
"""Adım 3–5: üretim, izleme, teslim, kapatma. Onaylanmış senaryoyu Colab GPU'sunda videoya çevirir.

Mimari: Colab yalnızca GPU işi yapar (render, birleştirme, otomatik kontrol). Gemini'ye giden her şey — videonun
izlenmesi, yeniden üretim kararı, süreklilik puanı, köprü prompt'u — BU makineden yapılır. Gemini anahtarı runtime'a
hiç gitmez (Muse'un kasası anahtarı yalnızca bu makineden çıkan isteklerde gerçek anahtarla değiştirir).
Gemini anahtarı verilirse bu betik google-genai ister: ~/workspace/tools/h3muse-venv/bin/python ile çalıştır.

Komutlar:
  uret   --senaryo S --oturum-dizini D [--gpu g4,h100,a100] [--anahtar K]
         GPU açar, dosyaları yükler; her GPU işini başlatır, yoklar, indirir, burada izletir; kusur varsa aynı
         runtime'da yeni seed ile tekrar üretir; sonunda runtime'ı kapatır, rapor yazar.
  devam  --oturum-dizini D   Muse'un makinesi yeniden başladıysa kaldığı yerden sürdürür.
  durum  --oturum-dizini D   Uzaktaki üretimin durumunu bir kez gösterir (hiçbir şeyi değiştirmez).
  kapat  --oturum-dizini D   Eldeki çıktıları indirmeyi dener ve runtime'ı kapatır.

Kurallar (kodda zorunlu):
  - Runtime, betik içinde bir hata olursa önce çıktılar indirilmeye çalışılarak kapatılır.
  - Başarılı yolda runtime ancak teslim paketi indirilip sha256 ile doğrulandıktan sonra kapatılır.
  - Gemini anahtarı runtime'a hiç yüklenmez; komut satırına ya da günlüklere girmez.
Çıkış kodları: 0 = video teslim edildi, 1 = hata (rapor.md'ye bak), 3 = GPU alınamadı (hiçbir şey açılmadı).
"""

import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ortak  # noqa: E402

BURADA = os.path.dirname(os.path.abspath(__file__))
ISARET = "@@H3@@"
UZAK = ortak.UZAK_DIZIN
UZAK_J = UZAK.lstrip("/")          # Jupyter dosya yolu: content/h3muse
ASAMALAR = ("yeni", "runtime_acik", "yuklendi", "uretim", "bitti", "kapatildi")


GECICI_HATALAR = ("Read timed out", "ReadTimeout", "ConnectTimeout", "ConnectionError", "Connection aborted",
                  "RemoteDisconnected", "502 Bad Gateway", "503 Service Unavailable", "504 Gateway")
TEKRAR_SN = int(os.environ.get("H3MUSE_TEKRAR_SN", "15"))


class Hata(Exception):
    pass


class GpuYok(Hata):
    pass


def yaz(mesaj):
    print(f"[{datetime.datetime.now():%H:%M:%S}] {mesaj}", flush=True)


class Colab:
    """`colab` sarmalayıcısını alt süreç olarak çağırır."""

    def __init__(self, yol, oturum_dizini):
        self.yol = os.path.expanduser(yol)
        self.gecici = os.path.join(oturum_dizini, "_kod")
        os.makedirs(self.gecici, exist_ok=True)

    def calistir(self, *args, sure=300):
        try:
            r = subprocess.run([self.yol, *args], capture_output=True, text=True, timeout=sure)
        except subprocess.TimeoutExpired:
            return 124, f"(colab {' '.join(args[:1])} {sure} sn içinde bitmedi)"
        except FileNotFoundError:
            raise Hata(f"colab sarmalayıcısı bulunamadı: {self.yol}")
        return r.returncode, (r.stdout or "") + (r.stderr or "")

    def kod(self, ad, kod, sure=120, deneme=3):
        """Runtime'da kısa bir kod çalıştırır, ISARET satırındaki JSON'u döner. Geçici ağ hatalarında
        (ör. CLI'nın 10 sn'lik okuma zaman aşımı) bekleyip tekrar dener; buradaki kodlar tekrar güvenlidir."""
        dosya = os.path.join(self.gecici, f"k_{int(time.time() * 1000)}.py")
        with open(dosya, "w", encoding="utf-8") as f:
            f.write(kod)
        try:
            for i in range(1, deneme + 1):
                rc, out = self.calistir("exec", "-s", ad, "-f", dosya, "--timeout", str(sure), sure=sure + 120)
                if "appears to be lost" in out:
                    raise Hata("RUNTIME_KAYIP: runtime artık yok (Colab kapatmış olabilir).")
                for satir in out.splitlines():
                    if satir.startswith(ISARET):
                        return json.loads(satir[len(ISARET):])
                if i < deneme and (rc == 124 or any(x in out for x in GECICI_HATALAR)):
                    yaz(f"Runtime'a geçici olarak ulaşılamadı ({i}/{deneme}); {TEKRAR_SN} sn sonra tekrar.")
                    time.sleep(TEKRAR_SN)
                    continue
                break
        finally:
            os.remove(dosya)
        raise Hata(f"Runtime'dan yanıt alınamadı (rc={rc}): {out.strip()[-600:]}")

    def yukle(self, ad, yerel, uzak, deneme=3):
        for i in range(1, deneme + 1):
            rc, out = self.calistir("upload", "-s", ad, yerel, uzak, sure=600)
            if rc == 0:
                return
            if i < deneme:
                yaz(f"Yükleme denemesi {i}/{deneme} başarısız ({os.path.basename(uzak)}); {TEKRAR_SN} sn sonra tekrar.")
                time.sleep(TEKRAR_SN)
        raise Hata(f"Yükleme başarısız ({uzak}): {out.strip()[-300:]}")

    def bakiye(self):
        rc, out = self.calistir("usage", sure=120)
        b = re.search(r"Current balance:\s*([\d.]+)", out)
        n = re.search(r"Active assignments:\s*(\d+)", out)
        return {"bakiye": float(b.group(1)) if b else None, "aktif": int(n.group(1)) if n else None,
                "ham": out.strip()[-400:]}


# ---------- Runtime'da çalışan küçük kodlar ----------

KOD_GPU = f"""
import json, subprocess
try:
    o = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
                       capture_output=True, text=True).stdout.strip().splitlines()[0]
    ad, mib = [x.strip() for x in o.split(",")]
    r = {{"gpu": ad, "mib": int(float(mib))}}
except Exception as e:
    r = {{"gpu": None, "hata": str(e)}}
import os; os.makedirs("{UZAK}", exist_ok=True)
print("{ISARET}" + json.dumps(r))
"""

KOD_BASLAT = """
import json, os, subprocess, sys
d = "@UZAK@"
no = @NO@
s = {}
try:
    s = json.load(open(d + "/durum.json"))
except Exception:
    pass
pid = s.get("pid")
canli = False
if pid:
    try:
        canli = open(f"/proc/{pid}/stat").read().split(") ")[1][0] not in "ZX"
    except Exception:
        canli = False
if s.get("is_no") == no and (canli or s.get("asama") in ("bitti", "hata")):
    print("@ISARET@" + json.dumps({"pid": pid, "zaten": True}))
elif canli:
    print("@ISARET@" + json.dumps({"hata": f"başka bir iş çalışıyor (iş {s.get('is_no')}, pid {pid})"}))
else:
    if os.path.exists(d + "/durum.json"):
        os.remove(d + "/durum.json")
    p = subprocess.Popen([sys.executable, d + "/runtime_runner.py", "--dizin", d], cwd=d,
                         stdout=open(d + "/runner_cikti.txt", "ab"), stderr=subprocess.STDOUT,
                         start_new_session=True)
    print("@ISARET@" + json.dumps({"pid": p.pid, "zaten": False}))
""".replace("@UZAK@", UZAK).replace("@ISARET@", ISARET)


KOD_DURUM = f"""
import json, os
d = "{UZAK}"
try:
    s = json.load(open(d + "/durum.json", encoding="utf-8"))
except Exception as e:
    s = {{"asama": "okunamadi", "hata": str(e)}}
pid = s.get("pid")
canli = False
if pid:
    try:
        canli = open(f"/proc/{{pid}}/stat").read().split(") ")[1][0] not in "ZX"
    except Exception:
        canli = False
s["canli"] = canli
s.pop("iz", None)
try:
    s["runner_son"] = open(d + "/runner_cikti.txt", encoding="utf-8", errors="replace").read()[-800:]
except Exception:
    pass
print("{ISARET}" + json.dumps(s, ensure_ascii=False))
"""


# ---------- Oturum ----------

class Oturum:
    def __init__(self, dizin):
        self.dizin = os.path.abspath(os.path.expanduser(dizin))
        self.yol = os.path.join(self.dizin, "oturum.json")
        self.v = ortak.json_oku(self.yol) if os.path.isfile(self.yol) else {}

    def kaydet(self, **alanlar):
        self.v.update(alanlar)
        self.v["guncelleme"] = datetime.datetime.now().isoformat(timespec="seconds")
        ortak.json_yaz(self.yol, self.v)

    @property
    def asama(self):
        return self.v.get("asama", "yeni")

    def gecti(self, asama):
        return ASAMALAR.index(self.asama) >= ASAMALAR.index(asama)

    @property
    def cikti(self):
        d = os.path.join(self.dizin, "cikti")
        os.makedirs(d, exist_ok=True)
        return d


def _sha256(yol):
    import hashlib
    h = hashlib.sha256()
    with open(yol, "rb") as f:
        for parca in iter(lambda: f.read(1 << 20), b""):
            h.update(parca)
    return h.hexdigest()


def runtime_ac(c, o, gpular, deneme=3, bekle=None):
    bekle = int(os.environ.get("H3MUSE_BEKLE_SN", 30)) if bekle is None else bekle
    for gpu in gpular:
        for i in range(1, deneme + 1):
            ad = f"h3m{datetime.datetime.now():%m%d%H%M%S}"
            yaz(f"GPU isteniyor: {gpu.upper()} (deneme {i}/{deneme})")
            gpu_arg = [] if gpu == "cpu" else ["--gpu", gpu]
            rc, out = c.calistir("new", "-s", ad, *gpu_arg, sure=900)
            if rc == 0 and "READY" in out:
                o.kaydet(asama="runtime_acik", ad=ad, gpu=gpu, acilis=time.time())
                yaz(f"Runtime açıldı: {ad} ({gpu.upper()})")
                return ad
            kisa = out.strip()[-300:]
            if "411" in out or "Length Required" in out:
                raise Hata("411 Length Required: CLI yaması eksik. Çalıştır: python muse/yama_411.py, sonra tekrar dene.")
            if "rejected accelerator" in out or "entitlement" in out:
                yaz(f"{gpu.upper()} bu hesapta kullanılamıyor; sıradaki GPU'ya geçiliyor.")
                break
            yaz(f"{gpu.upper()} alınamadı: {kisa}")
            if i < deneme:
                time.sleep(bekle)
    raise GpuYok("İstenen GPU'ların hiçbiri alınamadı: " + ", ".join(g.upper() for g in gpular))


def dosya_yukle(c, o, yerel, uzak):
    c.yukle(o.v["ad"], yerel, f"{UZAK_J}/{uzak}")
    yaz(f"Yüklendi: {uzak}")


def yukle(c, o, senaryo_yol):
    ad = o.v["ad"]
    senaryo = ortak.json_oku(senaryo_yol)
    g = c.kod(ad, KOD_GPU)
    if senaryo.get("sahte"):
        yaz(f"Kuru deneme (sahte senaryo): GPU denetimi atlandı ({g.get('gpu') or 'GPU yok'}).")
    elif not g.get("gpu"):
        raise Hata(f"Runtime'da GPU görünmüyor: {g}")
    else:
        yaz(f"GPU doğrulandı: {g['gpu']} ({g['mib']} MiB)")
        if g["mib"] < 40000:
            raise Hata(f"GPU belleği yetersiz ({g['mib']} MiB < 40 GB). H3 bu kartta çalışmaz.")
    o.kaydet(gpu_adi=g.get("gpu"), gpu_mib=g.get("mib"))
    dosya_yukle(c, o, os.path.join(BURADA, "runtime_runner.py"), "runtime_runner.py")
    dosya_yukle(c, o, ortak.h3app_paketle(os.path.join(o.dizin, "h3app.tar")), "h3app.tar")
    dosya_yukle(c, o, senaryo_yol, "senaryo.json")
    for i, r in enumerate(senaryo.get("referanslar") or [], 1):
        dosya_yukle(c, o, r["dosya"], f"ref_{i}{os.path.splitext(r['dosya'])[1].lower() or '.png'}")
    o.kaydet(asama="yuklendi", uretim_baslangic=o.v.get("uretim_baslangic") or time.time())


# ---------- GPU işleri ----------

def yokla(c, o, no):
    ad = o.v["ad"]
    bitis = o.v["uretim_baslangic"] + o.v["azami_dk"] * 60
    son, hata_sayisi = None, 0
    while True:
        try:
            s = c.kod(ad, KOD_DURUM, sure=90)
            hata_sayisi = 0
        except Hata as e:
            if str(e).startswith("RUNTIME_KAYIP"):
                raise
            hata_sayisi += 1
            yaz(f"Durum okunamadı ({hata_sayisi}/10): {str(e)[:200]}")
            if hata_sayisi >= 10:
                raise Hata("Runtime'a art arda 10 kez ulaşılamadı.")
            time.sleep(o.v["aralik"])
            continue
        if s.get("is_no") == no:
            satir = f"iş {no} · {s.get('asama')} · {s.get('son_satir', '')}"
            if satir != son:
                yaz(satir)
                son = satir
            if s.get("asama") in ("bitti", "hata"):
                return s
            if not s.get("canli"):
                raise Hata(f"Runner süreci durmuş ama 'bitti' yazmamış. Son çıktı: {s.get('runner_son', '')[-400:]}")
        if time.time() > bitis:
            raise Hata(f"Üretim {o.v['azami_dk']} dakikayı aştı.")
        time.sleep(o.v["aralik"])


def parcalari_indir(c, o, paket):
    toplam = 0
    for i, parca in enumerate(paket.get("parcalar") or [], 1):
        ad_tar = os.path.basename(parca["yol"])
        yerel = os.path.join(o.dizin, ad_tar)
        for deneme in range(1, 4):
            rc, out = c.calistir("download", "-s", o.v["ad"], f"{UZAK_J}/{ad_tar}", yerel, sure=900)
            if rc == 0 and os.path.isfile(yerel) and _sha256(yerel) == parca["sha256"]:
                break
            yaz(f"{ad_tar} doğrulanamadı (deneme {deneme}/3): {out.strip()[-200:]}")
        else:
            raise Hata(f"{ad_tar} 3 denemede doğru inmedi (sha256 uyuşmuyor).")
        with tarfile.open(yerel) as t:
            t.extractall(o.cikti, filter="data")
        os.remove(yerel)
        toplam += parca["boyut"]
    if paket.get("pakete_girmeyen"):
        yaz(f"47 MB'tan büyük, runtime'da kalan dosyalar: {', '.join(paket['pakete_girmeyen'])}")
    return toplam


def is_calistir(c, o, tanim):
    """Bir GPU işini runtime'da yürütür (daha önce indirildiyse önbellekten döner). {'video','video_ad','ek'}"""
    no = int(tanim["no"])
    isler = o.v.setdefault("isler", {})
    kayit = isler.get(str(no))
    if kayit and kayit["asama"] == "indirildi":
        return kayit["sonuc"]
    if not kayit:
        yerel = os.path.join(o.dizin, "_kod", f"is_{no}.json")
        ortak.json_yaz(yerel, tanim)
        c.yukle(o.v["ad"], yerel, f"{UZAK_J}/is.json")
        r = c.kod(o.v["ad"], KOD_BASLAT.replace("@NO@", str(no)))
        if r.get("hata"):
            raise Hata(f"İş {no} başlatılamadı: {r['hata']}")
        kayit = isler[str(no)] = {"tanim": {k: v for k, v in tanim.items() if k != "prompt"}, "asama": "baslatildi"}
        o.kaydet(asama="uretim", isler=isler)
        yaz(f"İş {no} ({tanim['tur']}) runtime'da {'zaten çalışıyor' if r.get('zaten') else 'başlatıldı'}.")
    s = yokla(c, o, no)
    if s.get("teslim"):
        parcalari_indir(c, o, s["teslim"])
    if s.get("asama") != "bitti":
        o.kaydet(son_hata_durumu=s)
        raise Hata(f"İş {no} ({tanim['tur']}) başarısız: {s.get('hata', 'bilinmeyen hata')}")
    video = os.path.join(o.cikti, s["video"])
    if not os.path.isfile(video) or _sha256(video) != s.get("video_sha256"):
        raise Hata(f"İş {no}: video inmedi ya da sha256 uyuşmuyor ({s['video']}).")
    kayit.update(asama="indirildi", sonuc={"video": video, "video_ad": s["video"], "ek": s.get("ek") or {}})
    o.kaydet(isler=isler)
    yaz(f"İş {no} indi ve doğrulandı: {s['video']}")
    return kayit["sonuc"]


# ---------- Gemini (bu makinede) ----------

class Gemini:
    """İzleme ve köprü prompt'u: istekler bu makineden çıkar. Sonuçlar oturuma yazılır; 'devam' tekrar sormaz."""

    def __init__(self, o, senaryo):
        self.o, self.senaryo = o, senaryo
        self.anahtar = ortak.anahtar_oku(o.v["anahtar"]) if o.v.get("anahtar") else None
        from senaryo import h3_yukle
        self.config, self.pw = h3_yukle()
        from h3app import review
        self.review = review
        self.test = json.loads(os.environ.get("H3MUSE_TEST_INCELEME", "null"))   # yalnızca testler
        self.test_s = json.loads(os.environ.get("H3MUSE_TEST_SUREKLILIK", "null"))
        self.aktif = bool(self.anahtar) and (not senaryo.get("sahte") or self.test is not None)
        if self.anahtar and self.test is None:
            try:
                import google.genai  # noqa: F401
            except ImportError:
                raise Hata("google-genai yok. Bu betiği ~/workspace/tools/h3muse-venv/bin/python ile çalıştır.")

    def engel(self, inceleme):
        """Yeniden üretim gerekir mi? Eşik 'yuksek' (varsayılan): yalnızca yüksek önemde kusur; 'orta': orta da."""
        if not inceleme:
            return False
        onemler = ("high", "medium") if self.o.v.get("yeniden_esik") == "orta" else ("high",)
        return any(d.get("severity") in onemler for d in inceleme.get("defects") or [])

    def _onbellek(self, ad):
        return self.o.v.setdefault(ad, {})

    def izle(self, video, prompt, refs, roles):
        if not self.aktif:
            return None
        c = self._onbellek("incelemeler")
        k = os.path.basename(video)
        if k not in c:
            yaz(f"🔍 Gemini {k} videosunu izliyor (bu makineden)…")
            if self.test is not None:
                r = self.test[len(c)] if len(c) < len(self.test) else None
            else:
                r = self.review.review_video(video, prompt, self.anahtar, refs, roles, log=yaz)
            c[k] = r
            self.o.kaydet()
            yaz("   " + self.review.summary(r))
        return c[k]

    def sureklilik(self, video, kesmeler):
        if not self.aktif:
            return None
        c = self._onbellek("sureklilik")
        k = os.path.basename(video)
        if k not in c:
            yaz(f"🎞️ Gemini {k} sürekliliğini izliyor (bu makineden)…")
            if self.test_s is not None:
                r = self.test_s[len(c)] if len(c) < len(self.test_s) else None
            else:
                r = self.review.continuity_review(video, kesmeler, self.senaryo.get("hikaye") or {}, self.anahtar,
                                                  log=yaz)
            c[k] = r
            self.o.kaydet()
        return c[k]

    def kopru_prompt(self, k, istek, sure, gorseller, roller):
        c = self._onbellek("kopru_promptlari")
        if k not in c:
            if not self.anahtar or self.senaryo.get("sahte"):
                return None
            yaz(f"🔗 {k}: köprü prompt'u yazılıyor (bu makineden)…")
            prompt, sorun = self.pw.rewrite(istek, sure, self.anahtar, self.config.GEMINI_MODEL, gorseller, log=yaz,
                                            style=self.senaryo["stil"], roles=roller)
            if sorun:
                yaz(f"   ⚠️ Köprü prompt'unda uyarı: {' | '.join(sorun)}")
            c[k] = prompt
            self.o.kaydet()
        return c[k]


def son_kare(video, hedef):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-sseof", "-0.2", "-i", video, "-frames:v", "1", hedef], check=True)
    return hedef


def blok_kesmeleri(config, bloklar):
    kesmeler, t = [], 0.0
    for b in bloklar[:-1]:
        t += config.frames_for(b["sure"]) / 24
        kesmeler.append(round(t, 2))
    return kesmeler


# ---------- Akışlar ----------

def akis_tek(c, o, senaryo, gm):
    rv = gm.review
    refs = [r["dosya"] for r in senaryo.get("referanslar") or []]
    roller = [{"role": r["rol"], "name": r.get("ad", "")} for r in senaryo.get("referanslar") or []] or None
    tekrar = int(senaryo.get("yeniden_uretim", gm.config.REVIEW_RETRIES)) if gm.aktif else 0
    adaylar = []
    for k in range(tekrar + 1):
        seed = int(senaryo["seed"]) + 1000 * k
        r = is_calistir(c, o, {"no": k + 1, "tur": "tek", "seed": seed})
        inc = gm.izle(r["video"], senaryo["prompt"], refs, roller)
        adaylar.append({"video": r["video"], "seed": seed, "inceleme": inc})
        if not gm.engel(inc):
            break
        if k < tekrar:
            yaz(f"🔁 Yüksek önemde kusur; aynı runtime'da yeni seed ({int(senaryo['seed']) + 1000 * (k + 1)}) ile "
                f"yeniden üretiliyor ({k + 1}/{tekrar}).")
    en_iyi = min(adaylar, key=lambda a: rv.score(a["inceleme"])) if gm.aktif else adaylar[-1]
    secim = (f"⭐ Seçilen: {os.path.basename(en_iyi['video'])} (seed {en_iyi['seed']}, {len(adaylar)} aday) — izleme: "
             f"{rv.short(en_iyi['inceleme']) if gm.aktif else 'yapılmadı (anahtar verilmedi ya da kuru deneme)'}")
    if gm.aktif and gm.engel(en_iyi["inceleme"]):
        secim += " · ⚠️ bütün adaylarda yüksek önemde kusur kaldı"
    yaz(secim)
    o.kaydet(sonuc={"secilen": en_iyi["video"], "secim": secim,
                    "adaylar": [{"video": os.path.basename(a["video"]), "seed": a["seed"],
                                 "izleme": rv.short(a["inceleme"]) if gm.aktif else "-"} for a in adaylar]})


def akis_uzun(c, o, senaryo, gm):
    rv, config = gm.review, gm.config
    tekrar = int(senaryo.get("yeniden_uretim", 0)) if gm.aktif else 0
    mfile = config.METHODS[senaryo["yontem"]]["file"]
    no = [0]

    def sonraki():
        no[0] += 1
        return no[0]

    referanslar = senaryo.get("referanslar") or []
    ref_rt = [f"ref_{i}{os.path.splitext(r['dosya'])[1].lower() or '.png'}" for i, r in enumerate(referanslar, 1)]
    ref_yerel = [r["dosya"] for r in referanslar]
    ref_rol = [{"role": r["rol"], "name": r.get("ad", "")} for r in referanslar]
    ozet = {"deney": bool(senaryo.get("deney")), "kollar": {}}
    kopru_kayit = o.v.setdefault("kopru_yuklenen", {})
    for kol, k in senaryo["kollar"].items():
        yaz(f"━━ Kol: {kol} ({'görsel referanslı, Ref2VA' if k['ref'] else 'yalnızca metin çapası'}) ━━")
        secilen_ad, secilen_yerel, kol_ozet = [], [], []
        for b in k["bloklar"]:
            n = b["blok"]
            prompt = b["prompt"]
            b_rt = list(ref_rt) if k["ref"] else []
            b_yerel = list(ref_yerel) if k["ref"] else []
            b_rol = list(ref_rol) if k["ref"] else None
            if senaryo.get("kopru") and k["ref"] and secilen_yerel and len(b_rt) < config.MAX_REF_IMAGES:
                ad = f"kopru_{kol}_{n}.png"
                kare = son_kare(secilen_yerel[-1], os.path.join(o.cikti, ad))
                if not kopru_kayit.get(ad):
                    dosya_yukle(c, o, kare, ad)
                    kopru_kayit[ad] = True
                    o.kaydet(kopru_yuklenen=kopru_kayit)
                b_rt.append(ad)
                b_yerel.append(kare)
                b_rol = (b_rol or []) + [{"role": "arka_plan", "name": "final frame of the previous block"}]
                yeni = gm.kopru_prompt(ad, b["istek"], b["sure"], b_yerel, b_rol)
                if yeni:
                    prompt = yeni
                else:
                    yaz(f"🔗 {ad}: köprü karesi eklendi; prompt yeniden yazılmadı (kuru deneme ya da anahtar yok).")
            adaylar = []
            for d in range(tekrar + 1):
                seed = int(senaryo["seed"]) + (n - 1) + 1000 * d
                r = is_calistir(c, o, {"no": sonraki(), "tur": "blok", "kol": kol, "blok": n, "sure": b["sure"],
                                       "prompt": prompt, "seed": seed, "refs": b_rt})
                inc = gm.izle(r["video"], prompt, b_yerel, b_rol)
                adaylar.append({"video": r["video"], "ad": r["video_ad"], "seed": seed, "inceleme": inc})
                if not gm.engel(inc):
                    break
                if d < tekrar:
                    yaz(f"🔁 [{kol}] Blok {n}: yüksek önemde kusur; aynı runtime'da yeni seed ile yeniden üretiliyor")
            en_iyi = min(adaylar, key=lambda a: rv.score(a["inceleme"])) if gm.aktif else adaylar[-1]
            secilen_ad.append(en_iyi["ad"])
            secilen_yerel.append(en_iyi["video"])
            kol_ozet.append({"blok": n, "secilen": en_iyi["ad"], "seed": en_iyi["seed"],
                             "inceleme": rv.short(en_iyi["inceleme"]) if gm.aktif else "atlandı",
                             "adaylar": [{"dosya": a["ad"], "seed": a["seed"], "inceleme": a["inceleme"]}
                                         for a in adaylar]})
        m = is_calistir(c, o, {"no": sonraki(), "tur": "birlestir", "kol": kol, "dosyalar": secilen_ad})
        kesmeler = blok_kesmeleri(config, k["bloklar"])
        surek = gm.sureklilik(m["video"], kesmeler)
        if surek:
            yaz(f"   Süreklilik [{kol}]: " + ", ".join(f"{x} {surek.get(x)}" for x in rv.SURECLILIK_PUANLARI)
                + f" · ortalama {surek.get('ortalama')}")
        ozet["kollar"][kol] = {"birlesik": m["video_ad"], "saniye": (m.get("ek") or {}).get("saniye"),
                               "bloklar": kol_ozet, "sureklilik": surek, "blok_kesmeleri": kesmeler}
    if ozet["deney"]:
        ozet["karsilastirma"] = {kk: (v["sureklilik"] or {}).get("ortalama") for kk, v in ozet["kollar"].items()}
        yaz(f"⚖️ Deney sonucu (süreklilik ortalaması): {ozet['karsilastirma']}")
    ortak.json_yaz(os.path.join(o.cikti, "uzun_sonuc.json"), ozet)
    ana = "ref" if "ref" in ozet["kollar"] else next(iter(ozet["kollar"]))
    o.kaydet(sonuc={"secilen": os.path.join(o.cikti, ozet["kollar"][ana]["birlesik"]), "uzun_ozet": ozet,
                    "secim": f"Kol {ana}: {ozet['kollar'][ana]['birlesik']}"})


def video_dogrula(o):
    yol = (o.v.get("sonuc") or {}).get("secilen")
    if not yol or not os.path.isfile(yol):
        raise Hata(f"Seçilen video yok: {yol}")
    sonuc = {"yol": yol, "boyut": os.path.getsize(yol)}
    if shutil.which("ffprobe"):
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type,width,height",
                            "-of", "json", yol], capture_output=True, text=True)
        bilgi = json.loads(r.stdout or "{}")
        akislar = [a.get("codec_type") for a in bilgi.get("streams", [])]
        sonuc.update(sure=float(bilgi.get("format", {}).get("duration", 0)), akislar=akislar,
                     boyutlar=[(a["width"], a["height"]) for a in bilgi.get("streams", []) if a.get("width")])
        if "video" not in akislar or "audio" not in akislar or sonuc["sure"] <= 0:
            raise Hata(f"ffprobe videoyu geçersiz buldu: {sonuc}")
    yaz(f"Video doğrulandı: {os.path.basename(yol)} · {sonuc.get('sure', '?')} sn · {sonuc['boyut']} bayt")
    o.kaydet(video=sonuc)
    return sonuc


def kapat(c, o):
    ad = o.v.get("ad")
    if not ad or o.asama == "kapatildi":
        return
    for i in range(1, 4):
        rc, out = c.calistir("stop", "-s", ad, sure=300)
        if rc == 0 and ("terminated" in out or "not found" in out):
            break
        yaz(f"Kapatma denemesi {i}/3 başarısız: {out.strip()[-200:]}")
        time.sleep(10)
    rc, out = c.calistir("sessions", sure=120)
    acik = ad in out
    son = c.bakiye()
    o.kaydet(asama="kapatildi" if not acik else o.asama, ccu_sonra=son, sunucudaki_oturumlar=out.strip()[-400:],
             kapanis=time.time() if not acik else None)
    if acik:
        raise Hata(f"Runtime {ad} hâlâ sunucuda görünüyor. Elle kapat: colab stop -s {ad}")
    yaz(f"Runtime kapatıldı. Aktif atama: {son.get('aktif')} · bakiye: {son.get('bakiye')} CCU")


def rapor(o, hata=None):
    s = o.v.get("sonuc") or {}
    once, sonra = (o.v.get("ccu_once") or {}).get("bakiye"), (o.v.get("ccu_sonra") or {}).get("bakiye")
    harcanan = f"{once - sonra:.2f}" if once is not None and sonra is not None else "?"
    dk = (o.v["kapanis"] - o.v["acilis"]) / 60 if o.v.get("kapanis") and o.v.get("acilis") else None
    oran = ortak.ORANLAR.get(o.v.get("gpu"))
    tahmin = (f"{dk:.1f} dk açık kaldı × {oran} CCU/saat ≈ {dk / 60 * oran:.3f} CCU" if dk is not None and oran
              else f"{dk:.1f} dk açık kaldı (bu GPU'nun oranı bilinmiyor; 'colab usage' Usage rate ile ölç)"
              if dk is not None else "süre bilinmiyor")
    senaryo = ortak.json_oku(o.v["senaryo"]) if o.v.get("senaryo") and os.path.isfile(o.v["senaryo"]) else {}
    satirlar = [
        "# H3 üretim raporu", "",
        f"- Sonuç: {'✅ teslim edildi' if not hata else '❌ ' + str(hata)}",
        f"- Fikir: {senaryo.get('fikir', '?')}",
        f"- Tür: {senaryo.get('tur', 'tek')} · yöntem / süre / stil: {senaryo.get('yontem')} / {senaryo.get('sure')} sn / "
        f"{senaryo.get('stil')}",
        f"- GPU: {o.v.get('gpu', '?')} · {o.v.get('gpu_adi') or '—'}",
        f"- Prompt modelleri: {senaryo.get('modeller') or '-'}",
        f"- Video: {(o.v.get('video') or {}).get('yol', '-')}",
        f"- Seçim ve Gemini izlemesi (bu makineden): {s.get('secim') or '-'}",
        f"- GPU işleri: {len(o.v.get('isler') or {})} · Gemini izlemesi: {len(o.v.get('incelemeler') or {})} video",
        f"- CCU: {once} → {sonra} (bakiye farkı {harcanan}; tahmin: {tahmin}); "
        f"aktif atama: {(o.v.get('ccu_sonra') or {}).get('aktif')}",
        f"- Runtime: {o.v.get('ad', '-')} · aşama: {o.asama}",
    ]
    for a in s.get("adaylar") or []:
        satirlar.append(f"  - aday {a['video']} · seed {a['seed']} · izleme: {a['izleme']}")
    uzun = s.get("uzun_ozet") or {}
    for kol, v in (uzun.get("kollar") or {}).items():
        sk = v.get("sureklilik") or {}
        puan = ", ".join(f"{k} {sk.get(k)}" for k in ("kimlik", "kiyafet", "mekan", "ses", "hikaye")) if sk else "izlenmedi"
        satirlar.append(f"- Kol `{kol}`: {v.get('birlesik')} · süreklilik: {puan} · ortalama {sk.get('ortalama', '-')}")
        for b in v.get("bloklar") or []:
            satirlar.append(f"  - blok {b['blok']}: {b['secilen']} · izleme: {b['inceleme']} · {len(b['adaylar'])} aday")
        if sk.get("sorunlar"):
            satirlar += [f"  - ⚠️ {x.get('zaman_s')} sn [{x.get('alan')}] {x.get('aciklama')}" for x in sk["sorunlar"][:6]]
    if uzun.get("karsilastirma"):
        satirlar.append(f"- ⚖️ Deney (süreklilik ortalaması): {uzun['karsilastirma']}")
    hd = o.v.get("son_hata_durumu") or {}
    if hd.get("hata"):
        satirlar.append(f"- Runtime hatası: {hd['hata']}")
    yol = os.path.join(o.dizin, "rapor.md")
    with open(yol, "w", encoding="utf-8") as f:
        f.write("\n".join(satirlar) + "\n")
    print("\n".join(satirlar))
    print(f"\nRapor: {yol}")


def akis(c, o, a):
    """Kaldığı yerden sonuna kadar yürütür. Hata olursa runtime'ı kapatır (her iş zaten indirilmiş olur)."""
    try:
        senaryo = ortak.json_oku(o.v["senaryo"])
        gm = Gemini(o, senaryo)
        if not o.gecti("runtime_acik"):
            o.kaydet(ccu_once=c.bakiye())
            runtime_ac(c, o, o.v["gpular"])
        if not o.gecti("yuklendi"):
            yukle(c, o, o.v["senaryo"])
        if not o.gecti("bitti"):
            (akis_uzun if senaryo.get("tur") == "uzun" else akis_tek)(c, o, senaryo, gm)
            o.kaydet(asama="bitti")
        video_dogrula(o)
        kapat(c, o)
        rapor(o)
        return 0
    except GpuYok as e:
        o.kaydet(ccu_sonra=c.bakiye())
        rapor(o, e)
        return 3
    except Hata as e:
        yaz(f"❌ {e}")
        if o.v.get("ad") and o.asama != "kapatildi" and not str(e).startswith("RUNTIME_KAYIP"):
            try:
                kapat(c, o)
            except Exception as e3:  # noqa: BLE001
                yaz(f"❌ KAPATILAMADI: {e3}. Hemen elle kapat: colab stop -s {o.v.get('ad')}")
        rapor(o, e)
        return 1


def main(argv=None):
    p = argparse.ArgumentParser(description="H3 üretimi: Colab GPU'sunda senaryodan videoya")
    alt = p.add_subparsers(dest="komut", required=True)
    for ad in ("uret", "devam", "durum", "kapat"):
        q = alt.add_parser(ad)
        q.add_argument("--oturum-dizini", required=True)
        q.add_argument("--colab", default=os.environ.get("COLAB_BIN", "~/workspace/tools/colab"))
        if ad == "uret":
            q.add_argument("--senaryo", required=True)
            q.add_argument("--gpu", default="g4,h100,a100", help="Denenecek GPU sırası (virgülle)")
            q.add_argument("--anahtar", default="~/.config/h3muse/gemini.key",
                           help="Gemini anahtarı (bu makinedeki izleme için). İzlemesiz: --anahtar ''")
            q.add_argument("--azami-dakika", type=int, help="Varsayılan: senaryoya göre hesaplanır")
            q.add_argument("--aralik", type=int, default=30, help="Yoklama aralığı (sn)")
            q.add_argument("--yeniden-esik", choices=("yuksek", "orta"), default="yuksek",
                           help="Hangi önemdeki kusur yeniden üretimi tetikler (orta: daha temiz, ~2 kat GPU süresi)")
            q.add_argument("--sorunlu-kabul", action="store_true",
                           help="Denetim sorunlu senaryoyu yine de üret (yalnızca orhan onay verdiyse)")
    a = p.parse_args(argv)
    o = Oturum(a.oturum_dizini)
    c = Colab(a.colab, o.dizin)

    if a.komut == "uret":
        if o.v and o.asama != "kapatildi":
            raise SystemExit(f"Bu oturum dizininde bitmemiş bir oturum var (aşama: {o.asama}). "
                             "'devam' ya da 'kapat' kullan, veya yeni bir dizin seç.")
        if o.v:
            raise SystemExit("Bu oturum dizini daha önce kullanılmış. Yeni bir dizin seç.")
        senaryo = ortak.json_oku(a.senaryo)
        if senaryo.get("durum") != "hazir" and not a.sorunlu_kabul:
            raise SystemExit("Senaryo 'hazir' değil (denetim sorunları var). Önce senaryoyu düzelt; "
                             "orhan sorunlara rağmen onay verdiyse --sorunlu-kabul ekle.")
        if senaryo.get("h3app_surum") != ortak.h3app_surum():
            raise SystemExit(f"Senaryo farklı bir h3app sürümüyle yazılmış ({senaryo.get('h3app_surum')} ≠ "
                             f"{ortak.h3app_surum()}); senaryoyu yeniden yazdır.")
        gpular = [g.strip().lower() for g in a.gpu.split(",") if g.strip()]
        if "cpu" in gpular and not senaryo.get("sahte"):
            raise SystemExit("CPU runtime yalnızca kuru deneme (--sahte senaryo) içindir; gerçek üretim GPU ister.")
        if a.anahtar:
            ortak.anahtar_oku(a.anahtar)   # GPU açmadan önce: anahtar yoksa hemen dur
        os.makedirs(o.dizin, exist_ok=True)
        senaryo_kopya = os.path.join(o.dizin, "senaryo.json")
        if os.path.abspath(a.senaryo) != senaryo_kopya:
            shutil.copyfile(a.senaryo, senaryo_kopya)
        o.kaydet(asama="yeni", senaryo=senaryo_kopya, gpular=gpular, anahtar=a.anahtar or None,
                 yeniden_esik=a.yeniden_esik,
                 azami_dk=a.azami_dakika or ortak.azami_dakika(senaryo), aralik=a.aralik,
                 baslangic=datetime.datetime.now().isoformat(timespec="seconds"))
        return akis(c, o, a)
    if not o.v:
        raise SystemExit(f"Oturum bulunamadı: {o.yol}")
    if a.komut == "devam":
        if o.asama == "kapatildi":
            print("Bu oturum zaten kapatılmış.")
            rapor(o)
            return 0
        yaz(f"Kaldığı yerden devam: aşama {o.asama}")
        return akis(c, o, a)
    if a.komut == "durum":
        if not o.v.get("ad") or o.asama == "kapatildi":
            print(json.dumps({k: o.v.get(k) for k in ("asama", "ad", "gpu", "isler")}, ensure_ascii=False, indent=2))
            return 0
        print(json.dumps(c.kod(o.v["ad"], KOD_DURUM, sure=90), ensure_ascii=False, indent=2))
        return 0
    if a.komut == "kapat":
        if o.v.get("ad") and o.asama != "kapatildi":
            kapat(c, o)
        rapor(o, None if o.v.get("video") else "elle kapatıldı")
        return 0


if __name__ == "__main__":
    sys.exit(main())
