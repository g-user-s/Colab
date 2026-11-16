"""Hızlı üretim: tek düğmeyle fikir → brief → H3 prompt'u → video (sahte modda, GPU ve Gemini olmadan)."""

import json
import os
import sys
import types as pytypes

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tests.test_assemble import _make_av_clip  # noqa: E402

FIX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "referans.png")


def _ui(monkeypatch, tmp_path):
    monkeypatch.setitem(sys.modules, "gradio", pytypes.SimpleNamespace(update=lambda **kw: kw))
    from h3app import ui
    monkeypatch.setattr(ui, "FAKE", True)
    monkeypatch.setattr(ui, "REAL_GEMINI", False)
    monkeypatch.setenv("H3APP_FAKE_VIDEO", _make_av_clip(str(tmp_path / "fake.mp4"), "blue", seconds=1))
    monkeypatch.setattr(ui.config, "OUTPUT_DIR", str(tmp_path / "out"))
    ui._state["drive_dir"] = None
    return ui


def test_quick_runs_all_steps_and_ends_with_ready_video(monkeypatch, tmp_path):
    ui = _ui(monkeypatch, tmp_path)
    steps = list(ui.quick_generate("Çay ocağında iki kişi", 10, "real", "pika", "16:9 yatay · 1344×768", 22,
                                   "gemini-test-pro", "k"))
    statuses = [st[0] for st in steps]
    assert any(s.startswith("⏳ 1/3") for s in statuses) and any(s.startswith("⏳ 2/3") for s in statuses)
    assert any(s.startswith("⏳ 3/3") for s in statuses)
    status, brief, prompt, video, files, log = steps[-1]
    assert status.startswith("✅ Hazır: ") and os.path.basename(video) in status
    assert os.path.isfile(video) and brief and prompt.startswith("integrated_multimodal_description:")
    assert any(f.endswith("_bilgi.json") for f in files) and "Tamamlandı" in log


def test_quick_uses_reference_roles_and_reports_errors(monkeypatch, tmp_path):
    ui = _ui(monkeypatch, tmp_path)
    assert list(ui.quick_generate("", 10, "real", "pika", "16:9 yatay · 1344×768", 22, "m", "k"))[-1][0].startswith("❌")
    roles = [{"role": "karakter", "name": "Ayşe"}, {"role": "arka_plan", "name": ""}]
    steps = list(ui.quick_generate("Ayşe çay ocağında", 99, "real", "bilinmeyen", "yok", 22, "m", "k",
                                   [FIX, FIX], roles, [], {}))
    status, *_rest, files, log = steps[-1]
    assert status.startswith("✅ Hazır")
    info = json.load(open(next(f for f in files if f.endswith("_bilgi.json")), encoding="utf-8"))
    assert [r["role"] for r in info["roller"]] == ["karakter", "arka_plan"]
    assert info["saniye"] <= 15.5 and info["yontemler"] == ["pika"]   # süre ve yöntem güvenli değerlere çekildi
