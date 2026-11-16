"""Birden fazla referans görsel ve rolleri: karakter / arka plan-mekân / nesne."""

import os
import sys
import types as pytypes

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from h3app import prompt_writer  # noqa: E402
from tests.test_rewrite_mock import install  # noqa: E402

C, B, N = prompt_writer.ROLE_CHARACTER, prompt_writer.ROLE_SCENE, prompt_writer.ROLE_OBJECT
ROLES = [{"role": C, "name": "Çaycı Ahmet"}, {"role": B, "name": ""}, {"role": C, "name": ""}, {"role": N, "name": "semaver"}]


def _imgs(tmp_path, n):
    from PIL import Image
    out = []
    for i in range(n):
        p = tmp_path / f"g{i + 1}.png"
        Image.new("RGB", (8, 8), (40 * i, 0, 0)).save(p)
        out.append(str(p))
    return out


def test_characters_are_numbered_in_order_and_get_speaker_ids():
    specs = prompt_writer.normalize_roles(ROLES, 4)
    assert [s["char"] for s in specs] == [1, None, 2, None]
    assert "character 1" in prompt_writer.role_label(specs[0]) and "S1" in prompt_writer.role_label(specs[0])
    assert '"Çaycı Ahmet"' in prompt_writer.role_label(specs[0])
    assert "scene/background" in prompt_writer.role_label(specs[1])
    assert "character 2" in prompt_writer.role_label(specs[2]) and "S2" in prompt_writer.role_label(specs[2])
    assert "object/prop" in prompt_writer.role_label(specs[3])
    # eksik/bilinmeyen rol karakter sayılır
    assert [s["role"] for s in prompt_writer.normalize_roles([{"role": "??"}], 2)] == [C, C]


def test_pictures_reach_gemini_with_their_roles(monkeypatch, tmp_path):
    imgs = _imgs(tmp_path, 4)
    good = ("subject_definitions: <Subject 1> is Çaycı Ahmet from <Picture 1>. Reference role: identity anchor.\n"
            "<Subject 2> is the tea house in <Picture 2>. Reference role: scene anchor.\n"
            "<Subject 3> is the young man in <Picture 3>. Reference role: identity anchor.\n"
            "<Subject 4> is the samovar in <Picture 4>. Reference role: prop reference.\n\n"
            "summary: x\n\nretention_analysis: x\n\ndetailed_description: x\n\noverall_soundscape: x\n\n"
            "non_diegetic_music: N/A")
    fake = install(monkeypatch, [good], tmp_path)
    sent = []
    orig = fake.generate_content

    def gen(model, contents, config):
        sent.append((contents, config.system_instruction))
        return orig(model, contents, config)
    fake.generate_content = gen
    prompt, problems = prompt_writer.rewrite("iki kişi çay ocağında", 10, "k", "m", imgs, log=lambda m: None, roles=ROLES)
    assert problems == [], problems
    labels = [c for c in sent[0][0] if isinstance(c, str) and c.startswith("<Picture")]
    assert labels[1] == "<Picture 2> (role: scene/background — the setting, not a person):"
    assert labels[0].startswith('<Picture 1> (role: character 1 "Çaycı Ahmet"')
    assert "scene anchor" in sent[0][1] and "create a person from this picture" in sent[0][1]


def test_check_catches_background_used_as_a_person():
    bad = ("subject_definitions: <Subject 1> is the woman in <Picture 1>. Reference role: identity anchor.\n"
           "<Subject 2> is the man in <Picture 2>. Reference role: identity anchor.\n\n"
           "summary: <Picture 1> <Picture 2>\n\nretention_analysis: x\n\ndetailed_description: x\n\n"
           "overall_soundscape: x\n\nnon_diegetic_music: N/A")
    roles = [{"role": C}, {"role": B}]
    probs = prompt_writer.check(bad, "x", 2, roles=roles)
    assert any("<Picture 2>" in p and "arka plan" in p for p in probs)
    assert not any("<Picture 2>" in p and "arka plan" in p for p in prompt_writer.check(bad, "x", 2))   # rol yoksa eski davranış


def test_stylize_uses_scene_and_object_prompts(monkeypatch, tmp_path):
    src = _imgs(tmp_path, 1)[0]
    fake = install(monkeypatch, [], tmp_path)
    sent = []

    def gen(model, contents, config):
        sent.append(contents[0])
        part = pytypes.SimpleNamespace(inline_data=pytypes.SimpleNamespace(data=b"PNG", mime_type="image/png"))
        return pytypes.SimpleNamespace(candidates=[pytypes.SimpleNamespace(
            content=pytypes.SimpleNamespace(parts=[part]))])
    fake.generate_content = gen
    prompt_writer.stylize_reference(src, "anime", "k", "m", str(tmp_path / "o"), variants=1, role=B)
    prompt_writer.stylize_reference(src, "anime", "k", "m", str(tmp_path / "o"), variants=1, role=N)
    prompt_writer.stylize_reference(src, "anime", "k", "m", str(tmp_path / "o"), variants=1)
    assert "Remove every person" in sent[0] and "Redraw the person" not in sent[0]
    assert "Redraw this object" in sent[1]
    assert "Redraw the person" in sent[2]


def test_ui_keeps_order_and_roles_with_partial_style_picks(monkeypatch, tmp_path):
    monkeypatch.setitem(sys.modules, "gradio", pytypes.SimpleNamespace(update=lambda **kw: kw))
    from h3app import ui
    imgs = _imgs(tmp_path, 3)
    styled = {"Görsel 1 · A": "s1a.png", "Görsel 1 · B": "s1b.png", "Görsel 3 · B": "s3b.png"}
    # 2. görsel (arka plan) için çizim seçilmedi: yüklenen hâli yerinde kalır, sıra kaymaz
    assert ui._refs(imgs, "anime", ["Görsel 3 · B", "Görsel 1 · A"], styled) == ["s1a.png", imgs[1], "s3b.png"]
    assert ui._refs(imgs, "real", ["Görsel 1 · A"], styled) == imgs

    out = ui._on_refs(imgs)
    n = len(out)
    assert n == 1 + 3 * ui.config.MAX_REF_IMAGES + 1
    gallery, roles = out[0], out[-1]
    assert [c for _, c in gallery] == ["Görsel 1 · Karakter 1 (S1)", "Görsel 2 · Karakter 2 (S2)",
                                       "Görsel 3 · Karakter 3 (S3)"]
    assert out[1]["visible"] and not out[4]["visible"]

    dds = [C, B, C] + [C] * (ui.config.MAX_REF_IMAGES - 3)
    names = ["Ayşe", "", "Mehmet"] + [""] * (ui.config.MAX_REF_IMAGES - 3)
    roles, gallery = ui._collect_roles(imgs, *dds, *names)
    assert [c for _, c in gallery] == ["Görsel 1 · Karakter 1 (S1) — Ayşe", "Görsel 2 · Arka plan",
                                       "Görsel 3 · Karakter 2 (S2) — Mehmet"]
    assert ui.roles_summary(roles, imgs).count("Karakter") == 2
