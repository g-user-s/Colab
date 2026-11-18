"""H3 Stüdyo'nun arka planı: ayarlar, komut çalıştırma, ayrık üretim süreci, oturum okuma.

İlke: üretim mantığı yeniden yazılmaz. Uygulama, test edilmiş betikleri (muse/senaryo.py, uzun_senaryo.py,
h3_uret.py, yama_411.py) alt süreç olarak çalıştırır; durumlarını dosyalardan (oturum.json, günlük) okur.
"""

import datetime
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import unicodedata
from pathlib import Path

from PySide6.QtCore import QObject, QProcess, QProcessEnvironment, Signal

REPO = Path(__file__).resolve().parents[2]
MUSE = REPO / "muse"
if str(MUSE) not in sys.path:
    sys.path.insert(0, str(MUSE))
import ortak  # noqa: E402

AYAR_YOLU = Path(os.environ.get("H3STUDYO_AYAR", Path.home() / ".config" / "h3studyo" / "ayarlar.json"))
VARSAYILAN = {
    "uretim_dizini": str(Path.home() / "H3Uretimler"),
    "python": sys.executable,                       # google-genai ve colab-cli kurulu python (kur.sh: venv)
    "colab": shutil.which("colab") or "colab",
    "anahtar": str(Path.home() / ".config" / "h3muse" / "gemini.key"),
    "duz_anahtarlik": False,                        # sistem anahtarlığı yoksa (ör. sunucu) Colab token'ı düz dosyada
    "gpu": "a100,g4",
    "sahte": False,                                 # yalnızca deneme/test: Gemini ve GPU'suz sahte akış
}


class Ayarlar(dict):
    def __init__(self):
        super().__init__(VARSAYILAN)
        if AYAR_YOLU.is_file():
            try:
                self.update(json.loads(AYAR_YOLU.read_text(encoding="utf-8")))
            except Exception:  # noqa: BLE001
                pass

    def kaydet(self):
        AYAR_YOLU.parent.mkdir(parents=True, exist_ok=True)
        AYAR_YOLU.write_text(json.dumps(dict(self), ensure_ascii=False, indent=2), encoding="utf-8")

    @property
    def kok(self):
        return Path(os.path.expanduser(self["uretim_dizini"]))


def ortam(ayar):
    """Alt süreçlerin ortam değişkenleri."""
    env = dict(os.environ)
    env["COLAB_BIN"] = os.path.expanduser(ayar["colab"])
    env["PYTHONUNBUFFERED"] = "1"
    if ayar.get("duz_anahtarlik"):
        env["PYTHON_KEYRING_BACKEND"] = "keyrings.alt.file.PlaintextKeyring"
    return env


def muse_komutu(ayar, betik, *args):
    return [os.path.expanduser(ayar["python"]), str(MUSE / betik), *[str(a) for a in args]]


def colab_komutu(ayar, *args):
    return [os.path.expanduser(ayar["colab"]), *[str(a) for a in args]]


class Komut(QObject):
    """Bir komutu QProcess ile çalıştırır; çıktıyı satır satır yayar. stdin'e yazılabilir (Colab girişi)."""
    satir = Signal(str)
    bitti = Signal(int, str)        # çıkış kodu, bütün çıktı

    def __init__(self, ayar, parent=None):
        super().__init__(parent)
        self.ayar = ayar
        self.p = QProcess(self)
        self.p.setProcessChannelMode(QProcess.MergedChannels)
        self.p.readyReadStandardOutput.connect(self._oku)
        self.p.finished.connect(self._bitti)
        self.p.errorOccurred.connect(self._hata)
        self._tampon, self.cikti = "", []

    def calistir(self, komut, cwd=None):
        env = QProcessEnvironment()
        for k, v in ortam(self.ayar).items():
            env.insert(k, v)
        self.p.setProcessEnvironment(env)
        self.p.setWorkingDirectory(str(cwd or REPO))
        self._tampon, self.cikti = "", []
        self.p.start(komut[0], komut[1:])

    def yaz(self, metin):
        self.p.write(metin.encode("utf-8"))

    def calisiyor(self):
        return self.p.state() != QProcess.NotRunning

    def durdur(self):
        if self.calisiyor():
            self.p.kill()

    def _oku(self):
        self._tampon += bytes(self.p.readAllStandardOutput()).decode("utf-8", "replace")
        *satirlar, self._tampon = self._tampon.split("\n")
        for s in satirlar:
            self.cikti.append(s)
            self.satir.emit(s)
        if self._tampon and not self._tampon.endswith("\n") and ("http" in self._tampon or ":" in self._tampon[-3:]):
            # soru satırı (ör. "Enter the authorization code: ") yeni satır olmadan gelir
            self.cikti.append(self._tampon)
            self.satir.emit(self._tampon)
            self._tampon = ""

    def _bitti(self, kod, _durum):
        if self._tampon:
            self.cikti.append(self._tampon)
            self.satir.emit(self._tampon)
            self._tampon = ""
        self.bitti.emit(int(kod), "\n".join(self.cikti))

    def _hata(self, hata):
        if hata == QProcess.FailedToStart:
            msg = f"Komut başlatılamadı: {self.p.program()}"
            self.cikti.append(msg)
            self.satir.emit(msg)
            self.bitti.emit(127, msg)


# ---------------- üretim klasörleri ve oturumlar ----------------

def kisa_ad(metin, uzunluk=24):
    t = unicodedata.normalize("NFKD", metin.translate(str.maketrans("ıİşŞğĞçÇöÖüÜ", "iIsSgGcCoOuU")))
    t = re.sub(r"[^A-Za-z0-9]+", "_", t.encode("ascii", "ignore").decode()).strip("_").lower()
    return (t[:uzunluk].rstrip("_") or "video")


def yeni_is_klasoru(ayar, ad):
    d = ayar.kok / f"{datetime.datetime.now():%Y%m%d_%H%M%S}_{kisa_ad(ad)}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def oturum_oku(oturum_dizini):
    yol = Path(oturum_dizini) / "oturum.json"
    try:
        return json.loads(yol.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}


def oturumlar(ayar):
    """Üretim klasöründeki bütün oturumlar, yeniden eskiye: [(oturum_dizini, oturum)]."""
    out = []
    if ayar.kok.is_dir():
        for yol in ayar.kok.glob("*/oturum*/oturum.json"):
            out.append((yol.parent, oturum_oku(yol.parent)))
    return sorted(out, key=lambda x: x[0].parent.name, reverse=True)


def surec_canli(oturum_dizini):
    """Bu oturum için başlatılan h3_uret süreci hâlâ çalışıyor mu?"""
    pid_yol = Path(oturum_dizini) / "uygulama.pid"
    try:
        pid = int(pid_yol.read_text())
        cmd = Path(f"/proc/{pid}/cmdline").read_bytes()
        durum = Path(f"/proc/{pid}/stat").read_text().split(") ")[1][0]
    except Exception:  # noqa: BLE001
        return False
    return b"h3_uret.py" in cmd and durum not in "ZX"


def acik_kalmis(oturum_dizini, o):
    """Runtime açılmış ama kapatılmamış ve onu yöneten süreç yok: CCU yanıyor olabilir."""
    return bool(o.get("ad")) and o.get("asama") != "kapatildi" and not surec_canli(oturum_dizini)


def uretim_baslat(ayar, oturum_dizini, komut, *args):
    """h3_uret.py'yi uygulamadan bağımsız (setsid) başlatır; çıktı oturum/uygulama.log'a eklenir.
    Uygulama kapansa da üretim sürer."""
    oturum_dizini = Path(oturum_dizini)
    oturum_dizini.mkdir(parents=True, exist_ok=True)
    log = open(oturum_dizini / "uygulama.log", "ab")
    p = subprocess.Popen(muse_komutu(ayar, "h3_uret.py", komut, "--oturum-dizini", oturum_dizini, *args),
                         stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, cwd=str(REPO),
                         env=ortam(ayar), start_new_session=True)
    (oturum_dizini / "uygulama.pid").write_text(str(p.pid))
    return p


def uretimi_durdur(oturum_dizini):
    """Yerel yönetici süreci durdurur (runtime'ı KAPATMAZ; onun için h3_uret.py kapat)."""
    try:
        pid = int((Path(oturum_dizini) / "uygulama.pid").read_text())
        if surec_canli(oturum_dizini):
            os.killpg(pid, signal.SIGTERM)
    except Exception:  # noqa: BLE001
        pass


def gunluk_son(oturum_dizini, satir=200):
    yol = Path(oturum_dizini) / "uygulama.log"
    try:
        return yol.read_text(encoding="utf-8", errors="replace").splitlines()[-satir:]
    except Exception:  # noqa: BLE001
        return []


ASAMA_ADI = {"yeni": "GPU isteniyor", "runtime_acik": "Dosyalar yükleniyor", "yuklendi": "Üretim başlıyor",
             "uretim": "Üretim sürüyor", "bitti": "Kapatılıyor", "kapatildi": "Bitti"}


def asama_metni(oturum_dizini, o):
    a = o.get("asama", "yeni")
    metin = ASAMA_ADI.get(a, a)
    isler = o.get("isler") or {}
    if a == "uretim" and isler:
        son = max(isler, key=int)
        metin += f" · iş {son} ({isler[son].get('tanim', {}).get('tur', '?')})"
    if a != "kapatildi" and o.get("ad") and not surec_canli(oturum_dizini):
        metin += " · ⚠️ yönetici süreç çalışmıyor (Devam gerekli)"
    return metin


def sonuc_video(oturum_dizini, o):
    yol = (o.get("video") or {}).get("yol") or (o.get("sonuc") or {}).get("secilen")
    return yol if yol and os.path.isfile(yol) else None


def senaryo_oku(yol):
    try:
        return json.loads(Path(yol).read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}


def maliyet_metni(senaryo, gpu_sirasi, esik="yuksek"):
    gpular = [g.strip() for g in gpu_sirasi.split(",") if g.strip()] or ["a100"]
    t = ortak.tahmini_maliyet(senaryo, gpular[0])
    dk = f"{t['dk'][0]}–{t['dk'][1]} dk" if t["dk"][0] != t["dk"][1] else f"~{t['dk'][0]} dk"
    if t["ccu"]:
        ccu = f"{t['ccu'][0]}–{t['ccu'][1]} CCU" if t["ccu"][0] != t["ccu"][1] else f"~{t['ccu'][0]} CCU"
    else:
        ccu = "CCU bilinmiyor (bu GPU'nun oranı ölçülmedi)"
    not_ = (" Eşik 'orta' olduğu için üst sınıra yakın olması beklenir." if esik == "orta" else "")
    return f"{gpular[0].upper()} ile tahmini {dk}, {ccu}.{not_}"
