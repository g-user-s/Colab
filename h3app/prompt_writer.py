"""Gemini ile iki adım: (1) kısa fikir → detaylı yönetmen brief'i, (2) brief → MiniMax-H3 prompt'u.

Kural kaynağı H3'ün resmi `h3-prompt-writing` skill'idir (SKILL.md + references/base-en.txt ve
references/ref-en.txt); dosyalar MiniMax'in GitHub deposundan sabit commit ile indirilir ve git blob sha
ile doğrulanır. Referans görsel verilirse (Ref2VA) görseller Gemini'ye de gönderilir; prompt resmi altı
bölümlü yapıyla yazılır ve görseller <Picture 1>, <Picture 2>… olarak anılır.
Çıktı denetlenir: bölümler eksiksiz ve sıralı mı, kullanıcının tırnak içindeki her metni (ekran yazısı,
diyalog) harfi harfine korunmuş mu, her görsel anılmış mı. Sorun varsa Gemini'ye bir kez daha sorulur.
"""

import hashlib
import json
import mimetypes
import math
import os
import re
import time
import urllib.request

from . import config

EXAMPLE_INPUT = 'Turkish dialogue, lip sync and acting. A two-person medium shot inside a small traditional Turkish tea house in Cappadocia at dusk. An old man with a white moustache sits across from a young woman, steam rising from tulip tea glasses between them. He says in Turkish, in a warm gravelly voice, "Kızım, dünya çok hızlı dönüyor, bazen durup bakmak lazım." She smiles, nods and answers in Turkish, softly, "Haklısın dede, ama durunca da hep bir şey kaçırıyormuşum gibi hissediyorum." He chuckles and replies, "Kaçıran sensin, bakan değil." Perfect lip sync, natural micro expressions, eyes follow each speaker, hands stay stable around the glasses. Camera: 50mm, shallow depth of field, slow push-in then a gentle shift of focus between faces. Lighting: golden window light with warm lantern fill, soft rim light. Color palette: terracotta, amber, deep teal. Sound: clear synchronized Turkish speech, glass clinks, distant street ambience, soft saz-free ambient room tone. Photoreal cinematic drama.'

EXAMPLE_OUTPUT = "integrated_multimodal_description: [Shot 1] Live-action, photoreal cinematic drama shot on a 50mm lens with shallow depth of field: a two-person medium shot inside a small traditional Turkish tea house in Cappadocia at dusk. On the left an old Turkish man in his seventies with a thick white moustache, weathered tanned skin and a dark wool flat cap sits at a low wooden table; on the right, facing him, a young Turkish woman in her mid-twenties with dark hair tied back and a mustard knitted cardigan. Between them on the table stand two tulip-shaped tea glasses of deep red tea on small saucers, thin steam rising from both. Golden light falls through a deep-teal window frame behind them, a hanging copper lantern adds warm fill, and a soft rim light outlines both faces against terracotta plaster walls and amber kilim cushions. The camera pushes in with small amplitude at slow speed during the first seconds, then settles. The old man with a warm, deep, gravelly voice and a slow speaking rate (S1) looks at her, both hands resting around his tea glass, and says: <d>[Turkish] Kızım, dünya çok hızlı dönüyor, bazen durup bakmak lazım.</d> While he speaks she watches his face. At about 4.5 seconds the focus gently shifts from his face to hers. The young woman with a soft, clear, gentle voice (S2) smiles, nods once, and answers: <d>[Turkish] Haklısın dede, ama durunca da hep bir şey kaçırıyormuşum gibi hissediyorum.</d> While she speaks his eyes stay on her. At about 10.5 seconds the focus gently shifts back to the old man, who chuckles softly, his moustache lifting, and the old man (S1) replies: <d>[Turkish] Kaçıran sensin, bakan değil.</d> She lowers her eyes to her tea glass and smiles. Each speaker's lips move in exact sync with every syllable, with natural micro-expressions and blinks; their eyes follow whoever is speaking; both pairs of hands stay steady around the tea glasses throughout.\n\noverall_soundscape: Quiet room tone of a small stone tea house with a faint hiss from the lantern, the soft clink of a tea glass touching its saucer, a short warm chuckle, and distant street ambience of footsteps and a faraway car through the window.\n\nnon_diegetic_music: N/A"

# Brief örnekleri: kısa fikir → kullanıcının kendi yazdığı detaylı brief (Test 1 ve Test 2)
BRIEF_EXAMPLES = [
    ('Kapadokya\'da bir çay evinde akşamüstü yaşlı bir dede ile genç bir kadın Türkçe sohbet ediyor. Dede: "Kızım, dünya çok hızlı dönüyor, bazen durup bakmak lazım." Kadın gülümseyip: "Haklısın dede, ama durunca da hep bir şey kaçırıyormuşum gibi hissediyorum." Dede gülerek: "Kaçıran sensin, bakan değil." Dudak senkronu kusursuz olsun, sinematik.', EXAMPLE_INPUT),
    ('Gece yağmurlu bir İstanbul ara sokağı. Çay evinin üstünde kırmızı neon tabela "DUR, BİR BAK!" yazıyor, altında tebeşir menüde "ÇAY 15 TL". Trençkotlu bir adam tabelanın altından geçiyor. Yazılar 15 saniye boyunca hiç bozulmasın.', 'Typography and Turkish text rendering. A rainy Istanbul back street at night, a hand-painted neon sign above a tea house reads exactly "DUR, BİR BAK!" in glowing red letters, flickering once, reflected perfectly and mirrored in the wet cobblestones. Below it a smaller chalkboard menu reads "ÇAY 15 TL" in white chalk handwriting. A man in a trench coat walks under the sign, the rain drops catch the neon light, and the camera slowly pushes in then racks focus from the sign to his face. Text must remain perfectly legible, spelled correctly with the Turkish characters İ and Ç intact, stable and consistent across all 15 seconds with no morphing letters. Lighting: neon red and teal practicals, wet asphalt reflections, volumetric steam from the tea house. Anamorphic lens, 35mm grain, cinematic photoreal. Sound: rain, distant call to prayer, neon buzz, low synth hum.'),
    # Test 3: kullanıcının asıl istediği (referans videoyu bu yazı üretti); ses satırı geri bildirime göre yumuşatıldı
    ('Kapalıçarşı\'da öğle vakti, kırmızı paltolu ve gümüş atkılı bir kadın kalabalığın içinde yürüyor; kamera steadicam ile önünde geri geri gidiyor. Etrafta bağıran esnaflar, fotoğraf çeken turistler, çay tepsisi taşıyan bir çocuk, baharat arabası iten bir adam ve bacakların arasından koşan bir kedi var. İnsanlar önünden geçse de kadının yüzü, saçı ve kıyafeti 15 saniye boyunca hiç değişmesin; arka plandaki yüzler de bozulmasın. Fotogerçekçi, sinematik.', 'Crowd density and identity consistency. A continuous steadicam tracking shot walking backwards in front of a woman in a red coat as she moves through the packed Grand Bazaar in Istanbul at midday, framed wide and full-body from head to feet with the shops visible on both sides; she looks ahead where she is going, not into the lens. Dozens of distinct extras around her: merchants calling out, tourists with cameras, a boy carrying a tea tray, a man pushing a cart of spices, a cat darting between legs. Her face, hair, red coat and silver scarf stay perfectly consistent for the entire 15 seconds, even when people pass between her and the camera. Faces of background people stay stable and do not morph. Lantern light, hanging carpets, copper pots, drifting dust in shafts of sunlight from the vaulted ceiling. Camera: 28mm lens, f/2.8, smooth steadicam, natural motion blur at 180 degree shutter. Color palette: saturated reds, warm ochre, turquoise tiles. Sound: layered crowd murmur as the dominant layer, background bargaining in Turkish between a carpet seller and a customer ("Bu halı kaça?" "Sana özel, bin beş yüz lira abla."), a vendor calling "Buyrun, bakmak bedava!", tea glasses clinking, soft footsteps of flat boots buried under the crowd. Photoreal cinematic.'),
]

T2V_FIELDS = ("integrated_multimodal_description:", "overall_soundscape:", "non_diegetic_music:")
REF_FIELDS = ("subject_definitions:", "summary:", "retention_analysis:", "detailed_description:",
              "overall_soundscape:", "non_diegetic_music:")

# Varsayılan yönetmenlik kuralları (Test 3 geri bildirimi: çok yakın çekim, topuk sesi, pazarlık sesi yok).
# Hem brief hem H3 prompt adımında kullanılır; kullanıcı açıkça başka bir şey istediyse onun dediği geçerlidir.
_FRAMING = """- Framing: keep the user's shot size and lens. When a person walks or is tracked through a place and no
  shot size is given, frame a wide full-body shot (head to feet in frame, about a 28mm lens) with the
  surroundings visible on both sides; do not tighten to a medium shot or close-up. The person looks where
  they are going, not into the lens, and does not pose or smile at the camera."""
_REALISM = """- Realism: a named real place must look like the real place (its architecture, the shops and goods that
  really dominate it, its light and its people), not a generic or touristic version of it. Something the
  user mentions once (a spice cart, a cat) stays one element; it must not take over the whole set."""
_FOOTSTEPS = """- Footsteps: never heels, clicking or tapping steps unless asked. Footwear is flat boots or shoes and
  steps are soft and buried under the ambience."""
_ANIMALS = """- Animals: a cat, dog or other animal moves on the ground (between legs, along the floor, under stalls)
  unless the user asks otherwise; never write that it darts past lanterns or anything hanging in the air."""
_STAGING = """- Staging and hands: say where every visible person stands on screen (left / centre / right, foreground /
  background) and which hand holds what. Describe the first 2 seconds as one clear opening image in which every
  visible person is named and already in place. An object is handed only between two people who are both
  visible, hand to hand, never from outside the frame. The camera never shows a character's point of view and
  no extra hands, arms or people enter the frame unless the user asks for it."""
_SIGNAGE_NONE = ("No readable text, signboards, banners or lettering anywhere in the background; shopfronts are "
                 "identified only by their goods, architectural arches, lanterns and displays, with no written signs.")
_SIGNAGE_ONLY = ("Only the exact quoted sign text appears; no other signs, extra boards or background lettering "
                 "anywhere in the frame.")
_SIGNAGE = f"""- Signage: when the user did not ask for on-screen text in quotes, state explicitly: "{_SIGNAGE_NONE}"
  When the user asked for specific quoted sign text, state explicitly: "{_SIGNAGE_ONLY}\""""
_SPEECH = """- Background speech: when people talk, call out, bargain or chat in a crowd or market, write 2-3 short,
  natural background lines in the local language (Turkish for Turkey) as real dialogue, e.g. a vendor
  and a customer bargaining, heard at a lower level under the ambience; the crowd voices are the dominant
  sound layer, not footsteps."""
_MUSIC_SILENT = ("ambient sound only, no voices, no speech, no singing")
_MUSIC_MODE = f"""- Music montage mode (no speech): do NOT write any spoken dialogue (<d>...</d>), crowd chatter or human
  voices. In overall_soundscape state explicitly "{_MUSIC_SILENT}" along with natural environmental foley,
  and in non_diegetic_music write "N/A" (external music will be mixed later)."""
_DIRECTION_HEAD = "Default direction (use only when the user did not ask for something else):"
DIRECTION_RULES = "\n".join([_DIRECTION_HEAD, _FRAMING, _STAGING, _REALISM, _FOOTSTEPS, _ANIMALS, _SIGNAGE, _SPEECH])

# Gerçek dünya dışındaki stillerde gerçekçilik kuralı: mekân tanınır kalır ama stilde yeniden çizilir
_REALISM_STYLED = """- Real places: a named real place keeps what makes it recognisable (its architecture, the shops and
  goods that really dominate it, its light and its people), redrawn in the chosen style, not photographed.
  Something the user mentions once (a spice cart, a cat) stays one element; it must not take over the whole set.
  Never leave shops or stalls generic ("market stalls"): name what they really sell there and how it is shown
  (e.g. gold jewellery in lit glass vitrines, carpets hanging from the walls), or the model fills every stall
  with spices and sweets."""

STYLE_RULES = """Visual style (chosen by the user; it overrides every "photoreal", "live-action" or "cinematic
photography" wording in the guide and in the examples, which only show the structure):
- The whole video is {look}. The people are {people}. The background and the whole set are {background}.
- Describe the background as art in that style too, not only the people: if only the people are described,
  the model draws them and leaves the sky, water and buildings photographic.
- Nothing may look photographic: it must look like a shot made from scratch in this style, not a filter over
  live footage. Avoid: {avoid}.
- Animated styles drift toward a static chest-up portrait that faces the camera. When a person walks or is
  tracked, write the framing in the shot itself and repeat it later: a wide full-body shot, head to feet in
  frame with the floor visible, the person walking and looking along their path, never posing for the lens.
- Open the first description section with one sentence that names this style (in place of "Live-action,
  photoreal ..."), and keep lighting, palette and lens choices that suit the style."""

STYLE_REF_RULE = """- Reference pictures give the identity only: the person keeps a recognisable face shape, hair, skin
  tone and colours, but is drawn as one of the {people}, never as a photographed person. When a reference picture
  already shows the character in the chosen style with distinctive clothing, hat, eyewear/goggles, props or setting
  (e.g. a jungle) and the user does not ask for different ones, preserve that exact character design, outfit,
  accessories and environment across all shots."""


def signage_rule(request=""):
    """Kullanıcı tırnak içinde yazı istediyse yalnızca o tabelaya izin verir; istemediyse arka plan yazılarını yasaklar."""
    return _SIGNAGE_ONLY if literals(request) else _SIGNAGE_NONE


def direction_rules(style=config.DEFAULT_STYLE, n_images=0, audio_mode=config.DEFAULT_AUDIO_MODE):
    """Stil kuralları + varsayılan yönetmenlik kuralları. "real" + "speech" için bugünkü DIRECTION_RULES aynen döner."""
    s = config.STYLES.get(style) or config.STYLES[config.DEFAULT_STYLE]
    sound_rule = _MUSIC_MODE if audio_mode == "music" else _SPEECH
    if "look" not in s:
        if audio_mode == config.DEFAULT_AUDIO_MODE:
            return DIRECTION_RULES
        return "\n".join([_DIRECTION_HEAD, _FRAMING, _STAGING, _REALISM, _FOOTSTEPS, _ANIMALS, _SIGNAGE, sound_rule])
    rules = STYLE_RULES.format(**s) + ("\n" + STYLE_REF_RULE.format(**s) if n_images else "")
    return rules + "\n\n" + "\n".join([_DIRECTION_HEAD, _FRAMING, _STAGING, _REALISM_STYLED, _FOOTSTEPS, _ANIMALS,
                                        _SIGNAGE, sound_rule])


COMMON_RULES = """Hard rules:
- Output ONLY the final prompt sections, in the required order, each starting on its own line with its
  field name, separated by one blank line. No title, no explanation, no markdown, no code fences.
- Write the sections in English, but copy every piece of on-screen text and every spoken line from the
  user's request character for character in its original language. Keep Turkish letters exactly
  (İ ı Ş ş Ğ ğ Ç ç Ö ö Ü ü) and keep the original punctuation.
- On-screen text goes in English double quotes, e.g. a neon sign that reads "DUR, BİR BAK!".
  When the user asks for legible or stable text, say explicitly that the text stays exactly spelled,
  legible and stable for the whole video with no morphing letters, no extra words and no subtitles.
- Dialogue uses speaker IDs (S1), (S2)... and <d>[Language] exact words</d>, e.g. <d>[Turkish] ...</d>.
- The whole timeline must fit the requested duration of {seconds} seconds; use "At about N seconds"
  for timed events inside a single shot, or [Shot N] with "At 00:SS.000" for cuts.
- Prefer concrete visual and audio details. Keep every requirement of the user (camera, lens,
  lighting, palette, sound, consistency) and do not add music when the user did not ask for any
  (then write non_diegetic_music: N/A).
- Background lines you add yourself also use speaker IDs and <d>[Turkish] ...</d>; say they come from
  background speakers at a lower volume.

{direction}"""

T2V_TEMPLATE = """You rewrite a user's video request into a prompt for the MiniMax H3 video+audio model.
Follow the official H3 prompt-writing guide below exactly. The task mode is T2VA (text only, no
reference pictures), so the prompt starts directly with the three core fields
integrated_multimodal_description, overall_soundscape, non_diegetic_music.

{rules}

===== OFFICIAL GUIDE: SKILL.md =====
{skill}

===== OFFICIAL GUIDE: references/base-en.txt =====
{guide}

===== WORKED EXAMPLE (14-second request) =====
User request:
{example_in}

Final prompt:
{example_out}
"""

REF_TEMPLATE = """You rewrite a user's video request into a prompt for the MiniMax H3 video+audio model in
full-reference mode (Ref2VA). The user attached {n} reference picture(s); they are given to you in
order and are called <Picture 1> ... <Picture {n}>. Follow the official full-reference guide below
exactly and write the six sections subject_definitions, summary, retention_analysis,
detailed_description, overall_soundscape, non_diegetic_music.

Additional rules for reference pictures:
- Look at every picture carefully. In subject_definitions, define the person or object of each picture
  as a <Subject N> with "Reference role: identity anchor" (for a person) and list the visible features
  to follow exactly: face shape, eyes, eyebrows, facial marks/scars, nose, lips, skin tone, hair colour,
  length and style, approximate age, and—when the user's request does not ask for different clothing or
  setting—their exact outfit, hat, eyewear/goggles, props and scene environment from <Picture N>.
  Mention every <Picture N> at least once.
- Clothing, props and setting come from the user's request when they differ from the picture (then say that
  only the identity is taken from the picture and that its clothing/background is not carried over); when
  the user's request does not specify different clothing or setting, preserve the exact outfit, accessories
  and environment shown in <Picture N> and anchor the opening shot to <Picture N>.
- In detailed_description keep the referenced identity and outfit consistent in every moment, including when
  other people or obstacles pass in front of the subject.
- When a picture is labelled with a role, follow it exactly (the rules above about people apply to characters):
  * character N: a person; define them as a <Subject> with "Reference role: identity anchor"; when they speak,
    use speaker ID (SN) and keep the given name.
  * scene/background: define it as an environment <Subject> with "Reference role: scene anchor"; reproduce its
    architecture, layout, materials, colour palette and light; all characters act inside this place; never
    create a person from this picture and never use it as an identity anchor.
  * object/prop: define it as an object <Subject> with "Reference role: prop reference"; keep its exact shape,
    colours and markings, and show it being used as the request describes.

{rules}

===== OFFICIAL GUIDE: SKILL.md =====
{skill}

===== OFFICIAL GUIDE: references/ref-en.txt =====
{guide}
"""

BRIEF_TEMPLATE = """You are a film director's assistant. Turn a short video idea into a detailed, vivid
one-paragraph brief for an AI video model, like the examples below: setting and time of day, subjects and
their look, action beat by beat, camera (shot type, lens, movement), lighting, colour palette, sound, style,
and any consistency requirements (text that must stay legible, faces that must not morph...).
Rules: write in English; keep every quoted text and spoken line from the idea exactly as written
(same language, same letters, same punctuation) inside double quotes; keep the idea's intent and
do not add story elements that contradict it; the video lasts {seconds} seconds; output only the brief.{ref_note}
For a real, named place, describe it as it really looks (its architecture, the shops and goods that really
fill it, its light, people and sounds) from your own knowledge. Props the idea mentions (a spice cart, a tea
tray) are added as single moving elements, not as the shops around the subject.

{direction}

{examples}"""


_GUIDE_BYTES = {}


def _git_blob_sha(data):
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def load_guide(cache_dir=None):
    """{dosya adı: metin}: SKILL.md, base-en.txt, ref-en.txt (ilk kullanımda indirilir ve doğrulanır)."""
    cache_dir = cache_dir or config.CACHE_DIR
    os.makedirs(cache_dir, exist_ok=True)
    texts = {}
    for path, sha in config.SKILL_FILES.items():
        local = os.path.join(cache_dir, sha)
        if os.path.isfile(local):
            data = open(local, "rb").read()
        elif sha in _GUIDE_BYTES:
            data = _GUIDE_BYTES[sha]
        else:
            url = f"https://raw.githubusercontent.com/{config.SKILL_REPO}/{config.SKILL_COMMIT}/{path}"
            data = urllib.request.urlopen(url, timeout=60).read()
        if _git_blob_sha(data) != sha:
            raise RuntimeError(f"Skill dosyası doğrulanamadı: {path}")
        _GUIDE_BYTES[sha] = data
        open(local, "wb").write(data)
        texts[os.path.basename(path)] = data.decode("utf-8")
    return texts


def system_prompt(seconds, guides, n_images=0, style=config.DEFAULT_STYLE, audio_mode=config.DEFAULT_AUDIO_MODE):
    rules = COMMON_RULES.format(seconds=seconds, direction=direction_rules(style, n_images, audio_mode))
    if n_images:
        return REF_TEMPLATE.format(n=n_images, rules=rules, skill=guides["SKILL.md"].strip(),
                                   guide=guides["ref-en.txt"].strip())
    return T2V_TEMPLATE.format(rules=rules, skill=guides["SKILL.md"].strip(), guide=guides["base-en.txt"].strip(),
                               example_in=EXAMPLE_INPUT, example_out=EXAMPLE_OUTPUT)


def brief_prompt(seconds, n_images=0, style=config.DEFAULT_STYLE, audio_mode=config.DEFAULT_AUDIO_MODE):
    examples = "\n\n".join(f"Example idea:\n{a}\n\nExample brief:\n{b}" for a, b in BRIEF_EXAMPLES)
    note = ("" if not n_images else
            f"\nThe user also attached {n_images} reference picture(s) (Picture 1 ... Picture {n_images}); refer to the "
            "person in them as \"the woman/man from reference picture N\" and do not describe a different face. "
            "Pictures may be labelled with a role: a scene/background picture is the setting (describe that place, "
            "never a person from it) and an object picture is a prop.")
    return BRIEF_TEMPLATE.format(seconds=seconds, ref_note=note, direction=direction_rules(style, n_images, audio_mode),
                                 examples=examples)


QUOTE_RE = re.compile(r'"([^"]+)"|\u201c([^\u201d]+)\u201d')
CUT_SPLIT_RE = re.compile(r"\[\s*cut\s*\]", re.I)
AUDIO_LINE_RE = re.compile(r"(?:^|\n)\s*Audio\s*:\s*(.+)$", re.I | re.S)


def _norm_quotes(text):
    """Kıvrık kesme ve tırnak işaretlerini (’ ‘ “ ”) ASCII karşılıklarına normalize eder."""
    return (text or "").replace("\u2018", "'").replace("\u2019", "'").replace("\u02bc", "'").replace("\u201c", '"').replace("\u201d", '"')


def literals(text):
    """Kullanıcı metnindeki tırnak içi her ifade (ekran yazısı, diyalog)."""
    return [a or b for a, b in QUOTE_RE.findall(text or "")]


def split_user_cuts(text):
    """Kullanıcı metninde `[cut]` varsa (çekim_listesi, genel_ses_notu) döner; yoksa ([], '')."""
    raw = (text or "").strip()
    if not CUT_SPLIT_RE.search(raw):
        return [], ""
    audio_note = ""
    m_aud = AUDIO_LINE_RE.search(raw)
    if m_aud:
        audio_note = m_aud.group(1).strip()
        raw = raw[:m_aud.start()].strip()
    parts = [p.strip() for p in CUT_SPLIT_RE.split(raw) if p and p.strip()]
    return (parts if len(parts) >= 2 else []), audio_note


def clean(text):
    text = (text or "").strip()
    return re.sub(r"^```[a-zA-Z]*\n|\n```$", "", text).strip()


def check(prompt, request, n_images=0, style=config.DEFAULT_STYLE, audio_mode=config.DEFAULT_AUDIO_MODE, roles=None):
    """Prompt'taki sorunların listesi; boş liste kullanılabilir demektir."""
    fields = REF_FIELDS if n_images else T2V_FIELDS
    problems = []
    pos = [prompt.find(f) for f in fields]
    if not prompt.startswith(fields[0]):
        problems.append(f"Prompt '{fields[0]}' ile başlamalı.")
    if any(p < 0 for p in pos):
        problems.append("Eksik bölüm: " + ", ".join(f for f, p in zip(fields, pos) if p < 0))
    elif pos != sorted(pos):
        problems.append("Bölümlerin sırası yanlış.")
    norm_prompt = _norm_quotes(prompt)
    for lit in literals(request):
        if lit.strip() and _norm_quotes(lit.strip()) not in norm_prompt:
            problems.append(f'Şu metin harfi harfine korunmamış: "{lit.strip()}"')
    for i in range(1, n_images + 1):
        if f"<Picture {i}>" not in prompt:
            problems.append(f"<Picture {i}> prompt'ta hiç anılmıyor.")
    if roles and n_images:
        defs = prompt[:prompt.find("summary:")] if "summary:" in prompt else prompt
        for i, spec in enumerate(normalize_roles(roles, n_images), 1):
            if spec["role"] == ROLE_CHARACTER:
                continue
            lines = [ln for ln in defs.splitlines() if f"<Picture {i}>" in ln]
            if any(re.search(r"identity anchor", ln, re.I) for ln in lines):
                kind = "arka plan/mekân" if spec["role"] == ROLE_SCENE else "nesne"
                problems.append(f"<Picture {i}> bir {kind} görseli ama kişi gibi 'identity anchor' olarak tanımlanmış; "
                                f"{'scene anchor' if spec['role'] == ROLE_SCENE else 'prop reference'} olmalı.")
    pov = re.compile(r"\b(point[- ]of[- ]view|POV|first[- ]person|from (?:his|her|their) (?:eyes|perspective))\b", re.I)
    if pov.search(prompt) and not re.search(pov.pattern + r"|bakış açısı|gözünden|birinci şahıs", request or "", re.I):
        problems.append("Kullanıcı istemediği halde bakış açısı (POV) çekimi yazılmış; kamera hiçbir karakterin gözünden "
                        "bakmamalı, kadraja fazladan el girmemeli.")
    if re.search(r"\bheel", prompt, re.I) and not re.search(r"\bheel|topuk", request, re.I):
        problems.append("Kullanıcı istemediği halde topuklu ayakkabı / topuk sesi yazılmış; düz bot ve yumuşak adım sesi kullan.")
    if not literals(request) and not re.search(
            r"\b(sign\w*|banner\w*|board\w*|text|letter\w*|neon|menu|chalkboard|tabela\w*|yazı\w*|afiş\w*|pano\w*|menü\w*)\b",
            request or "", re.I):
        signs = [m.group(0) for m in re.finditer(
            r"\b(?:(?:shop(?:front)?|storefront|neon|wooden|hanging)\s+signs?\b|"
            r"(?:sign(?:board)?s?|banners?|boards?|plaques?|placards?)\s+(?:that\s+)?(?:reads?|reading|with\s+(?:text|lettering|words)|bearing|displaying|saying|inscribed))",
            prompt, re.I)
            if not re.search(r"\b(no|not|non|without|avoid\w*|never|zero|free\s+of)\b[^.;:]{0,50}$",
                             prompt[max(0, m.start() - 60):m.start()], re.I)]
        if signs:
            problems.append(f"Kullanıcı yazı/tabela istemediği halde arka planda tabela veya yazı tarif edilmiş ({signs[0]}); "
                            f'kaldır ve "{_SIGNAGE_NONE}" kuralını uygula.')
    if audio_mode == "music":
        if "<d>" in prompt or "</d>" in prompt:
            problems.append("Müzikli konuşmasız modda konuşma (<d>...</d>) yazılmamalı; kaldır.")
        if "no voices" not in prompt.lower() and "no speech" not in prompt.lower():
            problems.append(f'Müzikli konuşmasız modda overall_soundscape içinde "{_MUSIC_SILENT}" belirtilmeli.')
    s = config.STYLES.get(style) or {}
    if s.get("keywords"):
        if not any(k in prompt.lower() for k in s["keywords"]):
            problems.append(f"Seçilen stil ({s['label']}) prompt'ta yok; ilk açıklama cümlesinde stili tarif et: {s['look']}.")
        # "no photorealism", "avoid live-action" gibi olumsuz kullanımlar serbest
        photo = [m.group(0) for m in re.finditer(r"photoreal\w*|live[- ]action", prompt, re.I)
                 if not re.search(r"\b(no|not|non|without|avoid\w*|never|instead of)\b[^.;:]{0,40}$",
                                  prompt[max(0, m.start() - 60):m.start()], re.I)]
        if photo and not re.search(r"photoreal|live.action|gerçekçi", request, re.I):
            problems.append(f"{s['label']} stili seçiliyken fotoğraf gerçekçiliği yazılmış ({photo[0]}); "
                            "kaldır, gerekirse yalnızca 'no photorealism' biçiminde yaz.")
    if "```" in prompt:
        problems.append("Kod bloğu işareti var.")
    return problems


def gemini_models(api_key):
    """Anahtarın kullanabildiği Gemini metin modelleri: en yeni önce, 'pro' önce."""
    from google import genai
    client = _client(api_key)
    names = []
    for m in client.models.list():
        name = (m.name or "").removeprefix("models/")
        actions = m.supported_actions or []
        if ("generateContent" in actions and name.startswith("gemini")
                and not any(x in name for x in ("tts", "image", "banana", "embedding", "live", "audio", "robotics",
                                                "transcribe", "computer-use", "customtools"))):
            names.append(name)

    def key(n):
        # Önce config.GEMINI_MODEL, sonra "en yeni Pro" takma adı, sonra sürüme göre yeniden eskiye
        ver = re.findall(r"gemini-(\d+(?:\.\d+)?)", n)
        return (n != config.GEMINI_MODEL, n != "gemini-pro-latest", "pro" not in n,
                -(float(ver[0]) if ver else 0), "preview" in n or "exp" in n, n)
    return sorted(set(names), key=key)


ROLE_CHARACTER, ROLE_SCENE, ROLE_OBJECT = "karakter", "arka_plan", "nesne"
ROLES = (ROLE_CHARACTER, ROLE_SCENE, ROLE_OBJECT)


def normalize_roles(roles, n):
    """Her görsel için {'role', 'name', 'char'} listesi (görsel sırasıyla). Rol verilmemişse karakter sayılır;
    karakterler sırayla 1, 2, … numaralanır ve konuşmacı kimliği (S1, S2…) bu numaradır."""
    out, k = [], 0
    for i in range(n):
        r = (roles[i] if roles and i < len(roles) else None) or {}
        role = r.get("role") if r.get("role") in ROLES else ROLE_CHARACTER
        char = None
        if role == ROLE_CHARACTER:
            k += 1
            char = k
        out.append({"role": role, "name": (r.get("name") or "").strip(), "char": char})
    return out


def role_label(spec):
    """Gemini'ye görselin yanında giden kısa rol etiketi (İngilizce)."""
    name = f' "{spec["name"]}"' if spec.get("name") else ""
    if spec["role"] == ROLE_SCENE:
        return f"role: scene/background{name} — the setting, not a person"
    if spec["role"] == ROLE_OBJECT:
        return f"role: object/prop{name}"
    return f"role: character {spec['char']}{name} — speaker S{spec['char']} if they talk"


def _image_parts(images, roles=None):
    from google.genai import types
    parts = []
    specs = normalize_roles(roles, len(images or [])) if roles else None
    for i, path in enumerate(images or [], 1):
        mime = mimetypes.guess_type(path)[0] or "image/png"
        label = f"<Picture {i}> ({role_label(specs[i - 1])}):" if specs else f"<Picture {i}>:"
        parts += [label, types.Part.from_bytes(data=open(path, "rb").read(), mime_type=mime)]
    return parts


class FirstChunkTimeout(TimeoutError):
    """Model ilk metin parçasını FIRST_CHUNK_SECONDS içinde göndermedi."""


TRANSIENT_RE = re.compile(r"\b(503|429|504|500)\b|UNAVAILABLE|RESOURCE_EXHAUSTED|DEADLINE_EXCEEDED|INTERNAL|"
                          r"high demand|overloaded|timed? ?out", re.I)
TEXT_TIMEOUT_MS = 180_000   # ilk parça geldikten sonra tüm yanıt için üst sınır
IMAGE_TIMEOUT_MS = 300_000


def _transient(e):
    return isinstance(e, TimeoutError) or "Timeout" in type(e).__name__ or bool(TRANSIENT_RE.search(str(e)))


def _client(api_key, timeout_ms=TEXT_TIMEOUT_MS):
    from google import genai
    from google.genai import types
    return genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=timeout_ms))


def _stream_text(api_key, model, system, contents, temperature, first_chunk=None, total=TEXT_TIMEOUT_MS / 1000):
    """Yanıtı akış olarak ister. İlk parça `first_chunk` sn içinde gelmezse FirstChunkTimeout; bekleyen istek
    arka planda kendiliğinden biter, sonucu yok sayılır."""
    import queue
    import threading
    from google.genai import types
    first_chunk = config.FIRST_CHUNK_SECONDS if first_chunk is None else first_chunk
    if model.startswith("gemma"):   # Gemma API'de sistem talimatı yok: talimat mesajın başına konur
        cfg = types.GenerateContentConfig(temperature=temperature)
        contents = [f"Instructions:\n{system}\n\n---\n"] + list(contents)
    else:
        cfg = types.GenerateContentConfig(system_instruction=system, temperature=temperature)
    q, done = queue.Queue(), object()

    def work():
        try:
            client = _client(api_key)   # değişkende tutulmalı: geçici istemci çöpe gidince bağlantıyı kapatıyor
            for chunk in client.models.generate_content_stream(model=model, contents=contents, config=cfg):
                q.put(getattr(chunk, "text", None) or "")
        except Exception as e:
            q.put(e)
        finally:
            q.put(done)

    threading.Thread(target=work, daemon=True, name=f"gemini-{model}").start()
    parts, deadline, got_first = [], None, False
    while True:
        try:
            if not got_first:
                item = q.get(timeout=first_chunk)
            else:
                item = q.get(timeout=max(0.1, deadline - time.time()))
        except Exception:
            if not got_first:
                raise FirstChunkTimeout(f"{model} {first_chunk:g} sn içinde yanıt vermeye başlamadı") from None
            raise TimeoutError(f"{model} yanıtı {total:g} sn içinde bitmedi") from None
        if item is done:
            break
        if isinstance(item, Exception):
            raise item
        if not got_first:
            got_first, deadline = True, time.time() + total
        parts.append(item)
    text = "".join(parts)
    if not text.strip():
        raise RuntimeError(f"{model} boş yanıt döndü (503 UNAVAILABLE gibi davranılır)")
    return text


def _generate(api_key, model, system, contents, temperature, log=None):
    """Seçili modelle dener; ilk parça FIRST_CHUNK_SECONDS içinde gelmezse ya da model yoğunsa (503/429/zaman aşımı)
    beklemeden sıradaki yedek modele geçer ve bunu `log` ile arayüze yazar. Kalıcı hatada (ör. geçersiz anahtar) durur."""
    models = list(dict.fromkeys([model, config.GEMINI_MODEL, *config.GEMINI_FALLBACK_MODELS]))
    errors = []
    for i, m in enumerate(models):
        try:
            text = _stream_text(api_key, m, system, contents, temperature)
        except Exception as e:
            if not _transient(e):
                raise
            errors.append(f"{m}: {str(e)[:160]}")
            if log and i + 1 < len(models):
                log(f"⚠️ {m} yanıt vermedi ({str(e)[:120]}); yedek modele geçiliyor: {models[i + 1]}")
            continue
        if i and log:
            log(f"↪️ Bu adım yedek modelle yazıldı: {m}")
        return clean(text)
    raise RuntimeError("Hiçbir Gemini modeli yanıt vermedi:\n- " + "\n- ".join(errors))


def expand(idea, seconds, api_key, model, images=(), log=print, style=config.DEFAULT_STYLE,
           audio_mode=config.DEFAULT_AUDIO_MODE, roles=None):
    """Kısa fikir → detaylı brief (İngilizce, tırnak içi metinler aynen), seçilen stilde."""
    head = f"Duration: {seconds} seconds.\n\nIdea:\n{idea.strip()}"
    contents = [head] + _image_parts(images, roles)
    return _generate(api_key, model, brief_prompt(seconds, len(images or ()), style, audio_mode), contents, 0.7,
                     log=log)


def rewrite(request, seconds, api_key, model, images=(), retries=1, log=print, style=config.DEFAULT_STYLE,
            audio_mode=config.DEFAULT_AUDIO_MODE, roles=None):
    """Brief → H3 prompt'u. (prompt, sorunlar) döner; sorun listesi boşsa tüm denetimlerden geçmiştir."""
    images = list(images or ())
    system = system_prompt(seconds, load_guide(), len(images), style, audio_mode)
    head = f"Duration: {seconds} seconds.\n\nUser request:\n{request.strip()}"
    prompt, problems = "", ["Gemini yanıt vermedi."]
    contents = [head] + _image_parts(images, roles)
    for attempt in range(retries + 1):
        prompt = _generate(api_key, model, system, contents, 0.3, log=log)
        problems = check(prompt, request, len(images), style, audio_mode, roles=roles)
        if not problems:
            break
        log(f"Gemini çıktısında sorun ({attempt + 1}. deneme): " + " | ".join(problems))
        contents = [head + f"\n\nYour previous answer:\n{prompt}\n\nFix these problems and output the full "
                    "corrected prompt only:\n- " + "\n- ".join(problems)] + _image_parts(images, roles)
    return prompt, problems


SHOT_KEYS = ("block", "shot", "start_sec", "duration", "framing", "action", "camera", "sound")

PLAN_SHOTS_PROMPT = """You are a film director and editor planning a {total_seconds}-second multi-shot video for the
MiniMax H3 video+audio model. Because H3 generates at most 15 seconds per block, divide the {total_seconds}
seconds into {n_blocks} block(s) (each block between 4 and 15 seconds, summing to {total_seconds} seconds).
Within each block, plan 2 to 4 shots that cut cleanly at exact timestamps (`[Shot N] At 00:SS.000`).

Output ONLY valid JSON (no markdown fences, no commentary) with this exact structure:
{{
  "world_anchor": "2-4 sentences in English describing the unchanging character identity, garments, colours, footwear (flat boots/shoes), setting architecture, time of day, lighting, colour palette, and signage rule that must stay identical in every block.",
  "shots": [
    {{
      "block": 1,
      "shot": 1,
      "start_sec": 0.0,
      "duration": 5.0,
      "framing": "Wide establishing full-body shot, 28mm lens",
      "action": "Concrete visual action in English...",
      "camera": "Camera movement and focus...",
      "sound": "Spoken dialogue in quotes or ambient sound..."
    }}
  ]
}}

Hard rules for planning:
- `block` is 1..{n_blocks}. Within each block, `shot` starts at 1 and increments (1, 2, 3...), and `start_sec`
  is the start time (in seconds) relative to the start of THAT block (so shot 1 of every block has `start_sec: 0.0`).
- Every shot `duration` must be at least 2.0 seconds. Each block's shot durations must sum to ≤ 15.0 seconds
  (and ≥ 4.0 seconds), and the total across all blocks must equal {total_seconds} seconds.
- Shot variety & 180-degree rule: vary framing across shots (wide establishing full-body shot -> medium tracking
  or two-shot -> close-up reaction or detail shot -> wide/medium resolution) while keeping consistent screen
  direction (180-degree axis).
- Tail-drift protection (CRITICAL): the LAST shot of EVERY block MUST end with a calm ~0.5-second hold or
  settling beat (steady gaze, settled posture, or still camera), never in the middle of a fast turn or sudden
  motion. Block boundaries must always fall on a natural scene cut, never splitting one continuous fast motion.
- Keep every quoted on-screen text and spoken line from the user's idea character for character (with Turkish
  letters İ ı Ş ş Ğ ğ Ç ç Ö ö Ü ü intact) inside the appropriate shot's `action` or `sound`.{ref_note}

{direction}"""


def _parse_json(text):
    text = clean(text)
    m = re.search(r"\{.*\}", text, re.S)
    return json.loads(m.group(0) if m else text)


def check_plan(plan, total_seconds, idea="", audio_mode=config.DEFAULT_AUDIO_MODE):
    """Blok/çekim planını denetler ve start_sec değerlerini blok içinde normalize eder; sorun listesi döner."""
    problems = []
    if not isinstance(plan, dict):
        return ["Plan bir JSON nesnesi olmalı."]
    anchor = (plan.get("world_anchor") or "").strip()
    shots = plan.get("shots")
    if not anchor:
        problems.append("'world_anchor' (ortak karakter/dünya çapası) boş olamaz.")
    if not isinstance(shots, list) or not shots:
        return problems + ["'shots' boş olmayan bir çekim listesi olmalı."]
    by_block = {}
    for idx, s in enumerate(shots, 1):
        if not isinstance(s, dict):
            problems.append(f"{idx}. çekim geçerli bir nesne değil.")
            continue
        missing = [k for k in SHOT_KEYS if k not in s]
        if missing:
            problems.append(f"{idx}. çekimde eksik alan: {', '.join(missing)}")
            continue
        try:
            b = int(s["block"])
            dur = round(float(s["duration"]), 2)
        except Exception:
            problems.append(f"{idx}. çekimde block/duration sayısal değil.")
            continue
        if dur < config.MIN_SHOT_SECONDS:
            problems.append(f"Blok {b} çekim {s.get('shot')}: süre en az {config.MIN_SHOT_SECONDS} sn olmalı ({dur} sn).")
        by_block.setdefault(b, []).append(s)
    if problems:
        return problems
    total = 0.0
    for b in sorted(by_block):
        cur = 0.0
        for j, s in enumerate(by_block[b], 1):
            s["block"] = b
            s["shot"] = j
            s["start_sec"] = round(cur, 2)
            dur = round(float(s["duration"]), 2)
            s["duration"] = dur
            cur += dur
        if cur > config.MAX_SECONDS + 0.05:
            problems.append(f"Blok {b} toplam süresi 15 saniyeyi aşıyor ({cur:.1f} sn); en fazla 15 sn olmalı.")
        elif cur < config.MIN_SECONDS - 0.05:
            problems.append(f"Blok {b} toplam süresi çok kısa ({cur:.1f} sn); en az {config.MIN_SECONDS} sn olmalı.")
        total += cur
    if abs(total - float(total_seconds)) > 0.6:
        problems.append(f"Toplam süre {total_seconds} sn olmalı ama çekimlerin toplamı {total:.1f} sn.")
    user_cuts, _ = split_user_cuts(idea)
    if user_cuts and len(shots) != len(user_cuts):
        problems.append(f"Kullanıcı [cut] ile {len(user_cuts)} çekim verdi ama planda {len(shots)} çekim var; "
                        f"tam {len(user_cuts)} çekim olmalı.")
    all_text = _norm_quotes(json.dumps(plan, ensure_ascii=False))
    for lit in literals(idea):
        if lit.strip() and _norm_quotes(lit.strip()) not in all_text:
            problems.append(f'Şu tırnak içi metin planda korunmamış: "{lit.strip()}"')
    if audio_mode == "music":
        for s in shots:
            if "<d>" in (s.get("sound") or ""):
                problems.append("Müzikli konuşmasız modda çekim sesinde konuşma (<d>...</d>) olmamalı.")
                break
    return problems


def plan_shots(idea, total_seconds, api_key, model, images=(), style=config.DEFAULT_STYLE,
               audio_mode=config.DEFAULT_AUDIO_MODE, retries=1, log=print, roles=None):
    """Kısa fikir + toplam süre → {'world_anchor': ..., 'shots': [...]}. Bozuk JSON veya süre hatasında düzeltir."""
    total_seconds = int(round(float(total_seconds)))
    n_blocks = max(1, math.ceil(total_seconds / float(config.MAX_SECONDS)))
    ref_note = ("" if not images else
                f"\nThe user attached {len(images)} reference picture(s) (<Picture 1> ... <Picture {len(images)}>); "
                "anchor the main character's identity, exact outfit, accessories and scene environment to the reference "
                "picture(s) in `world_anchor`. Pictures labelled scene/background define the place (never a person); "
                "pictures labelled object are props.")
    user_cuts, audio_note = split_user_cuts(idea)
    if user_cuts:
        per_b = math.ceil(len(user_cuts) / float(n_blocks))
        cut_lines = []
        for idx, ctext in enumerate(user_cuts, 1):
            b_idx = min(n_blocks, (idx - 1) // per_b + 1)
            s_idx = (idx - 1) % per_b + 1
            cut_lines.append(f"  - Global Shot {idx} -> Block {b_idx}, Shot {s_idx}: {ctext}")
        ref_note += (
            f"\n\nCRITICAL — Explicit `[cut]` script provided by the user ({len(user_cuts)} total shots across "
            f"{n_blocks} block(s)):\nYou MUST output EXACTLY {len(user_cuts)} shots in the `shots` array in this exact "
            "order and block assignment, preserving every requested camera framing and camera move, every action and every spoken line "
            "verbatim:\n"
            + "\n".join(cut_lines)
        )
        if audio_note:
            ref_note += f"\nGlobal audio note from user (incorporate across shots' `sound` fields): {audio_note}"
    system = PLAN_SHOTS_PROMPT.format(
        total_seconds=total_seconds, n_blocks=n_blocks, ref_note=ref_note,
        direction=direction_rules(style, len(images or ()), audio_mode),
    )
    head = f"Total duration: {total_seconds} seconds ({n_blocks} blocks).\nAudio mode: {audio_mode}.\n\nIdea:\n{idea.strip()}"
    contents = [head] + _image_parts(images, roles)
    plan, problems = {"world_anchor": "", "shots": []}, ["Gemini yanıt vermedi."]
    for attempt in range(retries + 1):
        raw = _generate(api_key, model, system, contents, 0.4, log=log)
        try:
            plan = _parse_json(raw)
            problems = check_plan(plan, total_seconds, idea=idea, audio_mode=audio_mode)
        except Exception as e:
            problems = [f"Geçerli JSON üretilmedi: {e}"]
        if not problems:
            break
        log(f"Plan çıktısında sorun ({attempt + 1}. deneme): " + " | ".join(problems))
        contents = [head + f"\n\nYour previous answer:\n{raw}\n\nFix these problems and output ONLY valid JSON:\n- "
                    + "\n- ".join(problems)] + _image_parts(images, roles)
    return plan, problems


def blocks_from_plan(plan):
    """Plan içindeki çekimleri blok numarasına göre gruplar: [{'block', 'seconds', 'world_anchor', 'shots'}]."""
    anchor = (plan or {}).get("world_anchor", "").strip()
    by_block = {}
    for s in (plan or {}).get("shots") or []:
        b = int(s.get("block", 1))
        by_block.setdefault(b, []).append(dict(s))
    blocks = []
    for b in sorted(by_block):
        shots = by_block[b]
        cur = 0.0
        for j, s in enumerate(shots, 1):
            s["shot"] = j
            s["start_sec"] = round(cur, 2)
            cur += float(s.get("duration", 4.0))
        sec = max(config.MIN_SECONDS, min(config.MAX_SECONDS, int(round(cur))))
        blocks.append({"block": b, "seconds": sec, "world_anchor": anchor, "shots": shots})
    return blocks


def block_request(block_info, style=config.DEFAULT_STYLE, audio_mode=config.DEFAULT_AUDIO_MODE, idea=""):
    """Tek bir bloğun dünya çapası ve çekimlerini `rewrite()` için detaylı yönetmen brief'ine dönüştürür."""
    b = block_info["block"]
    sec = block_info["seconds"]
    anchor = block_info.get("world_anchor", "").strip()
    shots = block_info.get("shots") or []
    lines = [f"Block {b} ({sec} seconds total, {len(shots)} shot(s))."]
    if anchor:
        lines.append(f"World and character anchor (must remain identical across all blocks): {anchor}")
    lines.append(f"Signage rule: {signage_rule(idea or anchor)}")
    for j, s in enumerate(shots, 1):
        start = float(s.get("start_sec", 0.0))
        dur = float(s.get("duration", sec))
        mm, ss = divmod(start, 60.0)
        ts = f"At {int(mm):02d}:{ss:06.3f}" if j > 1 else "At 00:00.000 (opening shot)"
        hold = " Ends with a calm ~0.5-second hold/settling beat before the block ends." if j == len(shots) else ""
        lines.append(
            f"[Shot {j}] {ts} ({dur:.1f}s) — Framing: {s.get('framing', '')}. "
            f"Action: {s.get('action', '')}.{hold} Camera: {s.get('camera', '')}. Sound: {s.get('sound', '')}."
        )
    if audio_mode == "music":
        lines.append(f"Audio mode: music montage with no voices. In overall_soundscape write '{_MUSIC_SILENT}' and in non_diegetic_music write N/A.")
    return "\n".join(lines)


def rewrite_blocks(plan, api_key, model, images=(), retries=1, log=print, style=config.DEFAULT_STYLE,
                   audio_mode=config.DEFAULT_AUDIO_MODE, idea="", roles=None):
    """Plandaki her blok için H3 prompt'u üretir: [{'block', 'seconds', 'request', 'prompt', 'problems'}]."""
    out = []
    for binfo in blocks_from_plan(plan):
        req = block_request(binfo, style=style, audio_mode=audio_mode, idea=idea)
        log(f"Blok {binfo['block']} ({binfo['seconds']} sn, {len(binfo['shots'])} çekim) H3 prompt'u yazılıyor…")
        prompt, probs = rewrite(req, binfo["seconds"], api_key, model, images=images, retries=retries, log=log,
                                style=style, audio_mode=audio_mode, roles=roles)
        out.append({"block": binfo["block"], "seconds": binfo["seconds"], "request": req,
                    "prompt": prompt, "problems": probs})
    return out


def shots_to_rows(shots):
    """Çekim listesini Gradio Dataframe satırlarına çevirir."""
    return [[int(s.get("block", 1)), int(s.get("shot", i + 1)), round(float(s.get("start_sec", 0.0)), 2),
             round(float(s.get("duration", 5.0)), 2), str(s.get("framing", "")), str(s.get("action", "")),
             str(s.get("camera", "")), str(s.get("sound", ""))]
            for i, s in enumerate(shots or [])]


def rows_to_shots(rows):
    """Gradio Dataframe satırlarını (list veya pandas DataFrame) çekim sözlüklerine çevirir."""
    if hasattr(rows, "values"):
        rows = rows.values.tolist()
    shots = []
    for r in rows or []:
        if not r or len(r) < 8 or (str(r[4]).strip() == "" and str(r[5]).strip() == ""):
            continue
        shots.append({
            "block": int(float(r[0] or 1)),
            "shot": int(float(r[1] or 1)),
            "start_sec": round(float(r[2] or 0.0), 2),
            "duration": round(float(r[3] or 5.0), 2),
            "framing": str(r[4] or "").strip(),
            "action": str(r[5] or "").strip(),
            "camera": str(r[6] or "").strip(),
            "sound": str(r[7] or "").strip(),
        })
    return shots


# Test 4: yalnız yüzü dolduran portre referansıyla anime videosu göğüs planda kaldı; karakter baştan ayağa ve
# videodaki kıyafetiyle çizilince referans, istenen kadraja ve kıyafete de örnek olur.
STYLIZE_PROMPT = """Redraw the person in this photo as a full-body character in this style: {look}.
Keep the same identity: face shape, eyes, eyebrows, nose, lips, skin tone, hair colour, length and
style, approximate age. The person is drawn as one of the {people}; stylise the face, skin and hair
completely{face_texture} so the face is never semi-realistic or photographic. Avoid: {avoid}.
Show the whole figure from head to feet, standing in a relaxed neutral pose, facing three-quarters toward the
viewer, in front of a simple plain background, with even, soft light.
Clothing: {clothing}
No text, no letters, no logos, no watermark."""
CLOTHING_FROM_IDEA = ("dress the person exactly as the video idea below describes (garments, colours, accessories, "
                      "flat shoes or boots unless it says otherwise); keep the photo's clothing only for what the idea "
                      "does not mention.\nVideo idea: {idea}")
CLOTHING_FROM_PHOTO = "the same clothing and colours as in the photo, with flat shoes."

STYLIZE_SCENE_PROMPT = """Redraw this place as a background plate in this style: {look}. The background is {background}.
Keep the same place: its architecture, layout, perspective, materials, objects, colour palette and light.
Remove every person; show the empty set, ready for characters to act in it. Nothing may look photographic.
Avoid: {avoid}. No text, no letters, no logos, no watermark."""
STYLIZE_OBJECT_PROMPT = """Redraw this object in this style: {look}. Keep its exact shape, proportions, colours and
markings, on a simple plain background with even, soft light. No people. Avoid: {avoid}.
No text, no letters, no logos, no watermark."""


def image_models(api_key):
    """Görsel üretebilen Gemini modelleri (adında 'image' geçen), en yeni önce."""
    from google import genai
    client = _client(api_key)
    names = [(m.name or "").removeprefix("models/") for m in client.models.list()]
    names = [n for n in names if n.startswith("gemini") and "image" in n]
    ver = lambda n: -(float(re.findall(r"gemini-(\d+(?:\.\d+)?)", n)[0]) if re.findall(r"gemini-(\d+(?:\.\d+)?)", n) else 0)
    return sorted(set(names), key=lambda n: (ver(n), "preview" in n, n))


def stylize_reference(path, style, api_key, model, dest_dir, variants=2, idea="", role=None):
    """Referans fotoğrafı seçilen stilde yeniden çizdirir (scenario-alter'in "target frame" yöntemi: model,
    stilin bitmiş bir örneğini tarif edilmiş halinden çok daha iyi taklit eder). Kaydedilen dosya yolları döner."""
    from google import genai
    from google.genai import types
    s = config.STYLES[style]
    client = _client(api_key, IMAGE_TIMEOUT_MS)
    mime = mimetypes.guess_type(path)[0] or "image/png"
    clothing = CLOTHING_FROM_IDEA.format(idea=idea.strip()) if (idea or "").strip() else CLOTHING_FROM_PHOTO
    face_texture = " with visible brushwork and paper texture" if style == "watercolour" else " in this style"
    if role == ROLE_SCENE:
        text = STYLIZE_SCENE_PROMPT.format(**s)
    elif role == ROLE_OBJECT:
        text = STYLIZE_OBJECT_PROMPT.format(**s)
    else:
        text = STYLIZE_PROMPT.format(clothing=clothing, face_texture=face_texture, **s)
    contents = [text, types.Part.from_bytes(data=open(path, "rb").read(), mime_type=mime)]
    cfg = types.GenerateContentConfig(response_modalities=["IMAGE", "TEXT"], temperature=1.0)
    os.makedirs(dest_dir, exist_ok=True)
    stem = os.path.splitext(os.path.basename(path))[0]
    out = []
    for v in range(variants):
        resp = client.models.generate_content(model=model, contents=contents, config=cfg)
        for cand in resp.candidates or []:
            for part in (cand.content.parts if cand.content else None) or []:
                if getattr(part, "inline_data", None) and part.inline_data.data:
                    ext = mimetypes.guess_extension(part.inline_data.mime_type or "image/png") or ".png"
                    dest = os.path.join(dest_dir, f"{stem}_{style}_{chr(65 + v)}{ext}")
                    open(dest, "wb").write(part.inline_data.data)
                    out.append(dest)
                    break
            else:
                continue
            break
    if not out:
        raise RuntimeError("Gemini görsel döndürmedi (model görsel üretmeyi desteklemiyor olabilir).")
    return out
