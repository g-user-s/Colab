"""Kesinti dayanıklılığı: arka plan işi, ComfyUI çıktısı kurtarma, Drive'dan model, Gemini model seçimi."""

import hashlib
import json
import os
import sys
import threading
import types as pytypes

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from h3app import config, setup_env  # noqa: E402


def _ui(monkeypatch):
    monkeypatch.setitem(sys.modules, "gradio", pytypes.SimpleNamespace(update=lambda **kw: kw))
    from h3app import ui
    return ui


def test_job_keeps_running_after_tab_closes(monkeypatch):
    ui = _ui(monkeypatch)
    gate, done = threading.Event(), []

    def job():
        yield ("başladı",)
        gate.wait(5)
        yield ("ikinci",)
        done.append(True)

    run = ui._in_background(job, "test")
    gen = run()
    assert next(gen) == ("başladı",)
    gen.close()                      # tarayıcı sekmesi kapandı: Gradio generator'ı kapatır
    assert ui.job_running()
    gate.set()
    ui._job["thread"].join(5)
    assert done and not ui.job_running()
    assert ui._job["last"] == ("ikinci",)


def test_load_or_follow_waits_for_running_job(monkeypatch, tmp_path):
    ui = _ui(monkeypatch)
    monkeypatch.setattr(ui.config, "OUTPUT_DIR", str(tmp_path / "bos"))
    gate = threading.Event()

    def job():
        yield ("üretim sürüyor",)
        gate.wait(5)

    gen = ui._in_background(job, "test")()
    next(gen)
    gen.close()
    follow = ui.load_or_follow(poll=0.05)
    first = next(follow)
    assert "izleniyor" in first[0] and "üretim sürüyor" in first[0] and len(first) == 11
    gate.set()
    last = list(follow)[-1]
    assert "bulunamadı" in last[0]


def test_busy_click_does_not_replace_tracked_job(monkeypatch):
    ui = _ui(monkeypatch)
    gate = threading.Event()

    def long_job():
        yield ("uzun",)
        gate.wait(5)

    def short_job():
        yield ("meşgul",)

    g1 = ui._in_background(long_job, "a")()
    next(g1)
    tracked = ui._job["thread"]
    assert list(ui._in_background(short_job, "b")()) == [("meşgul",)]
    assert ui._job["thread"] is tracked
    gate.set()
    tracked.join(5)


def test_recover_finished_comfy_outputs(monkeypatch, tmp_path):
    ui = _ui(monkeypatch)
    out, comfy = tmp_path / "out", tmp_path / "ComfyUI"
    monkeypatch.setattr(ui.config, "OUTPUT_DIR", str(out))
    monkeypatch.setattr(ui.config, "COMFY_DIR", str(comfy))
    ui._state["drive_dir"] = None
    stamp = "20261116_120000"
    (comfy / "output" / "h3app").mkdir(parents=True)
    out.mkdir()
    for fn in (f"{stamp}_b1_pika_00001_.mp4", f"{stamp}_b2_pika_s99_00001_.mp4", "20250101_000000_pika_00001_.mp4"):
        (comfy / "output" / "h3app" / fn).write_bytes(b"v")
    info = {"uzun_video": True, "stamp": stamp, "blocks": {"1": {"seed": 22, "seconds": 15, "prompt": "p"}}}
    (out / f"{stamp}_bilgi.json").write_text(json.dumps(info))
    rec = ui.load_last_outputs()
    names = sorted(os.listdir(out))
    assert f"{stamp}_blok1_pika_h3_flex_seed22.mp4" in names
    assert f"{stamp}_blok2_pika_h3_flex_seed99.mp4" in names
    assert not any(n.startswith("20250101") for n in names)
    assert "kurtarıldı" in rec[0]


def test_ready_returns_newest_model(monkeypatch):
    ui = _ui(monkeypatch)
    monkeypatch.setattr(ui, "FAKE", False)
    monkeypatch.setattr(ui.prompt_writer, "gemini_models", lambda key: ["gemini-yeni", "gemini-eski"])
    assert ui._ready("anahtar", None) == ("anahtar", "gemini-yeni", None)
    assert ui._ready("anahtar", "gemini-eski") == ("anahtar", "gemini-eski", None)
    key, _, err = ui._ready("", None) if not ui._state["secret_key"] else (None, None, "x")
    assert key is None and err


def test_models_come_from_hf_first_and_drive_only_as_fallback(monkeypatch, tmp_path):
    """17.11.2026 ölçümü: HF ~6 dk, Drive kopyası ~12 dk. HF önce; Drive yalnızca HF başarısızsa."""
    data = b"model-bytes"
    sha = hashlib.sha256(data).hexdigest()
    drive = tmp_path / "drive" / "MiniMax-H3" / "models" / "vae"
    drive.mkdir(parents=True)
    (drive / "x.safetensors").write_bytes(data)
    monkeypatch.setattr(config, "COMFY_DIR", str(tmp_path / "ComfyUI"))
    monkeypatch.setitem(config.MODELS, "test_ok", ("vae/x.safetensors", "vae", len(data), sha))
    dst = tmp_path / "ComfyUI" / "models" / "vae" / "x.safetensors"

    # HF çalışıyor: Drive'da kopya olsa bile HF'ten iner
    _fake_hub(monkeypatch, tmp_path, data)
    logs = []
    setup_env.ensure_models(["test_ok"], log=logs.append, source_dirs=[str(tmp_path / "drive")])
    assert dst.read_bytes() == data and any("İndiriliyor" in m for m in logs)
    assert not any("Drive'dan" in m for m in logs)

    # HF'e ulaşılamıyor: Drive kopyası kullanılır
    os.remove(dst)
    calls = []
    fake_hub = pytypes.SimpleNamespace(hf_hub_download=lambda *a, **k: calls.append(a) or (_ for _ in ()).throw(OSError("ağ yok")))
    monkeypatch.setitem(sys.modules, "huggingface_hub", fake_hub)
    logs.clear()
    setup_env.ensure_models(["test_ok"], log=logs.append, source_dirs=[str(tmp_path / "drive")])
    assert calls and dst.read_bytes() == data and any("Drive'dan kopyalanıyor" in m for m in logs)

    # HF bozuk indirme verirse de Drive'a düşülür
    os.remove(dst)
    _fake_hub(monkeypatch, tmp_path, b"model-byteZ")      # aynı boyut, yanlış SHA
    logs.clear()
    setup_env.ensure_models(["test_ok"], log=logs.append, source_dirs=[str(tmp_path / "drive")])
    assert dst.read_bytes() == data and any("Bozuk indirme" in m for m in logs)

    # HF yok, Drive kopyası da bozuk: hata verir, yarım dosya kalmaz
    (drive / "y.safetensors").write_bytes(b"bozuk-bytes")
    monkeypatch.setitem(config.MODELS, "test_bad", ("vae/y.safetensors", "vae", len(b"bozuk-bytes"), sha))
    monkeypatch.setitem(sys.modules, "huggingface_hub", fake_hub)
    import pytest
    with pytest.raises(OSError):
        setup_env.ensure_models(["test_bad"], log=logs.append, source_dirs=[str(tmp_path / "drive")])
    assert not (tmp_path / "ComfyUI" / "models" / "vae" / "y.safetensors").exists()
    assert not any(n.endswith(".part") for n in os.listdir(tmp_path / "ComfyUI" / "models" / "vae"))


def test_heartbeat_streams_log_during_long_silent_step(monkeypatch):
    ui = _ui(monkeypatch)
    import time as _t
    log = []

    def slow_step():
        log.append("İndiriliyor: model")
        _t.sleep(0.35)
        return 7

    def job():
        g = ui._heartbeat(slow_step, lambda: (list(log),), every=0.1)
        value = yield from g
        log.append(f"bitti {value}")
        yield (list(log),)

    snaps = list(job())
    assert len(snaps) >= 3 and "İndiriliyor: model" in snaps[0][0]   # adım sürerken günlük akar
    assert snaps[-1][0][-1] == "bitti 7"

    def failing():
        raise RuntimeError("bozuk indirme")
    import pytest
    with pytest.raises(RuntimeError, match="bozuk"):
        list(ui._heartbeat(failing, lambda: ("x",), every=0.05))


def test_runner_repeats_last_snapshot_while_job_is_quiet(monkeypatch):
    ui = _ui(monkeypatch)
    monkeypatch.setattr(ui, "HEARTBEAT_SECONDS", 0.05)
    gate = threading.Event()

    def job():
        yield ("ilk",)
        gate.wait(5)
        yield ("son",)

    gen = ui._in_background(job, "t")()
    got = [next(gen) for _ in range(4)]
    gate.set()
    rest = list(gen)
    assert got == [("ilk",)] * 4 and rest[-1] == ("son",)


def test_message_names_model_that_actually_wrote(monkeypatch):
    ui = _ui(monkeypatch)
    notes = ["⚠️ a yanıt vermedi; yedek modele geçiliyor: b", "↪️ Bu adım yedek modelle yazıldı: gemini-3.5-flash-lite"]
    assert ui._used_model(notes, "gemini-4-hydrogen") == "gemini-3.5-flash-lite"
    assert ui._used_model([], "gemini-4-hydrogen") == "gemini-4-hydrogen"


def test_colab_proxy_host_only_for_colab_dev(monkeypatch):
    ui = _ui(monkeypatch)
    ext = "7860-gpu-a100-x.europe-west4.prod.r.colab.dev"
    H = ui.ColabProxyHost.external_host
    assert H([(b"referer", f"https://{ext}/".encode())]) == ext
    assert H([(b"origin", f"https://{ext}".encode())]) == ext
    assert H([(b"referer", b"https://evil.example.com/")]) is None
    assert H([(b"referer", b"http://x.colab.dev/")]) is None                  # yalnızca https
    assert H([(b"x-forwarded-host", b"a"), (b"referer", f"https://{ext}/".encode())]) is None
    assert H([]) is None


def _fake_hub(monkeypatch, tmp_path, data):
    def download(repo, rel, revision=None, local_dir=None):
        p = os.path.join(local_dir, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "wb").write(data)
        return p
    monkeypatch.setitem(sys.modules, "huggingface_hub", pytypes.SimpleNamespace(hf_hub_download=download))
    monkeypatch.setattr(config, "WORK_DIR", str(tmp_path / "work"))


def test_downloaded_models_are_saved_to_drive_when_asked(monkeypatch, tmp_path):
    data = b"indirilen-model"
    sha = hashlib.sha256(data).hexdigest()
    _fake_hub(monkeypatch, tmp_path, data)
    monkeypatch.setattr(config, "COMFY_DIR", str(tmp_path / "ComfyUI"))
    monkeypatch.setitem(config.MODELS, "t_vae", ("vae/z.safetensors", "vae", len(data), sha))
    drive = tmp_path / "drive" / "MiniMax-H3" / "models"
    logs = []
    setup_env.ensure_models(["t_vae"], log=logs.append, source_dirs=[str(drive)], save_dir=str(drive))
    assert setup_env.wait_model_saves(5)
    assert (drive / "vae" / "z.safetensors").read_bytes() == data
    assert any("Drive'a kaydedildi" in m for m in logs)

    # sonraki oturum, HF'e ulaşılamıyor: model Drive'dan gelir ve tekrar kaydedilmez
    os.remove(tmp_path / "ComfyUI" / "models" / "vae" / "z.safetensors")
    monkeypatch.setitem(sys.modules, "huggingface_hub", pytypes.SimpleNamespace(
        hf_hub_download=lambda *a, **k: (_ for _ in ()).throw(OSError("ağ yok"))))
    logs.clear()
    setup_env.ensure_models(["t_vae"], log=logs.append, source_dirs=[str(drive)], save_dir=str(drive))
    assert setup_env.wait_model_saves(5)
    assert any("Drive'dan kopyalanıyor" in m for m in logs) and not any("kaydedilecek" in m for m in logs)


def test_model_save_skips_when_drive_is_full_or_option_off(monkeypatch, tmp_path):
    data = b"buyuk-model"
    sha = hashlib.sha256(data).hexdigest()
    _fake_hub(monkeypatch, tmp_path, data)
    monkeypatch.setattr(config, "COMFY_DIR", str(tmp_path / "ComfyUI"))
    monkeypatch.setitem(config.MODELS, "t_big", ("loras/b.safetensors", "loras", len(data), sha))
    drive = tmp_path / "drive"
    monkeypatch.setattr(setup_env.shutil, "disk_usage", lambda p: pytypes.SimpleNamespace(free=1))
    logs = []
    setup_env.ensure_models(["t_big"], log=logs.append, source_dirs=[], save_dir=str(drive))
    assert setup_env.wait_model_saves(5)
    assert (tmp_path / "ComfyUI" / "models" / "loras" / "b.safetensors").exists()   # üretim etkilenmedi
    assert not (drive / "loras" / "b.safetensors").exists() and any("yer yok" in m for m in logs)

    # seçenek kapalı (save_dir yok): hiçbir şey kaydedilmez
    monkeypatch.setattr(config, "MODEL_SAVE_DIR", None)
    os.remove(tmp_path / "ComfyUI" / "models" / "loras" / "b.safetensors")
    logs.clear()
    setup_env.ensure_models(["t_big"], log=logs.append, source_dirs=[])
    assert not any("Drive" in m for m in logs)
