"""Muse betiklerinin sahte modda uçtan uca testleri. GPU, Colab ve Gemini gerekmez.

Gerekenler: ffmpeg/ffprobe ve h3/requirements-dev.txt.
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
H3 = os.environ.get("H3_DIZIN", os.path.join(KOK, "h3"))
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
    colab = tmp_path / "colab"
    colab.write_text(f"#!/bin/sh\nexec {sys.executable} {SAHTE} \"$@\"\n")
    colab.chmod(0o755)
    anahtar = tmp_path / "gemini.key"
    anahtar.write_text("SAHTE-ANAHTAR-123\n")
    anahtar.chmod(0o600)
    env = dict(os.environ, SAHTE_KOK=str(kok), SAHTE_PYTHON=sys.executable, H3APP_FAKE_VIDEO=str(video),
               COLAB_BIN=str(colab), H3MUSE_BEKLE_SN="0", H3MUSE_TEKRAR_SN="0", H3APP_WORK_DIR=str(tmp_path / "yerel_cache"))
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
    assert s["h3app_surum"] == ortak.h3app_surum()
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
    assert o["isler"]["1"]["asama"] == "indirildi" and o["asama"] == "kapatildi"
    assert os.path.isfile(o["video"]["yol"]) and o["video"]["sure"] > 4
    kaynak = cagrilar(ortam)
    assert sum(1 for c in kaynak if c[:1] == ["new"] and "g4" in c) == 3      # G4 üç kez denendi
    assert sum(1 for c in kaynak if c[:1] == ["new"] and "h100" in c) == 1    # reddedilince hemen geçildi
    assert ["sessions"] in kaynak and any(c[0] == "stop" for c in kaynak)
    # anahtar hiçbir komut satırında, günlükte ya da raporda yok; runtime'da da silinmiş
    assert "SAHTE-ANAHTAR" not in json.dumps(kaynak) and "SAHTE-ANAHTAR" not in cikti
    assert not (ortam["kok"] / "content" / "h3muse" / "gemini.key").exists()
    assert "SAHTE-ANAHTAR" not in (oturum / "cikti" / "gunluk.txt").read_text()
    rapor = (oturum / "rapor.md").read_text()
    assert "teslim edildi" in rapor and "CCU/saat ≈" in rapor


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
    h3_uret.yukle(c, oturum, s)
    # İş 1'i başlat; sonra Muse'un makinesi yeniden başlamış gibi süreç biter ve 'devam' çağrılır
    yerel = os.path.join(oturum.dizin, "_kod", "is_1.json")
    ortak.json_yaz(yerel, {"no": 1, "tur": "tek", "seed": 22})
    c.calistir("upload", "-s", oturum.v["ad"], yerel, "content/h3muse/is.json")
    c.kod(oturum.v["ad"], h3_uret.KOD_BASLAT.replace("@NO@", "1"))
    oturum.kaydet(asama="uretim", isler={"1": {"tanim": {"no": 1, "tur": "tek", "seed": 22}, "asama": "baslatildi"}})
    r = calistir(os.path.join(MUSE, "h3_uret.py"), "devam", "--oturum-dizini", oturum.dizin, env=ortam["env"])
    assert r.returncode == 0, r.stdout + r.stderr
    assert json.loads(open(oturum.yol).read())["asama"] == "kapatildi"
    assert sum(1 for x in cagrilar(ortam) if x[-1] == "content/h3muse/is.json") == 1   # iş yeniden başlatılmadı


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


# ---------------- uzun video ----------------

def uzun_senaryo_hazirla(ortam, kol="ikisi", ek=()):
    d = ortam["tmp"] / "uzun"
    us = os.path.join(MUSE, "uzun_senaryo.py")
    fikir = 'Çay bahçesi. Çaycı: "Çaylar taze, buyurun." Sonra: "Afiyet olsun."'
    r1 = calistir(us, "kart", "--h3", H3, "--dizin", str(d), "--fikir", fikir, "--sure", "24", "--sahte",
                  env=ortam["env"])
    assert r1.returncode == 0, r1.stdout + r1.stderr
    r2 = calistir(us, "gorsel", "--h3", H3, "--dizin", str(d), env=ortam["env"])
    assert r2.returncode == 0, r2.stdout + r2.stderr
    r3 = calistir(us, "plan", "--h3", H3, "--dizin", str(d), "--kol", kol, *ek, env=ortam["env"])
    assert r3.returncode == 0, r3.stdout + r3.stderr
    return d, json.loads((d / "uzun_senaryo.json").read_text())


def test_uzun_senaryo_sahte(ortam):
    d, s = uzun_senaryo_hazirla(ortam)
    assert s["tur"] == "uzun" and s["deney"] and s["yeniden_uretim"] == 0
    assert set(s["kollar"]) == {"metin", "ref"}
    assert [b["sure"] for b in s["kollar"]["ref"]["bloklar"]] == [12, 12]
    assert [r["rol"] for r in s["referanslar"]] == ["karakter", "arka_plan"]
    assert all(os.path.isfile(r["dosya"]) for r in s["referanslar"])
    # dünya çapası iki kolda ve her blokta aynı
    istekler = [b["istek"] for k in s["kollar"].values() for b in k["bloklar"]]
    assert all(s["dunya_capasi"] in i for i in istekler)
    assert "warm deep voice" in s["dunya_capasi"]   # ses tarifi çapada


def test_uzun_deney_uctan_uca(ortam):
    d, _ = uzun_senaryo_hazirla(ortam)
    oturum = ortam["tmp"] / "uzun_oturum"
    r = calistir(os.path.join(MUSE, "h3_uret.py"), "uret", "--senaryo", str(d / "uzun_senaryo.json"),
                 "--oturum-dizini", str(oturum), "--anahtar", "", "--aralik", "1", env=ortam["env"])
    cikti = r.stdout + r.stderr
    assert r.returncode == 0, cikti
    dosyalar = os.listdir(oturum / "cikti")
    assert sum(f.endswith("_birlesik.mp4") for f in dosyalar) == 2
    assert "uzun_sonuc.json" in dosyalar
    o = json.loads((oturum / "oturum.json").read_text())
    assert o["video"]["sure"] > 9 and o["video"]["yol"].endswith("ref_pika_h3_flex_birlesik.mp4")
    rapor = (oturum / "rapor.md").read_text()
    assert "Kol `metin`" in rapor and "Kol `ref`" in rapor
    yuklenen = [c[-1] for c in cagrilar(ortam) if c[0] == "upload"]
    assert "content/h3muse/ref_1.png" in yuklenen and "content/h3muse/ref_2.png" in yuklenen
    assert "content/h3muse/h3app.tar" in yuklenen


def test_uzun_kopru(ortam):
    d, _ = uzun_senaryo_hazirla(ortam, kol="ref", ek=("--kopru",))
    oturum = ortam["tmp"] / "kopru_oturum"
    r = calistir(os.path.join(MUSE, "h3_uret.py"), "uret", "--senaryo", str(d / "uzun_senaryo.json"),
                 "--oturum-dizini", str(oturum), "--anahtar", "", "--aralik", "1", env=ortam["env"])
    assert r.returncode == 0, r.stdout + r.stderr
    assert "köprü karesi eklendi" in r.stdout
    assert "kopru_ref_2.png" in os.listdir(oturum / "cikti")


def test_teslim_parcalara_bolunur(tmp_path, monkeypatch):
    import runtime_runner
    monkeypatch.setattr(runtime_runner, "PARCA_SINIRI", 2500)
    monkeypatch.setattr(runtime_runner, "TEK_DOSYA_SINIRI", 4000)
    dosyalar = []
    for i, boyut in enumerate([1000, 1000, 1000, 5000]):
        p = tmp_path / f"d{i}.bin"
        p.write_bytes(os.urandom(boyut))
        dosyalar.append(str(p))
    (tmp_path / "gunluk.txt").write_text("x")
    paket = runtime_runner.teslim_paketi(str(tmp_path), dosyalar[1:], [dosyalar[0]])
    assert [p["icerik"][0] for p in paket["parcalar"]][0] == "d0.bin"   # temel dosya ilk parçada
    assert len(paket["parcalar"]) == 2 and paket["pakete_girmeyen"] == ["d3.bin"]


def test_uzun_gemini_yollari_taklitle(ortam, monkeypatch):
    """Gemini çağrıları taklit edilir: kart JSON'u, çekim planı ve blok prompt'ları doğru girdilerle istenir mi?"""
    sys.path.insert(0, H3)
    monkeypatch.setenv("H3APP_WORK_DIR", ortam["env"]["H3APP_WORK_DIR"])
    from h3app import prompt_writer as pw
    import uzun_senaryo
    from h3app import hikaye as hk
    fikir = 'Çaycı: "Çaylar taze." Kadın: "Teşekkürler."'
    kart = hk.ornek_kart(fikir, 20)
    istekler = {"generate": [], "plan": [], "rewrite": []}

    def gen(api_key, model, system, contents, temperature, log=None, step=None):
        istekler["generate"].append((model, system, contents))
        return json.dumps(kart, ensure_ascii=False)

    def plan(idea, total, api_key, model, images=(), style="real", log=print, roles=None, **_):
        istekler["plan"].append((idea, total, list(images), roles))
        return hk.ornek_plan(kart), []

    def rewrite(request, seconds, api_key, model, images=(), log=print, style="real", roles=None, **_):
        istekler["rewrite"].append((seconds, list(images), roles))
        return pw.EXAMPLE_OUTPUT, []

    monkeypatch.setattr(pw, "_generate", gen)
    monkeypatch.setattr(pw, "plan_shots", plan)
    monkeypatch.setattr(pw, "rewrite", rewrite)
    d = ortam["tmp"] / "taklit"
    ortak_arg = ["--h3", H3, "--dizin", str(d), "--anahtar", ortam["anahtar"]]
    assert uzun_senaryo.main(["kart", *ortak_arg, "--fikir", fikir, "--sure", "20"]) == 0
    assert "20-second video made of 2 block(s)" in istekler["generate"][0][1]
    assert "SAHTE-ANAHTAR" not in json.dumps(istekler["generate"], ensure_ascii=False)
    os.makedirs(d / "gorseller")
    for ad in ("K1", "MEKAN"):
        hk.ornek_png(str(d / "gorseller" / f"{ad}.png"))
    assert uzun_senaryo.main(["plan", *ortak_arg, "--kol", "ikisi"]) == 0
    idea, total, imgs, roles = istekler["plan"][0]
    assert total == 20 and '"Çaylar taze."' in idea and len(imgs) == 2
    assert [r["role"] for r in roles] == ["karakter", "arka_plan"]
    # metin kolu görselsiz, ref kolu iki görselle yazıldı (blok başına bir çağrı)
    assert [len(x[1]) for x in istekler["rewrite"]] == [0, 0, 2, 2]


def test_eski_h3app_ile_yazilmis_senaryo_reddedilir(ortam):
    s = senaryo_yaz(ortam)
    veri = json.loads(open(s).read())
    veri["h3app_surum"] = "eskisurum000"
    open(s, "w").write(json.dumps(veri))
    r = calistir(os.path.join(MUSE, "h3_uret.py"), "uret", "--senaryo", s, "--oturum-dizini",
                 str(ortam["tmp"] / "o7"), "--anahtar", "", env=ortam["env"])
    assert r.returncode != 0 and "h3app sürümü" in r.stderr


def test_yama_411_elle_uygulanmis_yamayi_tanir(tmp_path):
    kaynak = os.environ.get("COLAB_CLI_CLIENT")
    if not kaynak:
        pytest.skip("COLAB_CLI_CLIENT verilmedi")
    metin = open(kaynak, encoding="utf-8").read().replace(
        "        response = self.session.request(",
        '        if method.upper() == "POST" and "data" not in kwargs and "json" not in kwargs:\n'
        '            kwargs["json"] = {}\n        response = self.session.request(', 1)
    hedef = tmp_path / "client.py"
    hedef.write_text(metin, encoding="utf-8")
    r = calistir(os.path.join(MUSE, "yama_411.py"), "--dosya", str(hedef), "--kontrol")
    assert r.returncode == 0 and "işlevsel" in r.stdout
    calistir(os.path.join(MUSE, "yama_411.py"), "--dosya", str(hedef))
    assert hedef.read_text(encoding="utf-8").count('kwargs["json"] = {}') == 1   # ikinci kez eklenmedi


def test_anahtar_yoksa_gemini_oncesi_acik_mesaj(ortam):
    r = calistir(os.path.join(MUSE, "uzun_senaryo.py"), "kart", "--dizin", str(ortam["tmp"] / "k"), "--sure", "20",
                 "--fikir", "x", "--anahtar", str(ortam["tmp"] / "yok.key"), env=ortam["env"])
    cikti = r.stdout + r.stderr
    assert r.returncode != 0 and "güvenli giriş kartıyla" in cikti and "hikâye kartını yazıyor" not in cikti
    r2 = calistir(os.path.join(MUSE, "uzun_senaryo.py"), "gorsel", "--dizin", str(ortam["tmp"] / "k"),
                  env=ortam["env"])
    assert r2.returncode == 1 and "Önce 'kart'" in r2.stdout


def test_anahtar_ortam_degiskeninden(ortam):
    s = senaryo_yaz(ortam)
    env = dict(ortam["env"], GEMINI_API_KEY="ORTAM-ANAHTARI-456")
    oturum = ortam["tmp"] / "ortam_anahtar"
    r = calistir(os.path.join(MUSE, "h3_uret.py"), "uret", "--senaryo", s, "--oturum-dizini", str(oturum),
                 "--anahtar", str(ortam["tmp"] / "olmayan.key"), "--aralik", "1", env=env)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "ORTAM-ANAHTARI" not in r.stdout + r.stderr
    assert not any("gemini.key" in str(x) for x in cagrilar(ortam))   # anahtar runtime'a hiç gitmez
    assert "ORTAM-ANAHTARI" not in json.dumps(cagrilar(ortam))


def test_izle_yerel_gemini_taklitle(ortam, monkeypatch, tmp_path):
    sys.path.insert(0, H3)
    monkeypatch.setenv("H3APP_WORK_DIR", ortam["env"]["H3APP_WORK_DIR"])
    from h3app import prompt_writer as pw, review
    import izle
    istek = {}

    class Yanit:
        text = ('{"verdict": "fail", "defects": [{"start_s": 1, "end_s": 2, "severity": "high", '
                '"category": "anatomy", "description": "extra hand"}], "summary": "x"}')

    class Istemci:
        class models:
            @staticmethod
            def generate_content(model, contents, config):
                istek["metin"] = " ".join(c for c in contents if isinstance(c, str))
                return Yanit()

    monkeypatch.setattr(pw, "_client", lambda *a, **k: Istemci())
    monkeypatch.setattr(review, "_proxy", lambda path, d: path)
    video = tmp_path / "v.mp4"
    video.write_bytes(b"0")
    s = senaryo_yaz(ortam)
    cikti = tmp_path / "inceleme.json"
    assert izle.main(["--video", str(video), "--senaryo", s, "--anahtar", ortam["anahtar"],
                      "--cikti", str(cikti)]) == 0
    sonuc = json.loads(cikti.read_text())
    assert sonuc["defects"][0]["severity"] == "high" and "Generation prompt" in istek["metin"]


def test_yerel_izleme_kusurda_ayni_runtimeda_yeniden_uretir(ortam):
    s = senaryo_yaz(ortam)
    kusur = {"verdict": "fail", "defects": [{"start_s": 1, "end_s": 2, "severity": "high", "category": "anatomi",
                                             "description": "fazladan el"}], "summary": "x", "model": "taklit"}
    temiz = {"verdict": "pass", "defects": [], "summary": "ok", "model": "taklit"}
    env = dict(ortam["env"], H3MUSE_TEST_INCELEME=json.dumps([kusur, temiz]))
    oturum = ortam["tmp"] / "izleme"
    r = calistir(os.path.join(MUSE, "h3_uret.py"), "uret", "--senaryo", s, "--oturum-dizini", str(oturum),
                 "--anahtar", ortam["anahtar"], "--aralik", "1", env=env)
    assert r.returncode == 0, r.stdout + r.stderr
    o = json.loads((oturum / "oturum.json").read_text())
    assert len(o["isler"]) == 2 and o["sonuc"]["secilen"].endswith("seed1022.mp4")
    assert sum(1 for x in cagrilar(ortam) if x[0] == "new") == 1          # aynı runtime
    assert not any("gemini.key" in str(x) for x in cagrilar(ortam))
    rapor = (oturum / "rapor.md").read_text()
    assert "aday" in rapor and "kusur yok" in rapor and "1 yüksek" in rapor


def test_uzun_yerel_izleme_ve_sureklilik(ortam):
    d, s = uzun_senaryo_hazirla(ortam, kol="ref", ek=("--kopru",))
    temiz = {"verdict": "pass", "defects": [], "summary": "ok", "model": "taklit"}
    surek = {"kimlik": 9, "kiyafet": 8, "mekan": 9, "ses": 6, "hikaye": 8, "ortalama": 8.0, "sorunlar": [],
             "model": "taklit"}
    env = dict(ortam["env"], H3MUSE_TEST_INCELEME=json.dumps([temiz, temiz]),
               H3MUSE_TEST_SUREKLILIK=json.dumps([surek]))
    oturum = ortam["tmp"] / "uzun_izleme"
    r = calistir(os.path.join(MUSE, "h3_uret.py"), "uret", "--senaryo", str(d / "uzun_senaryo.json"),
                 "--oturum-dizini", str(oturum), "--anahtar", ortam["anahtar"], "--aralik", "1", env=env)
    assert r.returncode == 0, r.stdout + r.stderr
    rapor = (oturum / "rapor.md").read_text()
    assert "ses 6" in rapor and "ortalama 8.0" in rapor
    yuklenen = [x[-1] for x in cagrilar(ortam) if x[0] == "upload"]
    assert "content/h3muse/kopru_ref_2.png" in yuklenen
    assert (oturum / "cikti" / "uzun_sonuc.json").is_file()


def test_no_proxy_kosesiz(monkeypatch):
    monkeypatch.setenv("NO_PROXY", "localhost,[::1],127.0.0.1,[fd00::1]")
    ortak.ag_ortamini_duzelt()
    assert os.environ["NO_PROXY"] == "localhost,::1,127.0.0.1,fd00::1"


def test_gecici_zaman_asiminda_tekrar_dener(ortam):
    s = senaryo_yaz(ortam)
    env = dict(ortam["env"], SAHTE_ZAMAN_ASIMI="2")   # ilk iki exec ReadTimeout verir
    oturum = ortam["tmp"] / "zaman_asimi"
    r = calistir(os.path.join(MUSE, "h3_uret.py"), "uret", "--senaryo", s, "--oturum-dizini", str(oturum),
                 "--anahtar", "", "--aralik", "1", env=env)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "geçici olarak ulaşılamadı" in r.stdout


def test_is_baslatma_takilirsa_tekrar_dener(ortam):
    s = senaryo_yaz(ortam)
    env = dict(ortam["env"], SAHTE_ASILMA="1")   # Deney B: iş başlatma komutu 240 sn yanıt vermedi
    oturum = ortam["tmp"] / "asilma"
    r = calistir(os.path.join(MUSE, "h3_uret.py"), "uret", "--senaryo", s, "--oturum-dizini", str(oturum),
                 "--anahtar", "", "--aralik", "1", env=env)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "geçici olarak ulaşılamadı" in r.stdout
    assert len(json.loads((oturum / "oturum.json").read_text())["isler"]) == 1


def test_yeniden_esik_orta(ortam):
    s = senaryo_yaz(ortam)
    orta = {"verdict": "pass", "defects": [{"start_s": 1, "end_s": 2, "severity": "medium", "category": "el",
                                            "description": "parmak"}], "summary": "x"}
    temiz = {"verdict": "pass", "defects": [], "summary": "ok"}
    for esik, beklenen in (("yuksek", 1), ("orta", 2)):
        env = dict(ortam["env"], H3MUSE_TEST_INCELEME=json.dumps([orta, temiz]))
        oturum = ortam["tmp"] / f"esik_{esik}"
        r = calistir(os.path.join(MUSE, "h3_uret.py"), "uret", "--senaryo", s, "--oturum-dizini", str(oturum),
                     "--anahtar", ortam["anahtar"], "--aralik", "1", "--yeniden-esik", esik, env=env)
        assert r.returncode == 0, r.stdout + r.stderr
        assert len(json.loads((oturum / "oturum.json").read_text())["isler"]) == beklenen
