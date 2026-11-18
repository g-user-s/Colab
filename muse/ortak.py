"""Muse betiklerinin ortak ayarları. Bu dosyadaki değerler bilerek sabittir; değiştirmeden önce orhan'a sorulur."""

import hashlib
import io
import json
import os
import stat
import tarfile

# H3 Video Stüdyosu bu deponun h3/ klasöründe (orha9n/h3-video-studyosu@70e0bc4'ten git subtree ile alındı).
# Runtime'a GitHub'dan klonlanmaz; h3/h3app klasörü paketlenip yüklenir.
H3_DIZIN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "h3")


def _h3app_dosyalari(h3_dizin=None):
    kok = os.path.join(h3_dizin or H3_DIZIN, "h3app")
    if not os.path.isfile(os.path.join(kok, "__init__.py")):
        raise SystemExit(f"h3app bulunamadı: {kok}")
    out = []
    for d, alt, dosyalar in os.walk(kok):
        alt[:] = sorted(x for x in alt if x != "__pycache__")
        out += [os.path.join(d, f) for f in sorted(dosyalar) if f.endswith(".py")]
    return kok, out


def h3app_surum(h3_dizin=None):
    """h3app kaynak kodunun içerik özeti (12 hane). Senaryo ile üretim aynı kodla yapılsın diye kaydedilir."""
    kok, dosyalar = _h3app_dosyalari(h3_dizin)
    h = hashlib.sha256()
    for f in dosyalar:
        h.update(os.path.relpath(f, kok).encode() + b"\0" + open(f, "rb").read() + b"\0")
    return h.hexdigest()[:12]


def h3app_paketle(hedef, h3_dizin=None):
    """h3app'i runtime'a yüklenecek bir tar dosyasına koyar (yalnızca .py dosyaları)."""
    kok, dosyalar = _h3app_dosyalari(h3_dizin)
    with tarfile.open(hedef, "w") as t:
        for f in dosyalar:
            t.add(f, arcname=os.path.join("h3app", os.path.relpath(f, kok)))
    return hedef

# Runtime üzerindeki çalışma klasörü (Jupyter yolu "content/h3muse" ile aynı yer)
UZAK_DIZIN = "/content/h3muse"

STILLER = ("real", "anime", "pixar", "watercolour")
YONTEMLER = ("pika", "turbo", "h3")
COZUNURLUKLER = {   # kısa ad → h3app.config.RESOLUTIONS anahtarı
    "yatay": "16:9 yatay · 1344×768",
    "dikey": "9:16 dikey · 768×1344",
    "kare": "1:1 kare · 1024×1024",
}
ROLLER = ("karakter", "arka_plan", "nesne")

# Yöntem başına üretimin süreceği en uzun süre (dakika). Aşılırsa çıktılar indirilir ve runtime kapatılır.
AZAMI_DAKIKA = {"pika": 45, "turbo": 30, "h3": 90}
# Ölçülmüş saatlik CCU oranları (17 Kasım 2026). `colab usage` bakiyeyi 2 ondalıkla verdiği için kısa işlerin
# maliyeti farktan görünmez; rapor ayrıca süre × oran tahminini yazar. H100 henüz ölçülmedi.
ORANLAR = {"g4": 9.92, "a100": 6.73, "cpu": 0.08}
BLOK_DAKIKA = {"pika": 14, "turbo": 8, "h3": 30}   # bir 15 sn'lik bloğun render + izleme payı


def azami_dakika(senaryo):
    """Senaryoya göre üretimin en uzun süresi (dk): tek videoda sabit, uzun videoda blok ve kol sayısına göre."""
    if senaryo.get("tur") != "uzun":
        return AZAMI_DAKIKA[senaryo["yontem"]]
    kollar = senaryo["kollar"]
    blok = sum(len(k["bloklar"]) for k in kollar.values())
    return 20 + blok * (int(senaryo.get("yeniden_uretim", 0)) + 1) * BLOK_DAKIKA[senaryo["yontem"]]


ANAHTAR_DEGISKENLERI = ("GEMINI_API_KEY", "GEMINI", "GOOGLE_API_KEY")


def anahtar_oku(yol):
    """Gemini anahtarını okur: önce dosyadan (chmod 600), dosya yoksa ortam değişkeninden
    (GEMINI_API_KEY, GEMINI, GOOGLE_API_KEY — ör. ajanın güvenli kasası anahtarı böyle veriyorsa).
    Anahtar hiçbir zaman ekrana yazılmaz."""
    yol = os.path.expanduser(yol or "")
    if yol and os.path.isfile(yol):
        mod = stat.S_IMODE(os.stat(yol).st_mode)
        if mod & 0o077:
            raise SystemExit(f"Anahtar dosyasının izinleri çok açık ({oct(mod)}). Çalıştır: chmod 600 {yol}")
        anahtar = open(yol, encoding="utf-8").read().strip()
        if not anahtar:
            raise SystemExit(f"Anahtar dosyası boş: {yol}")
        return anahtar
    for ad in ANAHTAR_DEGISKENLERI:
        if os.environ.get(ad, "").strip():
            return os.environ[ad].strip()
    raise SystemExit(f"❌ Gemini anahtarı yok: ne {yol or '(dosya verilmedi)'} dosyası ne de "
                     f"{' / '.join(ANAHTAR_DEGISKENLERI)} ortam değişkeni var.\n"
                     "   Bu adım Gemini ister. Anahtarı orhan güvenli giriş kartıyla verir. Kasan anahtarı ortam "
                     "değişkeni olarak veriyorsa adı yukarıdakilerden biri olmalı; dosya olarak veriyorsa "
                     "rehber 2.5'teki yola yaz. Anahtarı başka yerden arama.")


def anahtar_dosyasi_hazirla(yol, gecici_dizin):
    """Runtime'a yüklenecek anahtar dosyasının yolu. Anahtar ortam değişkenindeyse geçici bir 600 dosyası yazılır;
    (yol, gecici_mi) döner. Çağıran, gecici dosyayı yüklemeden hemen sonra siler."""
    yol = os.path.expanduser(yol or "")
    anahtar = anahtar_oku(yol)
    if yol and os.path.isfile(yol):
        return yol, False
    hedef = os.path.join(gecici_dizin, ".gemini.key.gecici")
    fd = os.open(hedef, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(anahtar + "\n")
    return hedef, True


def json_yaz(yol, veri):
    """Atomik yazma: yarım kalmış JSON dosyası oluşmaz."""
    gecici = yol + ".tmp"
    with open(gecici, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=2)
    os.replace(gecici, yol)


def json_oku(yol):
    with open(yol, encoding="utf-8") as f:
        return json.load(f)
