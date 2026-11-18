#!/usr/bin/env python3
"""Adım 3–5: üretim, teslim, kapatma. Onaylanmış senaryo.json'u Colab GPU'sunda videoya çevirir.

Komutlar:
  uret   --senaryo S --oturum-dizini D [--gpu g4,h100,a100] [--anahtar K]
         GPU açar, dosyaları yükler, üretimi arka planda başlatır, bitene kadar yoklar,
         çıktıyı indirip doğrular, runtime'ı kapatır, CCU raporu yazar.
  devam  --oturum-dizini D   Muse'un makinesi yeniden başladıysa kaldığı yerden sürdürür.
  durum  --oturum-dizini D   Uzaktaki üretimin durumunu bir kez gösterir (hiçbir şeyi değiştirmez).
  kapat  --oturum-dizini D   Eldeki çıktıları indirmeyi dener ve runtime'ı kapatır.

Kurallar (kodda zorunlu):
  - Runtime, betik içinde bir hata olursa önce çıktılar indirilmeye çalışılarak kapatılır.
  - Başarılı yolda runtime ancak teslim paketi indirilip sha256 ile doğrulandıktan sonra kapatılır.
  - Gemini anahtarı yalnızca dosya olarak yüklenir; komut satırına ya da günlüklere girmez.
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
ASAMALAR = ("yeni", "runtime_acik", "yuklendi", "baslatildi", "uzakta_bitti", "indirildi", "kapatildi")


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

    def kod(self, ad, kod, sure=120):
        """Runtime'da kısa bir kod çalıştırır, ISARET satırındaki JSON'u döner."""
        dosya = os.path.join(self.gecici, f"k_{int(time.time() * 1000)}.py")
        with open(dosya, "w", encoding="utf-8") as f:
            f.write(kod)
        try:
            rc, out = self.calistir("exec", "-s", ad, "-f", dosya, "--timeout", str(sure), sure=sure + 120)
        finally:
            os.remove(dosya)
        if "appears to be lost" in out:
            raise Hata("RUNTIME_KAYIP: runtime artık yok (Colab kapatmış olabilir).")
        for satir in out.splitlines():
            if satir.startswith(ISARET):
                return json.loads(satir[len(ISARET):])
        raise Hata(f"Runtime'dan yanıt alınamadı (rc={rc}): {out.strip()[-600:]}")

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

KOD_BASLAT = f"""
import json, os, subprocess, sys
d = "{UZAK}"
eski = None
try:
    eski = json.load(open(d + "/durum.json")).get("pid")
except Exception:
    pass
if eski and os.path.exists(f"/proc/{{eski}}"):
    print("{ISARET}" + json.dumps({{"pid": eski, "zaten": True}}))
else:
    p = subprocess.Popen([sys.executable, d + "/runtime_runner.py", "--dizin", d], cwd=d,
                         stdout=open(d + "/runner_cikti.txt", "ab"), stderr=subprocess.STDOUT,
                         start_new_session=True)
    print("{ISARET}" + json.dumps({{"pid": p.pid, "zaten": False}}))
"""

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


def yukle(c, o, senaryo_yol, anahtar_yol):
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
    yuklenecek = [(os.path.join(BURADA, "runtime_runner.py"), "runtime_runner.py"),
                  (ortak.h3app_paketle(os.path.join(o.dizin, "h3app.tar")), "h3app.tar"),
                  (senaryo_yol, "senaryo.json")]
    for i, r in enumerate(senaryo.get("referanslar") or [], 1):
        uzanti = os.path.splitext(r["dosya"])[1].lower() or ".png"
        yuklenecek.append((r["dosya"], f"ref_{i}{uzanti}"))
    if anahtar_yol:
        ortak.anahtar_oku(anahtar_yol)   # izin ve boşluk denetimi; değer kullanılmaz
        yuklenecek.append((os.path.expanduser(anahtar_yol), "gemini.key"))
    for yerel, uzak in yuklenecek:
        rc, out = c.calistir("upload", "-s", ad, yerel, f"{UZAK_J}/{uzak}", sure=600)
        if rc != 0:
            raise Hata(f"Yükleme başarısız ({uzak}): {out.strip()[-300:]}")
        yaz(f"Yüklendi: {uzak}")
    o.kaydet(asama="yuklendi")


def baslat(c, o):
    r = c.kod(o.v["ad"], KOD_BASLAT)
    o.kaydet(asama="baslatildi", pid=r["pid"], uretim_baslangic=o.v.get("uretim_baslangic") or time.time())
    yaz(f"Üretim arka planda {'zaten çalışıyor' if r.get('zaten') else 'başlatıldı'} (pid {r['pid']}).")


def yokla(c, o, azami_dk, aralik):
    ad = o.v["ad"]
    bitis = o.v["uretim_baslangic"] + azami_dk * 60
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
            time.sleep(aralik)
            continue
        satir = f"{s.get('asama')} · {s.get('son_satir', '')}"
        if satir != son:
            yaz(satir)
            son = satir
        if s.get("asama") in ("bitti", "hata"):
            o.kaydet(asama="uzakta_bitti", uzak_durum=s)
            return s
        if not s.get("canli") and s.get("asama") != "okunamadi":
            o.kaydet(uzak_durum=s)
            raise Hata(f"Runner süreci durmuş ama 'bitti' yazmamış. Son çıktı: {s.get('runner_son', '')[-400:]}")
        if time.time() > bitis:
            o.kaydet(uzak_durum=s)
            raise Hata(f"Üretim {azami_dk} dakikayı aştı.")
        time.sleep(aralik)


def indir(c, o):
    """Teslim parçalarını indirir, her birini sha256 ile doğrular ve açar. Başarılıysa True."""
    ad = o.v["ad"]
    s = o.v.get("uzak_durum") or {}
    paket = s.get("teslim")
    if not paket:
        try:
            s = c.kod(ad, KOD_DURUM, sure=90)
            paket = s.get("teslim")
            o.kaydet(uzak_durum=s)
        except Hata:
            paket = None
    cikti = os.path.join(o.dizin, "cikti")
    os.makedirs(cikti, exist_ok=True)
    if not paket or not paket.get("parcalar"):
        for dosya in ("gunluk.txt", "runner_cikti.txt"):   # en azından günlükler
            c.calistir("download", "-s", ad, f"{UZAK_J}/{dosya}", os.path.join(cikti, dosya), sure=300)
        yaz("Teslim paketi yok; yalnızca günlükler indirilmeye çalışıldı.")
        return False
    toplam = 0
    for no, parca in enumerate(paket["parcalar"], 1):
        ad_tar = os.path.basename(parca["yol"])
        yerel = os.path.join(o.dizin, ad_tar)
        for i in range(1, 4):
            rc, out = c.calistir("download", "-s", ad, f"{UZAK_J}/{ad_tar}", yerel, sure=900)
            if rc == 0 and os.path.isfile(yerel) and _sha256(yerel) == parca["sha256"]:
                break
            yaz(f"{ad_tar} doğrulanamadı (deneme {i}/3): {out.strip()[-200:]}")
        else:
            raise Hata(f"{ad_tar} 3 denemede doğru inmedi (sha256 uyuşmuyor).")
        with tarfile.open(yerel) as t:
            t.extractall(cikti, filter="data")
        os.remove(yerel)
        toplam += parca["boyut"]
        yaz(f"Parça {no}/{len(paket['parcalar'])} indi ve doğrulandı: {len(parca['icerik'])} dosya.")
    yaz(f"Teslim tamam: {toplam} bayt, {sum(len(p['icerik']) for p in paket['parcalar'])} dosya.")
    if paket.get("pakete_girmeyen"):
        yaz(f"47 MB'tan büyük, runtime'da kalan dosyalar: {', '.join(paket['pakete_girmeyen'])}")
    o.kaydet(asama="indirildi", cikti_dizini=cikti)
    return True


def _sha256(yol):
    import hashlib
    h = hashlib.sha256()
    with open(yol, "rb") as f:
        for parca in iter(lambda: f.read(1 << 20), b""):
            h.update(parca)
    return h.hexdigest()


def video_dogrula(o):
    s = o.v.get("uzak_durum") or {}
    if s.get("asama") != "bitti" or not s.get("video"):
        return None
    yol = os.path.join(o.dizin, "cikti", s["video"])
    if not os.path.isfile(yol):
        raise Hata(f"Video pakette yok: {s['video']}")
    if _sha256(yol) != s.get("video_sha256"):
        raise Hata("Videonun sha256'sı runtime'daki ile uyuşmuyor.")
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
    s = o.v.get("uzak_durum") or {}
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
        f"- Seçim ve Gemini izlemesi: {s.get('secim') or '-'}",
        f"- CCU: {once} → {sonra} (bakiye farkı {harcanan}; tahmin: {tahmin}); "
        f"aktif atama: {(o.v.get('ccu_sonra') or {}).get('aktif')}",
        f"- Runtime: {o.v.get('ad', '-')} · aşama: {o.asama}",
    ]
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
    if s.get("hata"):
        satirlar.append(f"- Runtime hatası: {s['hata']}")
    if s.get("uyari"):
        satirlar.append(f"- Uyarı: {s['uyari']}")
    yol = os.path.join(o.dizin, "rapor.md")
    with open(yol, "w", encoding="utf-8") as f:
        f.write("\n".join(satirlar) + "\n")
    print("\n".join(satirlar))
    print(f"\nRapor: {yol}")


def akis(c, o, a):
    """Kaldığı aşamadan sonuna kadar yürütür. Hata olursa çıktıları indirip runtime'ı kapatır."""
    try:
        if not o.gecti("runtime_acik"):
            o.kaydet(ccu_once=c.bakiye())
            runtime_ac(c, o, o.v["gpular"])
        if not o.gecti("yuklendi"):
            yukle(c, o, o.v["senaryo"], o.v.get("anahtar"))
        if not o.gecti("baslatildi"):
            baslat(c, o)
        if not o.gecti("uzakta_bitti"):
            yokla(c, o, o.v["azami_dk"], o.v["aralik"])
        if not o.gecti("indirildi"):
            if not indir(c, o):
                raise Hata("Teslim paketi oluşmadı.")
        s = o.v.get("uzak_durum") or {}
        if s.get("asama") != "bitti":
            raise Hata(f"Üretim başarısız: {s.get('hata', 'bilinmeyen hata')}")
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
            if not o.gecti("indirildi"):
                try:
                    indir(c, o)
                except Exception as e2:  # noqa: BLE001
                    yaz(f"Kısmi indirme de başarısız: {e2}")
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
                           help="Gemini anahtar dosyası; izleme için gerekli. Boş bırakmak için --anahtar ''")
            q.add_argument("--azami-dakika", type=int, help="Varsayılan yönteme göre: pika 45, turbo 30, h3 90")
            q.add_argument("--aralik", type=int, default=30, help="Yoklama aralığı (sn)")
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
        os.makedirs(o.dizin, exist_ok=True)
        senaryo_kopya = os.path.join(o.dizin, "senaryo.json")
        if os.path.abspath(a.senaryo) != senaryo_kopya:
            shutil.copyfile(a.senaryo, senaryo_kopya)
        o.kaydet(asama="yeni", senaryo=senaryo_kopya, gpular=gpular, anahtar=a.anahtar or None,
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
            print(json.dumps(o.v, ensure_ascii=False, indent=2))
            return 0
        print(json.dumps(c.kod(o.v["ad"], KOD_DURUM, sure=90), ensure_ascii=False, indent=2))
        return 0
    if a.komut == "kapat":
        if o.v.get("ad") and o.asama != "kapatildi":
            if not o.gecti("indirildi"):
                try:
                    indir(c, o)
                except Exception as e:  # noqa: BLE001
                    yaz(f"İndirme başarısız: {e}")
            kapat(c, o)
        rapor(o, None if o.v.get("video") else "elle kapatıldı")
        return 0


if __name__ == "__main__":
    sys.exit(main())
