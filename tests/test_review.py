"""Otomatik izleme (Gemini videoyu izler) ve kusurda yeni seed ile yeniden üretim döngüsü."""

import json
import os
import sys
import types as pytypes

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from h3app import config, prompt_writer, review  # noqa: E402
from tests.test_assemble import _make_av_clip  # noqa: E402

HAND = {"start_s": 0, "end_s": 2, "severity": "high", "category": "anatomy",
        "description": "Disembodied hand holds the tea glass."}


def _res(*defects, model="gemini-2.5-flash"):
    r = review.normalize({"defects": list(defects), "summary": "x"})
    r["model"] = model
    return r


def test_normalize_score_and_summaries():
    r = review.normalize({"verdict": "pass", "defects": [
        {"start_s": "5", "end_s": 7, "severity": "Medium", "description": "finger blur"},
        HAND, {"start_s": None, "severity": "weird", "description": "?"}]})
    assert r["verdict"] == "fail"                      # karar modelin sözünden değil, yüksek kusurdan türetilir
    assert [d["severity"] for d in r["defects"]] == ["high", "medium", "medium"]
    assert review.blocking(r) and review.score(r) == (1, 2, 0)
    assert review.short(r) == "1 yüksek, 2 orta kusur" and review.short(_res()) == "kusur yok"
    assert review.short(None) == "izlenemedi" and review.score(None) == (99, 99, 99)
    assert "0.0–2.0 sn, yüksek" in review.summary(r) and "kusur bulunmadı" in review.summary(_res())


def test_review_video_falls_back_between_models_and_never_blocks(monkeypatch, tmp_path):
    vid = _make_av_clip(str(tmp_path / "v.mp4"), "red", seconds=1)
    calls = []

    class Models:
        def generate_content(self, model, contents, config):
            calls.append((model, config.system_instruction))
            if model == "gemini-3-flash-preview":
                raise RuntimeError("503 UNAVAILABLE")
            return pytypes.SimpleNamespace(text=json.dumps({"verdict": "fail", "defects": [HAND], "summary": "el"}))

    monkeypatch.setattr(prompt_writer, "_client", lambda key, timeout_ms=0: pytypes.SimpleNamespace(models=Models()))
    logs = []
    r = review.review_video(vid, "prompt", "k", log=logs.append)
    assert r["model"] == "gemini-3.8-flash" and review.blocking(r)
    assert [c[0] for c in calls] == ["gemini-3-flash-preview", "gemini-3.8-flash"]
    assert "frame by frame" in calls[0][1] and any("izleyemedi" in m for m in logs)
    assert not any("lite" in m for m in config.REVIEW_MODELS)

    class Down:
        def generate_content(self, model, contents, config):
            raise RuntimeError("429 RESOURCE_EXHAUSTED")
    monkeypatch.setattr(prompt_writer, "_client", lambda key, timeout_ms=0: pytypes.SimpleNamespace(models=Down()))
    assert review.review_video(vid, "prompt", "k") is None


def test_404_model_is_skipped_for_the_rest_of_the_session(monkeypatch, tmp_path):
    """17.11.2026: gemini-2.5-flash yeni kullanıcılara 404 NOT_FOUND veriyordu; her izlemede boşa çağrı gitmesin."""
    vid = _make_av_clip(str(tmp_path / "v.mp4"), "red", seconds=1)
    monkeypatch.setattr(prompt_writer, "_gone_models", set())
    calls = []

    class Models:
        def generate_content(self, model, contents, config):
            calls.append(model)
            if model == "old-model":
                raise RuntimeError("404 NOT_FOUND. models/old-model is no longer available to new users")
            return pytypes.SimpleNamespace(text=json.dumps({"verdict": "pass", "defects": [], "summary": ""}))

    monkeypatch.setattr(prompt_writer, "_client", lambda key, timeout_ms=0: pytypes.SimpleNamespace(models=Models()))
    logs = []
    for _ in range(3):
        r = review.review_video(vid, "p", "k", models=("old-model", "new-model"), log=logs.append)
        assert r["model"] == "new-model"
    assert calls == ["old-model", "new-model", "new-model", "new-model"]
    assert sum("404" in m for m in logs) == 1

    # Metin zinciri de 404'te durmaz, sıradaki modele geçer ve yedek kullanıldığını kaydeder
    def fake_stream(key, m, system, contents, temperature):
        if m == "gone-text":
            raise RuntimeError("404 NOT_FOUND")
        return "ok"
    monkeypatch.setattr(prompt_writer, "_stream_text", fake_stream)
    monkeypatch.setattr(config, "GEMINI_MODEL", "gone-text")
    monkeypatch.setattr(config, "GEMINI_FALLBACK_MODELS", ("alive-text",))
    assert prompt_writer._generate("k", "gone-text", "s", ["c"], 0.3) == "ok"
    assert prompt_writer.last_model == {"name": "alive-text", "fallback": True}
    assert "gone-text" not in prompt_writer.available(["gone-text", "alive-text"])


def _ui(monkeypatch, tmp_path, results):
    monkeypatch.setitem(sys.modules, "gradio", pytypes.SimpleNamespace(update=lambda **kw: kw))
    from h3app import ui
    monkeypatch.setattr(ui, "FAKE", True)
    monkeypatch.setattr(ui, "REAL_GEMINI", True)            # video sahte, izleme "gerçek" (aşağıda taklit)
    monkeypatch.setenv("H3APP_FAKE_VIDEO", _make_av_clip(str(tmp_path / "fake.mp4"), "blue", seconds=1))
    monkeypatch.setattr(ui.config, "OUTPUT_DIR", str(tmp_path / "out"))
    ui._state["drive_dir"] = None
    seen = []

    def fake_review(path, prompt, key, images=(), roles=None, log=None):
        seen.append(os.path.basename(path))
        return results[min(len(seen) - 1, len(results) - 1)]
    monkeypatch.setattr(ui.review, "review_video", fake_review)
    return ui, seen


def test_high_defect_triggers_new_seed_and_best_candidate_is_kept(monkeypatch, tmp_path):
    ui, seen = _ui(monkeypatch, tmp_path, [_res(HAND), _res()])
    steps = list(ui.generate(prompt_writer.EXAMPLE_OUTPUT, ["pika"], "16:9 yatay · 1344×768", 5, 22, "fikir", "", None,
                             "real", [], {}, None, True, 2, "k"))
    log, left, _right, files, _sheets = steps[-1]
    assert seen == ["%s_pika_h3_flex_seed22.mp4" % seen[0].split("_pika")[0], seen[1]] and "seed1022" in seen[1]
    assert "🔁 Yüksek önemde kusur var; yeni seed (1022)" in log and "⭐ Seçilen:" in log and "kusur yok" in log
    assert left.endswith("seed1022.mp4") and sum(f.endswith(".mp4") for f in files) == 2
    info = json.load(open(next(f for f in files if f.endswith("_bilgi.json")), encoding="utf-8"))
    assert info["videolar"]["pika"]["dosya"].endswith("seed1022.mp4") and len(info["videolar"]["pika"]["adaylar"]) == 2

    # Bağlantı koptuysa: "Son Üretimleri Yükle" iki adaydan seçileni gösterir
    rec = ui.load_last_outputs()
    assert rec[1].endswith("seed1022.mp4") and "2 aday, seçilen" in rec[0]


def test_retries_are_capped_and_least_bad_candidate_wins(monkeypatch, tmp_path):
    worse = _res(HAND, dict(HAND, start_s=4, end_s=5))
    ui, seen = _ui(monkeypatch, tmp_path, [worse, _res(HAND), worse])
    log, left, *_ = list(ui.generate(prompt_writer.EXAMPLE_OUTPUT, ["pika"], "16:9 yatay · 1344×768", 5, 22, "f", "",
                                     None, "real", [], {}, None, True, 2, "k"))[-1]
    assert len(seen) == 3 and left.endswith("seed1022.mp4")          # 1 yüksek kusurlu aday, 2'liden iyi
    assert "Denemelerin hepsinde yüksek önemde kusur kaldı" in log

    ui, seen = _ui(monkeypatch, tmp_path, [_res(HAND)])
    log = list(ui.generate(prompt_writer.EXAMPLE_OUTPUT, ["pika"], "16:9 yatay · 1344×768", 5, 22, "f", "", None,
                           "real", [], {}, None, True, 0, "k"))[-1][0]
    assert len(seen) == 1 and "🔁" not in log                          # deneme sayısı 0: yeniden üretim yok

    ui, seen = _ui(monkeypatch, tmp_path, [_res(HAND)])
    log = list(ui.generate(prompt_writer.EXAMPLE_OUTPUT, ["pika"], "16:9 yatay · 1344×768", 5, 22, "f", "", None,
                           "real", [], {}, None, False, 2, "k"))[-1][0]
    assert seen == [] and "🔍" not in log                              # izleme kapalı


def test_quick_status_reports_review_result(monkeypatch, tmp_path):
    ui, _ = _ui(monkeypatch, tmp_path, [_res()])
    monkeypatch.setattr(ui.prompt_writer, "expand", lambda *a, **k: "brief")
    monkeypatch.setattr(ui.prompt_writer, "rewrite", lambda *a, **k: (prompt_writer.EXAMPLE_OUTPUT, []))
    status = list(ui.quick_generate("fikir", 8, "real", "pika", "16:9 yatay · 1344×768", 22, "gemini-x", "k"))[-1][0]
    assert status.startswith("✅ Hazır: ") and status.endswith("izleme: kusur yok")


def test_staging_rule_and_pov_check():
    assert "never shows a character's point of view" in prompt_writer.DIRECTION_RULES
    assert "Staging and hands" in prompt_writer.direction_rules("anime", 1)
    pov = prompt_writer.EXAMPLE_OUTPUT.replace("[Shot 1] ", "[Shot 1] A point-of-view shot from his eyes: ", 1)
    assert any("POV" in p for p in prompt_writer.check(pov, prompt_writer.EXAMPLE_INPUT))
    assert not any("POV" in p for p in prompt_writer.check(pov, "Kadının gözünden, bakış açısı çekimi"))
