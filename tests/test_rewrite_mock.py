"""Gemini çağrısı sahte bir istemciyle: ilk yanıt metni bozarsa ikinci turda düzeltilmiş hali alınır."""

import os
import sys
import types as pytypes

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from h3app import prompt_writer  # noqa: E402
from tests.test_core import TEST2_PROMPT, TEST2_REQUEST  # noqa: E402


class FakeModels:
    def __init__(self, answers):
        self.answers, self.calls = list(answers), []

    def generate_content(self, model, contents, config):
        self.calls.append((model, contents[0] if isinstance(contents, list) else contents, config.system_instruction))
        return pytypes.SimpleNamespace(text=self.answers.pop(0))

    def generate_content_stream(self, model, contents, config):
        yield pytypes.SimpleNamespace(text=self.generate_content(model, contents, config).text)

    def list(self):
        mk = lambda n, a: pytypes.SimpleNamespace(name="models/" + n, supported_actions=a)
        return [mk("gemini-2.5-flash", ["generateContent"]), mk("gemini-3.0-pro", ["generateContent"]),
                mk("gemini-3.0-flash", ["generateContent"]), mk("gemini-3.0-pro-tts", ["generateContent"]),
                mk("gemini-pro-latest", ["generateContent"]), mk("gemini-3-pro-image", ["generateContent"]),
                mk("gemini-3.8-flash", ["generateContent"]),
                mk("text-embedding-4", ["embedContent"])]


def install(monkeypatch, answers, tmp_path):
    fake = FakeModels(answers)
    from google import genai
    monkeypatch.setattr(genai, "Client", lambda api_key, **kw: pytypes.SimpleNamespace(models=fake))
    monkeypatch.setattr(prompt_writer.config, "CACHE_DIR", str(tmp_path))
    return fake


def test_retry_fixes_broken_turkish(monkeypatch, tmp_path):
    bad = "```\n" + TEST2_PROMPT.replace("ÇAY 15 TL", "CAY 15 TL") + "\n```"
    fake = install(monkeypatch, [bad, TEST2_PROMPT], tmp_path)
    prompt, problems = prompt_writer.rewrite(TEST2_REQUEST, 15, "k", "gemini-x", log=lambda m: None)
    assert problems == [] and prompt == TEST2_PROMPT
    assert len(fake.calls) == 2 and "ÇAY 15 TL" in fake.calls[1][1]
    assert "15 seconds" in fake.calls[0][2]


def test_model_order(monkeypatch, tmp_path):
    install(monkeypatch, [], tmp_path)
    monkeypatch.setattr(prompt_writer.config, "GEMINI_MODEL", "gemini-3.8-flash")
    assert prompt_writer.gemini_models("k") == ["gemini-3.8-flash", "gemini-pro-latest", "gemini-3.0-pro", "gemini-3.0-flash", "gemini-2.5-flash"]


def test_ref_mode_sends_image_and_checks_pictures(monkeypatch, tmp_path):
    img = tmp_path / "kadin.png"
    img.write_bytes(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "referans.png"), "rb").read())
    good = "\n\n".join(f + " the woman of <Picture 1>" for f in prompt_writer.REF_FIELDS)
    fake = install(monkeypatch, ["subject_definitions: no picture label", good], tmp_path)
    prompt, problems = prompt_writer.rewrite("a woman in a red coat", 15, "k", "m", [str(img)], log=lambda m: None)
    assert problems == [] and prompt == good and len(fake.calls) == 2
    assert "full-reference mode" in fake.calls[0][2]


def test_expand_writes_brief_without_google_search(monkeypatch, tmp_path):
    fake = install(monkeypatch, ["brief with carpets"], tmp_path)
    configs, orig = [], fake.generate_content

    def gen(model, contents, config):
        configs.append(config)
        return orig(model, contents, config)
    fake.generate_content = gen
    assert prompt_writer.expand("Kapalıçarşı'da bir kadın", 15, "k", "gemini-3.8-flash", log=lambda m: None) == "brief with carpets"
    assert len(configs) == 1 and not configs[0].tools and "Google Search" not in configs[0].system_instruction


def test_plan_shots_and_rewrite_blocks(monkeypatch, tmp_path):
    import json
    good_plan = {
        "world_anchor": "A woman in a red wool coat and silver scarf with flat boots in the vaulted Grand Bazaar.",
        "shots": [
            {"block": 1, "shot": 1, "start_sec": 0.0, "duration": 7.0, "framing": "Wide full-body shot",
             "action": "She walks through the bazaar.", "camera": "Steadicam backward", "sound": 'Vendor calls "Buyrun!"'},
            {"block": 1, "shot": 2, "start_sec": 7.0, "duration": 8.0, "framing": "Medium tracking shot",
             "action": "She passes lanterns and ends with a calm 0.5s hold.", "camera": "50mm pan", "sound": "Crowd murmur"},
            {"block": 2, "shot": 1, "start_sec": 0.0, "duration": 6.0, "framing": "Close-up reaction shot",
             "action": "She looks at carpets.", "camera": "50mm shallow DOF", "sound": "Quiet footsteps"},
            {"block": 2, "shot": 2, "start_sec": 6.0, "duration": 9.0, "framing": "Wide establishing shot",
             "action": "She stands calmly by an arch and holds for 0.5s.", "camera": "28mm slow pull-back", "sound": "Tea glass clink"},
        ],
    }
    # İlk yanıtta bozuk JSON dönerse ikinci turda düzeltir
    fake = install(monkeypatch, ["not valid json", "```json\n" + json.dumps(good_plan, ensure_ascii=False) + "\n```"], tmp_path)
    plan, probs = prompt_writer.plan_shots('Kapalıçarşı\'da "Buyrun!" sesiyle yürüyen kadın', 30, "k", "m", log=lambda m: None)
    assert probs == [] and plan["world_anchor"] == good_plan["world_anchor"]
    blocks = prompt_writer.blocks_from_plan(plan)
    assert len(blocks) == 2 and blocks[0]["seconds"] == 15 and blocks[1]["seconds"] == 15
    req1 = prompt_writer.block_request(blocks[0], idea='Kapalıçarşı\'da "Buyrun!"')
    assert "At 00:07.000" in req1 and "calm ~0.5-second hold" in req1 and good_plan["world_anchor"] in req1

    # Müzikli konuşmasız modda <d> yakalanır ve ikinci denemede düzeltilir
    plan["shots"][0]["sound"] = "Footsteps on stone"
    bad_music_p = "integrated_multimodal_description: [Shot 1] <d>[Turkish] Merhaba</d>\n\noverall_soundscape: voices\n\nnon_diegetic_music: N/A"
    good_music_p = ("integrated_multimodal_description: [Shot 1] She walks.\n\n"
                    "overall_soundscape: ambient sound only, no voices, no speech, no singing.\n\nnon_diegetic_music: N/A")
    fake2 = install(monkeypatch, [bad_music_p, good_music_p, good_music_p], tmp_path)
    out = prompt_writer.rewrite_blocks(plan, "k", "m", audio_mode="music", log=lambda m: None)
    assert len(out) == 2 and out[0]["problems"] == [] and "no voices" in out[0]["prompt"]
    assert len(fake2.calls) == 3

