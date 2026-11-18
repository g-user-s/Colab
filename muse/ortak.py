"""Muse betiklerinin ortak ayarları. Bu dosyadaki değerler bilerek sabittir; değiştirmeden önce orhan'a sorulur."""

import json
import os
import stat

# H3 Video Stüdyosu: test edilmiş sabit commit (17 Kasım 2026). Başka commit kullanılmaz.
H3_REPO = "https://github.com/orha9n/h3-video-studyosu"
H3_COMMIT = "70e0bc4244643119b35398078d3a2fe25a7a953b"

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


def anahtar_oku(yol):
    """Gemini anahtarını dosyadan okur. Anahtar hiçbir zaman ekrana yazılmaz."""
    yol = os.path.expanduser(yol)
    if not os.path.isfile(yol):
        raise SystemExit(f"Anahtar dosyası yok: {yol}")
    mod = stat.S_IMODE(os.stat(yol).st_mode)
    if mod & 0o077:
        raise SystemExit(f"Anahtar dosyasının izinleri çok açık ({oct(mod)}). Çalıştır: chmod 600 {yol}")
    anahtar = open(yol, encoding="utf-8").read().strip()
    if not anahtar:
        raise SystemExit(f"Anahtar dosyası boş: {yol}")
    return anahtar


def json_yaz(yol, veri):
    """Atomik yazma: yarım kalmış JSON dosyası oluşmaz."""
    gecici = yol + ".tmp"
    with open(gecici, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=2)
    os.replace(gecici, yol)


def json_oku(yol):
    with open(yol, encoding="utf-8") as f:
        return json.load(f)
