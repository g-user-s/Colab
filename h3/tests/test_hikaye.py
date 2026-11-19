"""Uzun video: hikâye kartı denetimi, dünya çapası, Gemini'siz plan ve süreklilik izlemesi (taklit istemciyle)."""

import os

from h3app import config, hikaye, prompt_writer as pw, review, uzun


def test_kart_denetimi_eksik_repligi_ve_sureyi_yakalar():
    kart = hikaye.ornek_kart('"Birinci."', 24)
    assert hikaye.kart_denetle(kart, 24, '"Birinci."') == []
    assert hikaye.kart_denetle(kart, 24, 'A "Birinci." B "İkinci."') == ['Fikirdeki şu metin kartta yok: "İkinci."']
    kart["bloklar"][0]["sure"] = 20
    sorunlar = hikaye.kart_denetle(kart, 24, "")
    assert any("4–15" in s for s in sorunlar) and any("toplamı" in s for s in sorunlar)


def test_konusmaci_sirasi_ve_uzun_replik():
    kart = hikaye.ornek_kart('"Merhaba."', 20)
    kart["karakterler"][0]["konusmaci"] = "S2"
    kart["bloklar"][1]["replikler"] = [{"konusmaci": "S2", "metin": " ".join(["kelime"] * 40)}]
    sorunlar = hikaye.kart_denetle(kart, 20, "")
    assert any("S1, S2" in s for s in sorunlar) and any("uzun" in s for s in sorunlar)


def test_gorsel_sirasi_konusmacilarla_eslesir(tmp_path):
    kart = hikaye.ornek_kart('"A."', 20)
    kart["karakterler"] = [
        {"id": "K1", "ad": "Sessiz", "konusmaci": "", "gorunum": "x", "kiyafet": "y"},
        {"id": "K2", "ad": "İkinci", "konusmaci": "S2", "gorunum": "x", "kiyafet": "y", "ses": "z"},
        {"id": "K3", "ad": "Birinci", "konusmaci": "S1", "gorunum": "x", "kiyafet": "y", "ses": "z"},
    ]
    liste = hikaye.gorsel_listesi(kart, str(tmp_path))
    assert [g["id"] for g in liste] == ["K3", "K2", "K1", "MEKAN"]
    roller = pw.normalize_roles([{"role": g["rol"]} for g in liste], len(liste))
    assert [r["char"] for r in roller] == [1, 2, 3, None]   # S1 → Karakter 1, S2 → Karakter 2


def test_ornek_plan_iki_kolda_ayni_capa(tmp_path):
    kart = hikaye.ornek_kart('"Çaylar taze." "Afiyet olsun."', 30)
    gorseller = hikaye.gorsel_listesi(kart, str(tmp_path))
    plan, kollar, sorunlar = hikaye.ornek_planla(kart, hikaye.KOLLAR, gorseller)
    assert sorunlar == [] and set(kollar) == {"metin", "ref"}
    capa = hikaye.dunya_capasi(kart)
    assert plan["world_anchor"] == capa and "warm deep voice" in capa
    assert all(capa in b["istek"] for k in kollar.values() for b in k)
    assert [b["sure"] for b in kollar["ref"]] == [15, 15]


def test_gorsel_metni_stile_gore():
    kart = hikaye.ornek_kart('"A."', 20)
    assert "Photorealistic" in hikaye.gorsel_metni(kart, "K1", "real")
    anime = hikaye.gorsel_metni(kart, "MEKAN", "anime")
    assert config.STYLES["anime"]["look"] in anime and "No people" in anime


def test_blok_kesmeleri():
    assert uzun.block_cuts([{"sure": 15}, {"sure": 15}, {"sure": 10}]) == [15.08, 30.17]


def test_sureklilik_izleme_puanlari(monkeypatch, tmp_path):
    class Yanit:
        text = '{"kimlik": 8, "kiyafet": 12, "mekan": 7, "ses": 5, "hikaye": 9, "ozet": "ok"}'

    class Istemci:
        class models:
            @staticmethod
            def generate_content(model, contents, config):
                assert "joined at" in config.system_instruction and "15.08" in config.system_instruction
                return Yanit()

    monkeypatch.setattr(pw, "_client", lambda *a, **k: Istemci())
    monkeypatch.setattr(review, "_proxy", lambda path, d: path)
    video = tmp_path / "v.mp4"
    video.write_bytes(b"0")
    s = review.continuity_review(str(video), [15.08], {"baslik": "x"}, "anahtar")
    assert s["kiyafet"] == 10 and s["ortalama"] == 7.8 and s["sorunlar"] == [] and s["model"]


def test_kopru_istegi_ilk_saniyeleri_korur():
    metin = hikaye.kopru_istegi("Block 2 (15 seconds total, 2 shot(s)).", 4)
    assert metin.startswith("Block 2") and "<Picture 4>" in metin and "1.5 seconds" in metin
