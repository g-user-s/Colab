"""Muse betiklerinin sahte modda uçtan uca testleri. GPU, Colab ve Gemini gerekmez.

Gerekenler: ffmpeg/ffprobe ve h3-video-studyosu'nun test bağımlılıkları (requirements-dev.txt).
H3_DIZIN ortam değişkeni sabit commit'teki h3 klonunu göstermelidir.
"""

import json
import os
import shutil
import subprocess
import sys

import pytest

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MUSE = os.path.join(KOK, "muse")
SAHTE = os.path.join(KOK, "tests", "sahte_colab.py")
H3 = os.environ.get("H3_DIZIN", os.path.expanduser("~/orha9n/h3-video-studyosu"))
sys.path.insert(0, MUSE)

import h3_uret  # noqa: E402
import ortak  # noqa: E402

pytestmark = pytest.mark.skipif(not os.path.isdir(os.path.join(H3, "h3app")), reason="H3_DIZIN yok")


def calistir(*args, env=None):
    return subprocess.run([sys.executable, *args], capture_output=True, text=True, env=env, cwd=KOK)


@pytest.fixture
def ortam(tmp_path):
    video = tmp_path / "ornek.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc=size=320x184:rate=24:duration=5",
                    "-f", "lavfi", "-i", "sine=frequency=440:duration=5", "-shortest", "-c:v", "libx264",
                    "-c:a", "aac", str(video)], check=True)
    kok = tmp_path / "runtime"
    (kok / "content" / "h3muse").mkdir(parents=True)
    os.symlink(H3, kok / "content" / "h3muse" / "repo")
    colab = tmp_path / "colab"
    colab.write_text(f"#!/bin/sh\nexec {sys.executable} {SAHTE} \"$@\"\n")
    colab.chmod(0o755)
    anahtar = tmp_path / "gemini.key"
    anahtar.write_text("SAHTE-ANAHTAR-123\n")
    anahtar.chmod(0o600)
    env = dict(os.environ, SAHTE_KOK=str(kok), SAHTE_PYTHON=sys.executable, H3APP_FAKE_VIDEO=str(video),
               COLAB_BIN=str(colab), H3MUSE_BEKLE_SN="0", H3APP_WORK_DIR=str(tmp_path / "yerel_cache"))
    return {"tmp": tmp_path, "kok": kok, "env": env, "anahtar": str(anahtar), "colab": str(colab)}


def senaryo_yaz(ortam):
    yol = ortam["tmp"] / "senaryo.json"
    r = calistir(os.path.join(MUSE, "senaryo.py"), "--h3", H3, "--fikir", 'Çay bahçesi. Çaycı: "Çaylar taze."',
                 "--sure", "5", "--sahte", "--cikti", str(yol), env=ortam["env"])
    assert yol.is_file(), r.stdout + r.stderr
    s = json.loads(yol.read_text())
    s["durum"] = "hazir"   # sahte örnek metinler fikirle eşleşmediği için denetim uyarısı verebilir
    yol.write_text(json.dumps(s, ensure_ascii=False))
    return str(yol)


def cagrilar(ortam):
    return [json.loads(s) for s in (ortam["kok"] / "cagrilar.jsonl").read_text().splitlines()]


def test_senaryo_sahte(ortam):
    yol = ortam["tmp"] / "s.json"
    r = calistir(os.path.join(MUSE, "senaryo.py"), "--h3", H3, "--fikir", "deneme", "--sure", "5", "--sahte",
                 "--cikti", str(yol), env=ortam["env"])
    assert r.returncode in (0, 2), r.stdout + r.stderr
    s = json.loads(yol.read_text())
    assert s["h3_commit"] == ortak.H3_COMMIT
    assert s["prompt"].startswith("integrated_multimodal_description")
    assert s["cozunurluk"] in ortak.COZUNURLUKLER.values()


def test_senaryo_acik_izinli_anahtari_reddeder(ortam):
    os.chmod(ortam["anahtar"], 0o644)
    r = calistir(os.path.join(MUSE, "senaryo.py"), "--h3", H3, "--fikir", "x", "--anahtar", ortam["anahtar"],
                 "--cikti", str(ortam["tmp"] / "x.json"), env=ortam["env"])
    assert r.returncode != 0 and "chmod 600" in (r.stdout + r.stderr)


def test_uretim_uctan_uca_ve_gpu_yedegi(ortam):
    s = senaryo_yaz(ortam)
    oturum = ortam["tmp"] / "oturum"
    env = dict(ortam["env"], SAHTE_PLAN="g4:503,h100:red,a100:ok")
    r = calistir(os.path.join(MUSE, "h3_uret.py"), "uret", "--senaryo", s, "--oturum-dizini", str(oturum),
                 "--anahtar", ortam["anahtar"], "--aralik", "1", env=env)
    cikti = r.stdout + r.stderr
    assert r.returncode == 0, cikti
    o = json.loads((oturum / "oturum.json").read_text())
    assert o["asama"] == "kapatildi" and o["gpu"] == "a100"
    assert o["uzak_durum"]["asama"] == "bitti"
    assert os.path.isfile(o["video"]["yol"]) and o["video"]["sure"] > 4
    kaynak = cagrilar(ortam)
    assert sum(1 for c in kaynak if c[:1] == ["new"] and "g4" in c) == 3      # G4 üç kez denendi
    assert sum(1 for c in kaynak if c[:1] == ["new"] and "h100" in c) == 1    # reddedilince hemen geçildi
    assert ["sessions"] in kaynak and any(c[0] == "stop" for c in kaynak)
    # anahtar hiçbir komut satırında, günlükte ya da raporda yok; runtime'da da silinmiş
    assert "SAHTE-ANAHTAR" not in json.dumps(kaynak) and "SAHTE-ANAHTAR" not in cikti
    assert not (ortam["kok"] / "content" / "h3muse" / "gemini.key").exists()
    assert "SAHTE-ANAHTAR" not in (oturum / "cikti" / "gunluk.txt").read_text()
    assert "teslim edildi" in (oturum / "rapor.md").read_text()


def test_cpu_kuru_deneme_ornek_videoyu_kendi_uretir(ortam):
    s = senaryo_yaz(ortam)
    env = dict(ortam["env"], SAHTE_PLAN="cpu:ok")
    env.pop("H3APP_FAKE_VIDEO")
    oturum = ortam["tmp"] / "kuru"
    r = calistir(os.path.join(MUSE, "h3_uret.py"), "uret", "--senaryo", s, "--gpu", "cpu",
                 "--oturum-dizini", str(oturum), "--anahtar", "", "--aralik", "1", env=env)
    assert r.returncode == 0, r.stdout + r.stderr
    assert ["new", "-s"] == cagrilar(ortam)[1][:2] and "--gpu" not in cagrilar(ortam)[1]


def test_cpu_gercek_senaryoda_reddedilir(ortam):
    s = senaryo_yaz(ortam)
    veri = json.loads(open(s).read())
    veri["sahte"] = False
    open(s, "w").write(json.dumps(veri))
    r = calistir(os.path.join(MUSE, "h3_uret.py"), "uret", "--senaryo", s, "--gpu", "cpu",
                 "--oturum-dizini", str(ortam["tmp"] / "o6"), "--anahtar", "", env=ortam["env"])
    assert r.returncode != 0 and "CPU runtime" in r.stderr


def test_gpu_alinamazsa_hicbir_sey_acilmaz(ortam):
    s = senaryo_yaz(ortam)
    env = dict(ortam["env"], SAHTE_PLAN="g4:503,a100:503")
    r = calistir(os.path.join(MUSE, "h3_uret.py"), "uret", "--senaryo", s, "--gpu", "g4,a100",
                 "--oturum-dizini", str(ortam["tmp"] / "o2"), "--anahtar", "", env=env)
    assert r.returncode == 3, r.stdout + r.stderr
    assert not any(c[0] == "stop" for c in cagrilar(ortam))


def test_411_hatasinda_yama_onerir(ortam):
    s = senaryo_yaz(ortam)
    env = dict(ortam["env"], SAHTE_PLAN="g4:411")
    r = calistir(os.path.join(MUSE, "h3_uret.py"), "uret", "--senaryo", s, "--gpu", "g4",
                 "--oturum-dizini", str(ortam["tmp"] / "o3"), "--anahtar", "", env=env)
    assert r.returncode == 1 and "yama_411.py" in r.stdout


def test_uretim_hatasinda_runtime_kapatilir(ortam):
    s = senaryo_yaz(ortam)
    env = dict(ortam["env"], H3APP_FAKE_VIDEO="/yok/video.mp4")   # sahte render başarısız olur
    oturum = ortam["tmp"] / "o4"
    r = calistir(os.path.join(MUSE, "h3_uret.py"), "uret", "--senaryo", s, "--oturum-dizini", str(oturum),
                 "--anahtar", "", "--aralik", "1", env=env)
    assert r.returncode == 1, r.stdout + r.stderr
    o = json.loads((oturum / "oturum.json").read_text())
    assert o["asama"] == "kapatildi"
    assert o["ccu_sonra"]["aktif"] == 0
    assert (oturum / "cikti" / "gunluk.txt").is_file()   # hata yolunda günlük yine indi


def test_kopmadan_sonra_devam(ortam, monkeypatch):
    s = senaryo_yaz(ortam)
    for k, v in ortam["env"].items():
        monkeypatch.setenv(k, v)
    oturum = h3_uret.Oturum(str(ortam["tmp"] / "o5"))
    os.makedirs(oturum.dizin)
    oturum.kaydet(asama="yeni", senaryo=s, gpular=["g4"], anahtar=None, azami_dk=10, aralik=1)
    c = h3_uret.Colab(ortam["colab"], oturum.dizin)
    oturum.kaydet(ccu_once=c.bakiye())
    h3_uret.runtime_ac(c, oturum, ["g4"])
    h3_uret.yukle(c, oturum, s, None)
    h3_uret.baslat(c, oturum)
    # Burada Muse'un makinesi yeniden başlamış gibi: süreç biter, sonra 'devam' çağrılır
    r = calistir(os.path.join(MUSE, "h3_uret.py"), "devam", "--oturum-dizini", oturum.dizin, env=ortam["env"])
    assert r.returncode == 0, r.stdout + r.stderr
    assert json.loads(open(oturum.yol).read())["asama"] == "kapatildi"


def test_yama_411_idempotent(tmp_path):
    whl = os.environ.get("COLAB_CLI_CLIENT")
    if not whl:
        pytest.skip("COLAB_CLI_CLIENT (google-colab-cli 0.8.0 client.py yolu) verilmedi")
    hedef = tmp_path / "client.py"
    shutil.copyfile(whl, hedef)
    r1 = calistir(os.path.join(MUSE, "yama_411.py"), "--dosya", str(hedef))
    r2 = calistir(os.path.join(MUSE, "yama_411.py"), "--dosya", str(hedef))
    assert r1.returncode == 0 and "uygulandı" in r1.stdout
    assert r2.returncode == 0 and "zaten" in r2.stdout
    assert hedef.read_text().count('kwargs["json"] = {}') == 1
    assert calistir(os.path.join(MUSE, "yama_411.py"), "--dosya", str(hedef), "--kontrol").returncode == 0
