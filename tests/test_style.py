"""Stil seçimi: kurallar, denetim, brief/H3 adımlarına iletim ve referans görseli stile çevirme (sahte Gemini)."""

import os
import sys
import types as pytypes

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from h3app import config, prompt_writer  # noqa: E402
from tests.test_rewrite_mock import FakeModels, install  # noqa: E402

T2V = "\n\n".join(f + " x" for f in prompt_writer.T2V_FIELDS)
STYLED = [k for k, v in config.STYLES.items() if "look" in v]


def test_style_table():
    assert config.DEFAULT_STYLE == "real" and set(STYLED) == {"anime", "pixar", "watercolour"}
    labels = [v["label"] for v in config.STYLES.values()]
    assert labels == ["Gerçek dünya", "Anime", "Disney Pixar", "Suluboya"]
    for k in STYLED:   # prompt'a marka adı gitmez
        s = config.STYLES[k]
        assert not any(b in (s["look"] + s["people"] + s["background"] + s["avoid"]).lower() for b in ("disney", "pixar"))


def test_real_style_keeps_old_rules(tmp_path):
    guides = prompt_writer.load_guide(str(tmp_path))
    assert prompt_writer.direction_rules("real") == prompt_writer.DIRECTION_RULES
    assert "moves on the ground" in prompt_writer.DIRECTION_RULES and "Animated styles" not in prompt_writer.DIRECTION_RULES
    assert prompt_writer.system_prompt(15, guides) == prompt_writer.system_prompt(15, guides, 0, "real")
    assert "Visual style" not in prompt_writer.brief_prompt(15)


def test_styled_rules_in_both_steps(tmp_path):
    guides = prompt_writer.load_guide(str(tmp_path))
    for k in STYLED:
        s = config.STYLES[k]
        for text in (prompt_writer.system_prompt(15, guides, 0, k), prompt_writer.system_prompt(15, guides, 1, k),
                     prompt_writer.brief_prompt(15, 0, k)):
            assert s["look"] in text and s["background"] in text and s["avoid"] in text
            assert "Nothing may look photographic" in text and "never heels" in text
            assert "redrawn in the chosen style" in text and "must look like the real place" not in text
            assert "with the floor visible" in text and "Never leave shops or stalls generic" in text
            assert "moves on the ground" in text
        assert "Reference pictures give the identity only" in prompt_writer.system_prompt(15, guides, 1, k)
        assert "Reference pictures give the identity only" not in prompt_writer.system_prompt(15, guides, 0, k)


def test_check_style_words():
    pixar_ok = T2V.replace(" x", " A 3D animated feature film, no photorealism, avoid live-action skin.", 1)
    assert prompt_writer.check(pixar_ok, "bir adam", 0, "pixar") == []
    assert any("stil" in p for p in prompt_writer.check(T2V, "bir adam", 0, "anime"))
    photo = T2V.replace(" x", " Live-action, photoreal anime scene.", 1)
    assert any("gerçekçiliği" in p for p in prompt_writer.check(photo, "bir adam", 0, "anime"))
    assert prompt_writer.check(photo, "bir adam", 0, "real") == []
    water = T2V.replace(" x", " A moving watercolor painting.", 1)
    assert prompt_writer.check(water, "x", 0, "watercolour") == []


def test_style_reaches_brief_and_rewrite(monkeypatch, tmp_path):
    fake = install(monkeypatch, ["brief"], tmp_path)
    assert prompt_writer.expand("Vapurda simit yiyen adam", 5, "k", "m", log=lambda m: None, style="pixar") == "brief"
    assert config.STYLES["pixar"]["look"] in fake.calls[0][2]
    good = T2V.replace(" x", " A 3D animated feature film on a ferry.", 1)
    fake = install(monkeypatch, [T2V, good], tmp_path)
    prompt, problems = prompt_writer.rewrite("a man on a ferry", 5, "k", "m", log=lambda m: None, style="pixar")
    assert problems == [] and prompt == good and len(fake.calls) == 2
    assert config.STYLES["pixar"]["look"] in fake.calls[0][2] and "Disney Pixar" in fake.calls[1][1]


def test_stylize_reference_and_image_models(monkeypatch, tmp_path):
    src = tmp_path / "kadin.png"
    src.write_bytes(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "referans.png"), "rb").read())
    fake = install(monkeypatch, [], tmp_path)
    sent = []

    def gen(model, contents, config):
        sent.append((model, contents, config))
        part = pytypes.SimpleNamespace(inline_data=pytypes.SimpleNamespace(data=b"PNGDATA%d" % len(sent),
                                                                         mime_type="image/png"))
        return pytypes.SimpleNamespace(candidates=[pytypes.SimpleNamespace(
            content=pytypes.SimpleNamespace(parts=[pytypes.SimpleNamespace(inline_data=None, text="ok"), part]))])
    fake.generate_content = gen
    outs = prompt_writer.stylize_reference(str(src), "anime", "k", "gemini-3-pro-image", str(tmp_path / "o"),
                                           idea="kırmızı paltolu ve gümüş atkılı bir kadın yürüyor")
    assert [os.path.basename(o) for o in outs] == ["kadin_anime_A.png", "kadin_anime_B.png"]
    assert open(outs[1], "rb").read() == b"PNGDATA2"
    assert config.STYLES["anime"]["look"] in sent[0][1][0] and "IMAGE" in sent[0][2].response_modalities
    assert "head to feet" in sent[0][1][0] and "kırmızı paltolu ve gümüş atkılı" in sent[0][1][0]
    prompt_writer.stylize_reference(str(src), "pixar", "k", "m", str(tmp_path / "o"), variants=1)
    assert "same clothing and colours as in the photo" in sent[-1][1][0]
    prompt_writer.stylize_reference(str(src), "watercolour", "k", "m", str(tmp_path / "o"), variants=1)
    wc_prompt = sent[-1][1][0]
    assert "wet-on-wet pigment bleed" in wc_prompt and "zero skin texture" in wc_prompt
    assert "realistic human faces" in wc_prompt and "visible brushwork" in wc_prompt
    assert prompt_writer.image_models("k") == ["gemini-3-pro-image"]
