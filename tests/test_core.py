"""Ağ gerektirmeyen testler + (internet varsa) skill dosyalarının doğrulanması."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from h3app import config, graphs, prompt_writer, setup_env  # noqa: E402

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
TEST2_REQUEST = ('Test 2, typography and Turkish text rendering. A rainy Istanbul back street at night, a hand-painted neon sign '
                 'above a tea house reads exactly "DUR, BİR BAK!" in glowing red letters, flickering once, reflected perfectly and '
                 'mirrored in the wet cobblestones. Below it a smaller chalkboard menu reads "ÇAY 15 TL" in white chalk handwriting.')
TEST2_PROMPT = open(os.path.join(FIXTURES, "test2_prompt.txt"), encoding="utf-8").read().strip()


def test_frames_match_official_formula():
    assert config.frames_for(14) == 345
    assert config.frames_for(15) == 362
    assert config.frames_for(4) == 107
    assert all((config.frames_for(s) - 5) % 17 == 0 for s in range(4, 16))


def test_literals_keep_turkish_characters():
    assert prompt_writer.literals(TEST2_REQUEST) == ["DUR, BİR BAK!", "ÇAY 15 TL"]
    assert prompt_writer.literals(prompt_writer.EXAMPLE_INPUT)[2] == "Kaçıran sensin, bakan değil."


def test_check_accepts_manual_prompts():
    assert prompt_writer.check(TEST2_PROMPT, TEST2_REQUEST) == []
    assert prompt_writer.check(prompt_writer.EXAMPLE_OUTPUT, prompt_writer.EXAMPLE_INPUT) == []


def test_check_catches_broken_text_and_missing_fields():
    broken = TEST2_PROMPT.replace("DUR, BİR BAK!", "DUR, BIR BAK!")
    assert any("DUR, BİR BAK!" in p for p in prompt_writer.check(broken, TEST2_REQUEST))
    assert prompt_writer.check("overall_soundscape: rain", TEST2_REQUEST)
    assert prompt_writer.clean("```\n" + TEST2_PROMPT + "\n```") == TEST2_PROMPT


def test_graphs_identical_to_validated_notebook():
    """graphs.build == ilk çalışan notebook'taki (yerel ComfyUI'ın /prompt doğrulamasından geçmiş) graph()."""
    g = {}
    exec("PROMPT = 'x'\nWIDTH, HEIGHT, SECONDS, H3_STEPS = 1344, 768, 15, 20\n", g)
    exec(open(os.path.join(FIXTURES, "validated_graph_nb05.py"), encoding="utf-8").read(), g)
    for method in ("pika", "h3"):
        old, n = g["graph"](method, 22, "p")
        new = graphs.build(method, "x", 22, 1344, 768, config.frames_for(15), "te_nvfp4", prefix="p")
        assert n == 362
        assert old == new, method


def test_int8_text_encoder_variant():
    g = graphs.build("h3", "x", 1, 768, 1344, 107, "te_int8")
    assert g["clip"]["inputs"]["clip_name"] == "qwen3vl_32b_minimax_h3_int8_convrot.safetensors"
    assert "lora" not in g and g["sigmas"]["inputs"]["steps"] == 20


def test_system_prompts_contain_guides(tmp_path):
    guides = prompt_writer.load_guide(str(tmp_path))
    s = prompt_writer.system_prompt(15, guides)
    assert "integrated_multimodal_description" in s and "Kızım, dünya" in s and "15 seconds" in s
    r = prompt_writer.system_prompt(15, guides, n_images=1)
    assert "subject_definitions" in r and "<Picture 1>" in r and "retention_analysis" in r
    b = prompt_writer.brief_prompt(15, 1)
    assert "DUR, BİR BAK!" in b and "reference picture" in b


def test_ref_check_and_graph():
    ref_prompt = "\n\n".join(f + " x <Picture 1>" for f in prompt_writer.REF_FIELDS)
    assert prompt_writer.check(ref_prompt, "", 1) == []
    assert any("<Picture 2>" in p for p in prompt_writer.check(ref_prompt, "", 2))
    g = graphs.build("pika", "p", 22, 1344, 768, 362, "te_nvfp4", ref_images=["a.png", "b.png"])
    assert g["cond"]["class_type"] == "MiniMaxH3ReferenceToVideo"
    assert g["cond"]["inputs"]["ref_images.ref_image_1"] == ["img1", 0]
    assert g["unet"]["inputs"]["unet_name"] == "minimax_h3_ref2va_pruned_int8_convrot.safetensors"
    assert g["lora"]["inputs"]["lora_name"] == "pika_h3_flex_ref2va_v1_bf16.safetensors"


def test_direction_rules_and_heel_check(tmp_path):
    guides = prompt_writer.load_guide(str(tmp_path))
    for s in (prompt_writer.system_prompt(15, guides), prompt_writer.system_prompt(15, guides, 1),
              prompt_writer.brief_prompt(15, 1)):
        assert "full-body" in s and "never heels" in s and "bargain" in s
        assert "No readable text, signboards, logos, banners or lettering anywhere in the frame" in s and "through windows" in s
        assert "Only the exact quoted sign text appears" in s
    t2v = "\n\n".join(f + " x" for f in prompt_writer.T2V_FIELDS)
    assert any("topuk" in p for p in prompt_writer.check(t2v + " high heels clicking", "a woman walks"))
    assert prompt_writer.check(t2v + " high heels clicking", "topuklu ayakkabılı kadın") == []


def test_signage_rules_and_check():
    assert "No readable text" in prompt_writer.signage_rule("Kapalıçarşı'da yürüyen bir kadın")
    assert "Only the exact quoted sign text appears" in prompt_writer.signage_rule('Tabelada "DUR, BİR BAK!" yazıyor')
    t2v = "\n\n".join(f + " x" for f in prompt_writer.T2V_FIELDS)
    assert any("tabela" in p for p in prompt_writer.check(t2v + ' a shop sign reading "Fiumaltaile"', "a woman walks"))
    assert any("tabela" in p for p in prompt_writer.check(t2v + " a banner with text above the door", "a woman walks"))
    assert prompt_writer.check(t2v + " with no written signs and no signboards reading anything.", "a woman walks") == []
    assert prompt_writer.check(t2v + ' a neon sign reading "DUR" above the door', 'tabelada "DUR" yazıyor') == []


def test_turbo_method_graph_and_roles():
    assert "turbo" in config.METHODS
    assert "Turbo" in config.METHODS["turbo"]["label"]
    # T2VA Turbo: 8 adım, minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors
    g_t2v = graphs.build("turbo", "prompt", 22, 1344, 768, 362, "te_nvfp4")
    assert g_t2v["lora"]["inputs"]["lora_name"] == "minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors"
    assert g_t2v["sampler"]["inputs"]["sampler_name"] == "res_multistep"
    assert g_t2v["sigmas"]["inputs"]["steps"] == 8
    assert g_t2v["guider"]["inputs"]["model"] == ["lora", 0]
    assert "turbo_lora" in setup_env.roles_for(["turbo"], "te_nvfp4", ref=False)

    # Ref2VA Turbo: 4 adım, minimax_h3_ref2v_turbo_4step_v0.1_comfyui_bf16.safetensors
    g_ref = graphs.build("turbo", "prompt", 22, 1344, 768, 362, "te_nvfp4", ref_images=["kadin.png"])
    assert g_ref["lora"]["inputs"]["lora_name"] == "minimax_h3_ref2v_turbo_4step_v0.1_comfyui_bf16.safetensors"
    assert g_ref["sigmas"]["inputs"]["steps"] == 4
    assert "turbo_lora_ref" in setup_env.roles_for(["turbo"], "te_nvfp4", ref=True)


def test_split_user_cuts_and_curly_apostrophe_check():
    script = (
        "The man’s eyes scan for danger.\n\n"
        "[cut] Extreme close-up: He says: “If one more bug touches me, I’m going back home.”\n\n"
        "[cut] Fast side tracking shot: He bolts through the jungle.\n\n"
        "Audio: Jungle ambience, buzzing insects."
    )
    cuts, audio = prompt_writer.split_user_cuts(script)
    assert len(cuts) == 3 and "crash" not in cuts[0] and "Extreme close-up" in cuts[1]
    assert audio == "Jungle ambience, buzzing insects."
    # Gemini düz kesme işareti (I'm) yazdığında kıvrık kesmeli (I’m) replik doğrulamadan geçmeli
    t2v = "\n\n".join(f + " <d>[English] If one more bug touches me, I'm going back home.</d>"
                      for f in prompt_writer.T2V_FIELDS)
    assert prompt_writer.check(t2v, script) == []


def test_generate_falls_back_when_first_chunk_is_late_or_model_busy(monkeypatch):
    import threading
    import types as pytypes
    import pytest
    release = threading.Event()

    class Models:
        def __init__(self):
            self.calls = []

        def generate_content_stream(self, model, contents, config):
            self.calls.append(model)
            if model == "yavas":
                release.wait(5)            # ilk parça hiç gelmiyor
            if model == "yogun":
                raise RuntimeError("429 RESOURCE_EXHAUSTED: quota")
            yield pytypes.SimpleNamespace(text="cevap ")
            yield pytypes.SimpleNamespace(text="tamam")

    models = Models()
    monkeypatch.setattr(prompt_writer, "_client", lambda key, timeout_ms=0: pytypes.SimpleNamespace(models=models))
    monkeypatch.setattr(config, "FIRST_CHUNK_SECONDS", 0.3)
    monkeypatch.setattr(config, "GEMINI_MODEL", "yavas")
    monkeypatch.setattr(config, "GEMINI_FALLBACK_MODELS", ("yogun", "hizli"))
    logs = []
    assert prompt_writer._generate("k", "yavas", "sys", ["x"], 0.3, log=logs.append) == "cevap tamam"
    release.set()
    assert models.calls == ["yavas", "yogun", "hizli"]
    assert any("yavas" in m and "yedek" in m for m in logs) and any("hizli" in m for m in logs)

    # Gemma'ya sistem talimatı ayrı alan olarak değil, mesajın başında gider
    seen = []

    class Gemma:
        def generate_content_stream(self, model, contents, config):
            seen.append((config.system_instruction, contents[0]))
            yield pytypes.SimpleNamespace(text="ok")
    monkeypatch.setattr(prompt_writer, "_client", lambda key, timeout_ms=0: pytypes.SimpleNamespace(models=Gemma()))
    assert prompt_writer._stream_text("k", "gemma-4-31b-it", "KURAL", ["soru"], 0.3) == "ok"
    assert seen[0][0] is None and "KURAL" in seen[0][1]

    # kalıcı hata (geçersiz anahtar) yedeğe geçmeden durur
    class Bad:
        def generate_content_stream(self, model, contents, config):
            raise RuntimeError("400 API key not valid")
            yield
    monkeypatch.setattr(prompt_writer, "_client", lambda key, timeout_ms=0: pytypes.SimpleNamespace(models=Bad()))
    with pytest.raises(RuntimeError, match="API key"):
        prompt_writer._generate("k", "a", "sys", ["x"], 0.3)




def test_background_speech_only_in_crowd_scenes():
    """17.11.2026 sahaf testi: iki kişilik sessiz dükkâna 'background speakers' eklendi, fazladan ses son kesmeyi
    ve repliği ~1 sn geciktirdi. Kalabalık/pazar yoksa arka plan konuşması kontrolde sorun sayılır."""
    from h3app import prompt_writer as pw
    quiet = ("A small, old antiquarian bookshop in Istanbul. An elderly bookseller sits behind a wooden counter; "
             "a young woman places an old leather-bound book on it.")
    added = (pw.EXAMPLE_OUTPUT.replace("non_diegetic_music: N/A", "").rstrip() +
             " Background speakers at a lower volume say: <d>[Turkish] Bir bakayım mı?</d>\n\nnon_diegetic_music: N/A")
    probs = pw.check(added, quiet)
    assert any("arka plan konuşması" in p for p in probs)
    assert not any("arka plan konuşması" in p for p in pw.check(pw.EXAMPLE_OUTPUT, quiet))
    bazaar = "A woman walks through the packed Grand Bazaar while merchants call out and bargain."
    assert not any("arka plan konuşması" in p for p in pw.check(added, bazaar))
    assert not any("arka plan konuşması" in p for p in pw.check(added, "Kapalıçarşı'da kalabalığın içinde yürüyor."))
    assert pw.CROWD_RE.search("fair-haired woman") is None
    assert "ONLY when the user's scene has a crowd" in pw.DIRECTION_RULES
