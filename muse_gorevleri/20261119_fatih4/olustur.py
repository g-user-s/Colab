"""Fatih'in İstanbul'a girişi — Zonaro'nun tablosunun canlı hâli. Elle yazılmış hikâye kartı, çekim planı ve
H3 prompt'ları (60 sn, 4 blok). MiniMax H3 resmî prompt rehberine (h3-prompt-writing, ref-en / base-en) göre yazıldı:
- altı bölüm sırasıyla; summary "[reference generation]" ile başlar;
- detailed_description stil cümlesiyle açılır, her blokta 350-500 İngilizce kelime;
- [Shot 1] zaman damgasız, sonrakiler "At MM:SS.mmm";
- kamera dili rehberin sözlüğüyle (push in, pull out, pedestal, tracking, static; amplitude + speed);
- konuşmacı kimliği filmdeki konuşma sırasıyla (Akşemseddin S1, Sultan S2), ses tarifi <d> dışında;
- retention_analysis her özne için görüldüğü çekimlerle.
Çalıştır: python3 muse_gorevleri/20261119_fatih4/olustur.py  →  aynı klasöre hikaye.json ve uzun_senaryo.json"""
import datetime, json, os, re, sys
DEPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(DEPO, "h3")); sys.path.insert(0, os.path.join(DEPO, "muse"))
os.environ.setdefault("H3APP_WORK_DIR", os.path.expanduser("~/.cache/h3muse"))
from h3app import hikaye, prompt_writer as pw
import ortak

MUSE_DIZIN = "/home/hatch/workspace/h3uretim/20261119_fatih4"
OUT = os.path.dirname(os.path.abspath(__file__))

L1 = "Hünkârım, Peygamber efendimizin müjdesi bugün gerçek oldu."
L2 = "Bu zafer bizim değil, Allah'ındır."
L3 = ("Kalkınız ve müsterih olunuz. Ben Sultan Mehmed; hepinize söylüyorum ki bu andan itibaren ne hürriyetleriniz "
      "ne de hayatlarınız hakkında korkmayınız.")

FIKIR = ("Profesyonel bir tarih filmi sahnesi, 60 saniye: Fausto Zonaro'nun 'Fatih'in İstanbul'a Girişi' tablosunun "
 "canlı hâli. Fethin üçüncü günü, Haziran 1453, ikindi. Topkapı'nın şehir içinden görülen büyük kemeri: kireç taşı ve "
 "kırmızı tuğla bantlı, hasarlı, kemerin iç yüzünde solmuş bir Bizans freskosu. Güneş kemerin arkasında; kemerin "
 "içinden göz alan altın bir ışık ve pus giriyor. Kemerden şehre doğru taş döşeli geniş bir yol; iki yanında omuz "
 "omuza yeniçeri kordonu, yalnızca tek beyaz hilalli, yıldızsız, yazısız kırmızı ve yeşil sancaklar; kordonun "
 "arkasında, yıkık duvarlarda, damlarda ve pencerelerde binlerce Rum padişahı bekliyor; aralarında altı yaşındaki "
 "oğlunu kucağında tutan genç bir anne. Önce sessiz bekleyiş, surların ötesinden ağır mehter. Tören alayı kemerden "
 "giriyor: mehter takımı, atlı çavuşlar, sancaktarlar ve yaldızlı alem; sonra tablodaki an: kemerin gölgesinden "
 "ışığa, beyaz atının üstünde genç Sultan II. Mehmed (21 yaşında, ince bıyıklı, kısa sakallı, gümüş zırh, kırmızı "
 "kaftan, beyaz sorguçlu miğfer) kameraya doğru çıkıyor; sağ eli hafifçe kalkık; solunda önde yaya, ak sakallı, "
 "lacivert cübbeli hocası Akşemseddin; arkasında kemerin içini dolduran mızrak ve sancak ormanı, parlak gökyüzüne "
 "karşı; ön planda solda kırmızı-altın sarıklı bir muhafız. Alay geçerken kalabalık dalga dalga diz çöküyor; alay "
 "kemerin önündeki meydanda duruyor, mehter susuyor, ağır bir sessizlik. "
 f"Akşemseddin: \"{L1}\" Sultan: \"{L2}\" Sultan diz çökmüş binlerce kişiye bakıyor; anne oğlunu sıkıca tutuyor. "
 f"Sultan yüksek, sakin ve güven veren bir sesle: \"{L3}\" Binlerce kişi yavaşça ayağa kalkıyor; yüksekten, kemer ve "
 "bütün meydan. Kan, ceset, yaralı ya da yağma yok; ağırbaşlı, törensel ve gerçekçi.")

SULTAN_G = ("21-year-old Turkish man, oval aristocratic face, slightly aquiline nose, warm olive-fair skin, dark brown "
 "almond-shaped eyes, thick dark arched eyebrows, thin neatly trimmed dark moustache and short dark beard, dark hair "
 "under his helmet, lean athletic build, tall")
SULTAN_K = ("deep crimson silk kaftan with long sleeves under polished silver chainmail and an ornate silver breastplate, "
 "pointed polished steel helmet with a gold-inlaid brow band and a tall white plume, silver bracers, dark leather riding "
 "boots; he rides a tall white Arabian stallion with a crimson velvet saddle cloth, silver-embossed saddle and gilded bridle")
AKS_G = ("Turkish scholar about 63 years old, dignified weathered oval face, fair-olive skin with fine wrinkles, calm "
 "deep-set dark eyes, thick white eyebrows, straight nose, long full white beard and white moustache, slender upright build")
AKS_K = ("long flowing dark navy-blue wool robe over an off-white inner tunic with a dark sash, large neatly wrapped white "
 "linen turban, soft dark leather flat boots; he walks on foot")
ANNE_G = ("Greek woman about 30 years old, oval face, olive skin, dark tired eyes, dark brown hair under a plain undyed "
 "linen head veil, slim build")
ANNE_K = ("long faded indigo wool dress, rough brown wool shawl over her shoulders, simple leather sandals; she holds her "
 "son of about six on her hip: short dark curly hair, plain beige linen tunic, barefoot")

MEKAN = ("The inner, city-side face of Topkapı, the great gate in the land walls of Constantinople, seen from inside the "
 "city at standing eye level about forty metres away, looking straight west into the gate. The massive round arch of "
 "pale limestone with bands of red brick fills the upper middle of the frame; its stones are cracked and scarred by "
 "cannon fire, and on the plastered inner face of the arch a large faded Byzantine fresco of a haloed figure in ochre "
 "and blue is half flaked away. Through the deep, shadowed passage of the arch the open sky beyond blazes white-gold. "
 "From the arch toward the camera runs a broad road of worn stone paving that opens into a wide square. A continuous "
 "cordon of janissaries in crimson kaftans and tall white felt börk caps stands shoulder to shoulder along both sides "
 "of the road, facing inward, holding tall plain crimson and green banners that each bear only a single white "
 "crescent. Behind the cordon, on heaps of fallen masonry, on the wall-walk above the gate, on the flat roofs and in the "
 "windows of the stone houses on both sides, thousands of townspeople stand packed and waiting: Greek men, women, old "
 "people, children on shoulders, in plain wool clothes of muted earth tones. The stone-paved centre of the road and the "
 "square is empty.")
ISIK = ("Late afternoon, June 1453. The sun stands low in the west directly behind the gate: hazy golden light and "
 "drifting dust pour through the arch toward the camera, the passage under the arch is in deep shade, the crowd and the "
 "houses are in soft warm shade, and every figure on the road is rim-lit from behind.")
PALET = ("crimson red, emerald green, warm limestone cream, terracotta brick, faded fresco ochre and blue, earth-brown "
 "and grey wool, burnished silver, white-gold sky")
NO_TEXT = ("No readable text, calligraphy, signboards, logos or lettering anywhere in the frame, including on the gate, "
 "the walls and the houses; the banners carry only a single plain white crescent, with no star and no writing.")
ALAY = ("The procession moves in strict order through the arch: a mehter band on foot (kettle drums, big drums, zurnas, "
 "cymbals; red and green kaftans, tall caps), mounted heralds and standard-bearers with tall crimson and green banners "
 "and a gilded alem finial, then the Sultan on his white horse flanked on foot by solak guards in identical red kaftans "
 "and white plumed caps, then mounted viziers and pashas in dark-green and deep-blue kaftans with large white turbans, "
 "and behind them a dense column of soldiers with upright spears.")

kart = {
 "baslik": "Fethin Üçüncü Günü",
 "karakterler": [
  {"id": "K1", "ad": "Akşemseddin", "konusmaci": "S1", "gorunum": AKS_G, "kiyafet": AKS_K,
   "ses": "warm, deep, slightly weathered baritone, slow and reverent, Istanbul Turkish"},
  {"id": "K2", "ad": "Sultan II. Mehmed", "konusmaci": "S2", "gorunum": SULTAN_G, "kiyafet": SULTAN_K,
   "ses": "measured, resonant young baritone, calm and commanding, clear formal Istanbul Turkish"},
  {"id": "K3", "ad": "Rum anne ve oğlu", "konusmaci": "", "gorunum": ANNE_G, "kiyafet": ANNE_K, "ses": ""},
 ],
 "mekan": {"ad": "Topkapı'nın şehir içinden görünüşü ve önündeki meydan", "tarif": MEKAN},
 "zaman_isik": ISIK, "renk_paleti": PALET,
 "bloklar": [
  {"blok": 1, "sure": 15, "ozet": "High wide shot of the gate and the square packed with thousands waiting in silence; "
   "distant mehter beyond the walls. Then at eye level among the crowd: tense faces, the young mother with her son on "
   "her hip; the first banners and the mehter emerge from the blazing arch.", "replikler": []},
  {"blok": 2, "sure": 15, "ozet": "Zonaro's painting comes alive: out of the shadow of the arch into the light, the Sultan "
   "rides toward the camera on his white horse, Akşemseddin walking ahead at left, a forest of spears and banners "
   "behind against the bright sky. The crowd kneels in a wave as he passes; the procession halts; silence.",
   "replikler": []},
  {"blok": 3, "sure": 15, "ozet": "In the silent square before the gate, Akşemseddin looks up and speaks; the Sultan "
   "answers calmly. Close on the kneeling young mother pressing her son to her chest. The Sultan looks over the kneeling "
   "thousands.", "replikler": [{"konusmaci": "S1", "metin": L1}, {"konusmaci": "S2", "metin": L2}]},
  {"blok": 4, "sure": 15, "ozet": "The Sultan addresses the kneeling crowd in a loud, calm, reassuring voice. As he "
   "finishes, the thousands lift their heads and slowly rise, seen from high above the gate and the square.",
   "replikler": [{"konusmaci": "S2", "metin": L3}]},
 ],
}
kart["_meta"] = {"fikir": FIKIR, "sure": 60, "stil": "real", "sahte": False,
                 "modeller": {"hikâye kartı": "elle yazıldı (Claude)"},
                 "olusturma": datetime.datetime.now().isoformat(timespec="seconds")}
sorun = hikaye.kart_denetle(kart, 60, FIKIR)
assert not sorun, sorun

def S(b, n, st, d, fr, act, cam, snd):
    return {"block": b, "shot": n, "start_sec": st, "duration": d, "framing": fr, "action": act, "camera": cam, "sound": snd}
HIGH = "High wide shot from a rooftop inside the city, facing the gate along its axis, 24mm lens"
CROWD = "Eye-level medium shot inside the crowd behind the cordon, 50mm lens"
TABLO = "Low frontal wide shot on the road's axis facing the arch (Zonaro's composition), 32mm lens"
SIDE = "Wide side shot along the cordon, 35mm lens"
TWO = "Medium two-shot of Akşemseddin and the Sultan with the arch behind them, 50mm lens"
MCU = "Medium close-up of the Sultan from slightly below, 50mm lens"
shots = [
 S(1,1,0.0,7.0,HIGH,"The gate, the empty road and the square; thousands waiting in silence behind the janissary cordon, on rubble, roofs and the wall-walk.","Pedestal down with large amplitude at slow speed.","Distant heavy mehter drums beyond the walls; a vast uneasy murmur."),
 S(1,2,7.0,8.0,CROWD,"Tense faces; the young mother with her son on her hip; the first banners and the mehter band emerge from the blazing arch, out of focus. Holds for the final second.","Static shot, shallow depth of field.","The march grows louder and echoes in the arch; whispers hushed."),
 S(2,1,0.0,9.0,TABLO,"Zonaro's painting comes alive: the Sultan rides out of the shadowed passage into the golden light toward the camera, right hand slightly raised; Akşemseddin walks ahead at left; spears and banners fill the arch behind against the bright sky; a red-and-gold-turbaned guard in the left foreground.","Push in with small amplitude at slow speed.","Close, heavy mehter march, hoofbeats on stone, banners in the wind."),
 S(2,2,9.0,6.0,SIDE,"The Sultan passes; the crowd behind the cordon sinks to its knees in a wave; the procession halts in the square; the march ends; everything holds still.","Tracking shot at slow speed, then static.","Last deep drum beat; rustle of thousands kneeling; heavy silence."),
 S(3,1,0.0,6.5,TWO,"The Sultan motionless on his horse, rim-lit, the arch behind; Akşemseddin at his right stirrup looks up and speaks.","Static shot.",f'Silence, wind; Akşemseddin (S1): "{L1}"'),
 S(3,2,6.5,4.0,MCU,"The Sultan looks down at Akşemseddin and answers calmly.","Static shot, slightly low.",f'The Sultan (S2): "{L2}"'),
 S(3,3,10.5,2.5,"Close-up of the kneeling young mother and her son, 50mm lens","She presses her son to her chest, trembling; her eyes lift toward the Sultan, then drop.","Static shot.","Her shaky breath."),
 S(3,4,13.0,2.0,MCU,"The Sultan looks over the kneeling thousands; his stern face softens. Holds still.","Static shot.","Silence."),
 S(4,1,0.0,10.5,MCU,"The Sultan straightens in the saddle and speaks to the kneeling crowd.","Push in with small amplitude at slow speed.",f'The Sultan (S2): "{L3}"'),
 S(4,2,10.5,4.5,HIGH,"From high above: the gate, the halted procession and the square; thousands lift their heads and slowly rise. Holds for the final 0.5 seconds.","Pedestal up with large amplitude at slow speed.","Rustle of thousands standing; a relieved murmur."),
]
plan = {"world_anchor": hikaye.dunya_capasi(kart), "shots": shots}
gorseller = hikaye.gorsel_listesi(kart, MUSE_DIZIN + "/gorseller")
roller = [{"role": g["rol"], "name": g["ad"]} for g in gorseller]
assert [g["id"] for g in gorseller] == ["K1", "K2", "K3", "MEKAN"], gorseller

DEF = ("subject_definitions:\n"
 f"<Subject 1> is Akşemseddin from <Picture 1> (Reference role: identity anchor): {AKS_G}. He wears a {AKS_K}. The background of <Picture 1> is not carried over.\n"
 f"<Subject 2> is Sultan II. Mehmed from <Picture 2> (Reference role: identity anchor): {SULTAN_G}. He wears a {SULTAN_K}. Follow his face, beard, armour, helmet, plume and the white horse exactly; the background of <Picture 2> is not carried over.\n"
 f"<Subject 3> is the young Greek mother and her son from <Picture 3> (Reference role: identity anchor): {ANNE_G}; {ANNE_K}. The background of <Picture 3> is not carried over.\n"
 f"<Subject 4> is the gate and the square from <Picture 4> (Reference role: scene anchor): {MEKAN} Never create a main character from <Picture 4>; the janissary cordon and the waiting crowd stay along the sides exactly where <Picture 4> shows them.\n")

def RET(gorunen):
    sat = {1: "face, white beard, white turban and navy robe stay identical.",
           2: "face, beard, armour, helmet, white plume and the white horse stay identical.",
           3: "the mother's face, veil, indigo dress and brown shawl, and the boy's curly hair and beige tunic stay identical.",
           4: "the arch, its brick banding and faded fresco, the road, the square, the houses, the janissary cordon and the crowd along the sides stay identical."}
    return "retention_analysis:\n" + "".join(
        f"<Subject {i}> (appears in {', '.join(f'[Shot {s}]' for s in gorunen[i])}): fully_preserved - {sat[i]}\n"
        for i in sorted(gorunen))

STYLE = ("The target video is a live-action historical feature film shot on 35mm film with anamorphic lenses, lit only by "
 f"natural late-afternoon sun, with real crowds of extras. {ISIK} Colour palette: {PALET}. {NO_TEXT}")

def prompt(summary, gorunen, shots_txt, sound, music):
    return (DEF + "\nsummary:\n[reference generation] " + summary + "\n\n" + RET(gorunen) + "\ndetailed_description:\n"
            + STYLE + "\n" + shots_txt + "\n\noverall_soundscape:\n" + sound + "\n\nnon_diegetic_music:\n" + music)

P1 = prompt(
 "Thousands of townspeople wait in silence before the gate of <Subject 4> as the ceremonial procession approaches from beyond the walls; at eye level, <Subject 3> waits among the crowd as the first banners emerge from the blazing arch.",
 {3: [2], 4: [1, 2]},
 "[Shot 1] A high wide shot from a flat rooftop inside the city, 24mm lens, looking straight down the axis of the road toward the gate of <Subject 4>. The camera pedestals down with large amplitude at slow speed from above the roofline. The great limestone-and-brick arch fills the upper middle of the frame, its passage in deep shade and the sky beyond blazing white-gold; dust drifts in the light pouring through it. The stone-paved road and the wide square below are empty. Along both sides stands the crimson janissary cordon with its crimson and green single-crescent banners, and behind it thousands of townspeople are packed on heaps of fallen masonry, on the wall-walk above the gate, on flat roofs and in windows; fathers hold children on their shoulders. Nobody moves; only the banners stir in the wind.\n"
 "[Shot 2] At 00:07.000, the shot cuts to a static eye-level medium shot inside the crowd behind the cordon, 50mm lens, shallow depth of field. In the foreground <Subject 3> stands among tense, silent townspeople, her son on her hip, his face turned into her shoulder; an old man beside her grips his cap with both hands; the red backs and white caps of the janissaries are just in front of them. Far behind, out of focus, the arch blazes with light, and the first tall banners and the mehter band step out of its shadowed passage into the square in strict order. <Subject 3> lifts her eyes toward the gate and holds her breath. From 00:14.000 everyone holds completely still until the end of the shot.",
 "A slow, heavy mehter march of kettle drums, big drums, zurnas and cymbals, muffled beyond the walls at first, then echoing loudly through the arch; the vast, uneasy murmur of thousands of people, wind in the banners, and close whispers hushed at street level.",
 "A low sustained drone of bowed double basses at a very slow tempo, with a soft frame drum pulse that grows slightly louder toward the end.")
P2 = prompt(
 "The moment of Zonaro's painting comes alive: <Subject 2> rides out of the shadow of the arch of <Subject 4> toward the camera on his white horse, <Subject 1> walking ahead at left, a forest of spears and banners behind against the bright sky; as he passes, the crowd sinks to its knees in a wave, the procession halts and silence falls.",
 {1: [1, 2], 2: [1, 2], 4: [1, 2]},
 "[Shot 1] A low frontal wide shot on the axis of the road, 32mm lens, facing the arch of <Subject 4>; the composition of a grand history painting. The camera pushes in with small amplitude at slow speed. Out of the deep shade of the passage, <Subject 2> rides into the golden light straight toward the camera, slightly left of centre, on his tall white stallion; the horse steps high and proud, its mane and the white plume rim-lit; the Sultan sits upright, his right hand slightly raised, his face calm. A few steps ahead of him on the left walks <Subject 1>, head bowed, right hand on his chest, his navy robe and white beard glowing at the edges. Behind them the whole passage of the arch is packed with mounted pashas in white turbans, solak guards in red kaftans and a dense forest of upright spears and crimson and green banners against the blazing white-gold sky. The faded fresco on the arch hangs above them. In the left foreground, close to the lens, a guard in a red kaftan and a red-and-gold turban stands half turned toward the procession. The mehter band, already through, stands at both sides of the square playing. Every horse walks with a natural four-beat gait.\n"
 "[Shot 2] At 00:09.000, the shot cuts to a wide side shot along the cordon, 35mm lens. The camera tracks at slow speed beside the procession as <Subject 2> rides past on his white horse, <Subject 1> at his right stirrup; behind the janissaries the crowd sinks to its knees in a slow wave that follows the Sultan. At 00:12.500 the procession halts in the middle of the square, the camera holds a static shot, the march ends on one last deep drum beat, and everyone stays completely still until the end of the shot.",
 "The heavy mehter march close and loud, hoofbeats on stone echoing in the arch, banners snapping in the wind, harness jingling; then one last deep drum beat, the soft rustle of thousands of people kneeling, and a heavy silence with only wind.",
 "N/A")
P3 = prompt(
 "In the silent square before the arch of <Subject 4>, <Subject 1> speaks to <Subject 2> and the Sultan answers; <Subject 3> kneels pressing her son to her chest; the Sultan looks over the kneeling thousands.",
 {1: [1, 2], 2: [1, 2, 4], 3: [3], 4: [1, 3, 4]},
 "[Shot 1] A static medium two-shot, 50mm lens, from the front-right of the halted procession. <Subject 2> sits motionless on his white horse in the middle of the square, rim-lit by the golden light, the great arch of <Subject 4> with its faded fresco and the massed spears and banners blurred behind him. <Subject 1> stands at his right stirrup on screen left, solak guards in red kaftans beyond, the kneeling crowd at the edges of the frame. For the first 1.5 seconds nobody moves. At about 00:02.000, <Subject 1>, an elderly scholar with a warm, deep, slightly weathered baritone voice and a slow reverent pace (S1), looks up at the Sultan and says: <d>[Turkish] " + L1 + "</d> His lips move only while he speaks, then close.\n"
 "[Shot 2] At 00:06.500, the shot cuts to a static medium close-up of <Subject 2> from slightly below, 50mm lens, his face half in warm shade, the golden backlight on his white plume and silver shoulders, the bright arch soft behind him. He breathes in and looks down at <Subject 1>. At about 00:07.500, the young Sultan with a measured, resonant young baritone voice (S2) says calmly: <d>[Turkish] " + L2 + "</d> His lips then close.\n"
 "[Shot 3] At 00:10.500, the shot cuts to a static close-up of <Subject 3>, 50mm lens, kneeling on the paving among the crowd behind the cordon. She presses her son's curly head to her chest with both arms, trembling; her eyes lift toward the Sultan for a moment, then drop.\n"
 "[Shot 4] At 00:13.000, the shot cuts back to the static medium close-up of <Subject 2>. He turns his head and looks over the kneeling thousands; his stern face softens. He holds completely still until the end of the shot.",
 "A deep silence over the whole square: faint wind through the arch, a horse snorting softly, the creak of saddle leather, a banner flapping once, the mother's shaky breath; the two spoken lines are close and clear.",
 "N/A")
P4 = prompt(
 "<Subject 2> tells the kneeling crowd before the gate of <Subject 4> to rise and fear nothing; the thousands lift their heads and slowly stand, seen from high above the arch and the square.",
 {2: [1, 2], 3: [2], 4: [1, 2]},
 "[Shot 1] A medium close-up of <Subject 2> from slightly below, 50mm lens, on his white horse in the middle of the square, rim-lit from behind, the bright arch of <Subject 4> soft over his shoulder. The camera pushes in with small amplitude at slow speed. He straightens in the saddle, lifts his chin and looks out over the crowd. At about 00:01.500, the young Sultan with a measured, resonant young baritone voice (S2), raised loud enough to carry across the square yet calm and reassuring, says: <d>[Turkish] " + L3 + "</d> His lips move clearly and only while he speaks; after the last word he holds still.\n"
 "[Shot 2] At 00:10.500, the shot cuts to a high wide shot from the rooftop inside the city, 24mm lens, on the axis of the road. The camera pedestals up with large amplitude at slow speed. Below lie the great arch of <Subject 4> blazing with golden light, the procession standing still in the middle of the square with the white horse at its centre, and on both sides thousands of townspeople lifting their heads and slowly rising to their feet behind the janissary cordon, on the rubble, on the roofs and on the wall-walk; <Subject 3> rises among them with her son. Everyone stands still for the final 0.5 seconds.",
 "The Sultan's voice carries across the silent square and echoes softly in the arch; then the vast soft rustle of thousands of people standing up, and a relieved murmur rolling through the crowd.",
 "A slow, warm string chord swells gently under the final wide shot and sustains to the end, with a single low ney note above it.")

def kelime(p):
    d = p[p.find("detailed_description:"):p.find("overall_soundscape:")]
    return len(re.findall(r"[A-Za-z']+", re.sub(r"<d>.*?</d>", "", d)))

bloklar = []
for b, p in zip(pw.blocks_from_plan(plan), (P1, P2, P3, P4)):
    ist = pw.block_request(b, style="real", idea=FIKIR)
    ist = "\n".join(("Signage rule: " + NO_TEXT) if l.startswith("Signage rule:") else l for l in ist.splitlines())
    probs = pw.check(p, ist, len(gorseller), "real", roles=roller)
    k = kelime(p)
    print("blok", b["block"], b["seconds"], "sn ·", k, "kelime · sorunlar:", probs)
    assert 350 <= k <= 520, (b["block"], k)
    bloklar.append({"blok": b["block"], "sure": b["seconds"], "istek": ist, "prompt": p, "sorunlar": probs})

senaryo = {
 "surum": 2, "tur": "uzun", "olusturma": datetime.datetime.now().isoformat(timespec="seconds"),
 "h3app_surum": ortak.h3app_surum(), "fikir": FIKIR, "sure": 60, "stil": "real", "yontem": "pika",
 "cozunurluk": ortak.COZUNURLUKLER["yatay"], "seed": 22,
 "referanslar": [{"dosya": g["dosya"], "rol": g["rol"], "ad": g["ad"]} for g in gorseller],
 "hikaye": {k: v for k, v in kart.items() if not k.startswith("_")},
 "dunya_capasi": plan["world_anchor"], "plan": plan, "kollar": {"ref": {"ref": True, "bloklar": bloklar}},
 "yeniden_uretim": 1, "kopru": False, "deney": False, "brief": hikaye.plan_fikri(kart),
 "sorunlar": [s for b in bloklar for s in b["sorunlar"]],
 "modeller": {"hikâye kartı": "elle yazıldı (Claude)", "H3 prompt'u": "elle yazıldı (Claude, MiniMax H3 rehberine göre)"},
 "yedek_model": [], "notlar": ["Zonaro'nun tablosunun canlı hâli. Kart, çekim planı ve dört H3 prompt'u elle yazıldı; köprü kapalı."],
 "sahte": False, "durum": "hazir",
}
assert not senaryo["sorunlar"], senaryo["sorunlar"]
json.dump(kart, open(os.path.join(OUT, "hikaye.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
json.dump(senaryo, open(os.path.join(OUT, "uzun_senaryo.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("h3app_surum", senaryo["h3app_surum"], "·", ortak.tahmini_maliyet(senaryo, "a100"))
