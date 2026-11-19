import json, os, sys, datetime
sys.path.insert(0, "/home/user/Colab/h3"); sys.path.insert(0, "/home/user/Colab/muse")
os.environ.setdefault("H3APP_WORK_DIR", "/tmp/claude-0/-home-user-Colab/85f17f2f-d7cb-5964-8859-f60fc53a6a2d/scratchpad/c")
from h3app import hikaye, prompt_writer as pw
import ortak

MUSE_DIZIN = "/home/hatch/workspace/h3uretim/20261119_fatih2"
OUT = "/home/user/Colab/muse_gorevleri/20261119_fatih2"

L1 = "Hünkârım, Peygamber efendimizin müjdesi bugün gerçek oldu."
L2 = "Bu zafer bizim değil, Allah'ındır."
L3 = "Kalkınız ve müsterih olunuz. Ben Sultan Mehmed; hepinize söylüyorum ki bu andan itibaren ne hürriyetleriniz ne de hayatlarınız hakkında korkmayınız."

FIKIR = ("Gerçekçi, sinematik bir tarih filmi sahnesi; 60 saniye. Fethin üçüncü günü, Haziran 1453, öğleden sonra. "
 "Bütün sahne İstanbul kara surlarındaki Topkapı'nın şehir içi tarafından, kapının kemerinden dışarıya, batıya bakan "
 "kameralarla çekiliyor (Fausto Zonaro'nun tablosundaki bakış). Güneş batıda, kapının arkasında: dışarıdaki toprak yol "
 "altın ışık içinde, yolun iki yanında sıra sıra saf tutmuş kırmızı kaftanlı, beyaz börklü yeniçeriler ve yalnızca tek "
 "beyaz hilalli, yıldızsız, yazısız kırmızı sancaklar; içerideki meydan surun uzun gölgesinde. Meydanda korku içinde "
 "diz çökmüş, başları önde yüzlerce Rum: kadınlar, erkekler, yaşlılar; aralarında altı yaşındaki oğlunu bağrına basmış "
 "genç bir anne. Uzaktan yaklaşan mehter marşı ve ordunun uğultusu. Genç Sultan II. Mehmed (21 yaşında, ince bıyıklı, "
 "kısa sakallı, gümüş zırh, kırmızı kaftan, sorguçlu miğfer) beyaz atıyla yolun sonundan kapıya ilerliyor; yanında yaya "
 "hocası Akşemseddin. Tören alayıyla geliyor: önde ağır bir marş çalan mehter takımı, atlı çavuşlar, sancaktarlar ve "
 "yaldızlı alem; Sultan'ın iki yanında yaya, kırmızı kaftanlı, beyaz sorguçlu solaklar; arkasında atlı vezirler ve "
 "paşalar, yeniçeri ağası ve sıra sıra yeniçeriler. Mehter kemerin önünde susuyor; Sultan kemerin altına girip ters ışık "
 "içinde duruyor, uğultu kesiliyor. "
 f"Akşemseddin: \"{L1}\" Sultan: \"{L2}\" Sultan kemerden meydanın gölgesine çıkıyor; diz çökmüş kalabalığı görüyor; "
 "anne oğlunu daha sıkı tutuyor. Sultan'ın yüzü yumuşuyor. Sultan yüksek, sakin ve güven veren bir sesle: "
 f"\"{L3}\" Halk başını kaldırıyor, anne ve çocuk dahil yavaşça ayağa kalkıyor, rahatlamış bir mırıltı yayılıyor. "
 "Kan, ceset, yaralı ya da yağma yok; ağırbaşlı ve törensel.")

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
 "son of about six close to her chest: short dark curly hair, plain beige linen tunic, barefoot")
VEZIR = ("the Sultan's ceremonial procession (alay): at its head a mehter band on foot, kettle drums, big drums, zurnas "
 "and cymbals, in red and green kaftans with tall caps, playing a slow, heavy march; behind them mounted çavuş heralds and "
 "standard-bearers carrying tall plain crimson banners with a single white crescent and a gilded alem finial; then the "
 "Sultan on his white horse, flanked on foot by two rows of solak guards in identical red kaftans and tall white plumed "
 "börk caps with bows across their backs, Akşemseddin walking at his right stirrup; behind him the viziers and pashas on "
 "horseback, grey-bearded men in long dark-green and deep-blue kaftans with large white turbans, the janissary ağa, and "
 "long rows of janissaries on foot. Each group wears identical uniforms")

MEKAN = ("The city-side (inner) face of Topkapı on the Theodosian land walls, seen from inside the city looking west "
 "through the open gate: pale cream limestone blocks with horizontal red-brick bands, crenellated battlements, fresh "
 "siege breaches and soot-blackened stone, a tall brick-arched gate passage with both heavy wooden gate leaves thrown "
 "fully open against the walls. Through the arch the sunlit packed-earth road outside runs straight away into the "
 "distance; fixed ranks of janissaries in crimson kaftans and tall white felt börk caps line both sides of that outside "
 "road for the whole video, holding plain crimson banners that each bear only a single white crescent, no star and no "
 "writing. On the inner side, a wide dusty square of packed earth and worn paving stones lies in the long shadow of the "
 "wall, edged by weathered two-storey stone houses with timber balconies and tiled roofs; the square and the gate "
 "passage are empty.")
ISIK = ("Late afternoon, June 1453. The sun is low in the west, directly behind the gate: the road outside glows golden, "
 "the inner square lies in cool blue-grey shadow, and a strong golden backlight pours through the arch, rim-lighting "
 "anyone who stands in it; fine dust hangs in the shafts of light.")
PALET = "crimson red, warm limestone cream, terracotta brick, cool shadow blue-grey, burnished silver, golden backlight"

NO_TEXT = ("No readable text, signboards, logos or lettering anywhere in the frame, including on walls, houses and the "
 "road through the arch; the banners carry only a single plain white crescent, with no star and no writing.")

kart = {
 "baslik": "Fethin Üçüncü Günü",
 "karakterler": [
  {"id": "K1", "ad": "Sultan II. Mehmed", "konusmaci": "S1", "gorunum": SULTAN_G, "kiyafet": SULTAN_K,
   "ses": "measured, resonant young baritone, calm and commanding, clear formal Istanbul Turkish"},
  {"id": "K2", "ad": "Akşemseddin", "konusmaci": "S2", "gorunum": AKS_G, "kiyafet": AKS_K,
   "ses": "warm, deep, slightly weathered baritone, slow and reverent, Istanbul Turkish"},
  {"id": "K3", "ad": "Rum anne ve oğlu", "konusmaci": "", "gorunum": ANNE_G, "kiyafet": ANNE_K, "ses": ""},
 ],
 "mekan": {"ad": "Topkapı, şehir içinden", "tarif": MEKAN},
 "zaman_isik": ISIK, "renk_paleti": PALET,
 "bloklar": [
  {"blok": 1, "sure": 15, "ozet": "From inside the shadowed square, past the bowed heads of the kneeling crowd, the full "
   "ceremonial procession comes up the sunlit road toward the gate between the janissary ranks: the mehter band playing a "
   "slow march, mounted heralds and standard-bearers with banners and a gilded alem, then the Sultan on his white horse "
   "flanked by solak guards, Akşemseddin at his right stirrup, the viziers and pashas on horseback behind. The band and "
   "banners halt and part before the gate; the Sultan rides into the arch and halts in its golden backlight; the music "
   "stops and the murmur fades into silence.", "replikler": []},
  {"blok": 2, "sure": 15, "ozet": "Under the arch, in backlight, solak guards on both sides, the mounted pashas and banners "
   "behind. Akşemseddin looks up at the Sultan and speaks; the Sultan breathes in and answers calmly; he then looks ahead "
   "into the shadowed square.",
   "replikler": [{"konusmaci": "S2", "metin": L1}, {"konusmaci": "S1", "metin": L2}]},
  {"blok": 3, "sure": 15, "ozet": "The Sultan rides a few steps out of the arch into the shadow of the square and stops; the "
   "solak guards fan out in two lines beside him, the pashas and standard-bearers fill the arch behind. Over his "
   "shoulder: hundreds of Greek townspeople kneel with bowed heads. Close on the young mother pressing her son "
   "to her chest, trembling, her eyes lifting for a moment. The Sultan's face softens.", "replikler": []},
  {"blok": 4, "sure": 15, "ozet": "The Sultan addresses the kneeling crowd in a loud, calm, reassuring voice. As he "
   "finishes, the people lift their heads in astonishment and slowly rise, the mother and child too; a relieved "
   "murmur spreads. No violence, no disorder.", "replikler": [{"konusmaci": "S1", "metin": L3}]},
 ],
}
kart["_meta"] = {"fikir": FIKIR, "sure": 60, "stil": "real", "sahte": False,
                 "modeller": {"hikâye kartı": "elle yazıldı (Claude)"},
                 "olusturma": datetime.datetime.now().isoformat(timespec="seconds")}
sorun = hikaye.kart_denetle(kart, 60, FIKIR)
assert not sorun, sorun

# ---- çekim planı (belge ve blok istekleri için)
def S(b, n, st, d, fr, act, cam, snd):
    return {"block": b, "shot": n, "start_sec": st, "duration": d, "framing": fr, "action": act, "camera": cam, "sound": snd}
WIDE_IN = "Wide low-angle shot from inside the square through the arch, 24mm lens"
shots = [
 S(1,1,0.0,7.0, WIDE_IN, "Foreground: the bowed, shadowed heads and shoulders of kneeling townspeople. Through the open arch, the sunlit road between the janissary ranks; the full ceremonial procession comes slowly toward the gate: the mehter band playing, mounted heralds and standard-bearers with banners and a gilded alem, then the Sultan on his white horse flanked by solak guards, Akşemseddin at his right stirrup, the mounted pashas behind.", "Locked-off camera at kneeling height.", "A slow, heavy mehter march with kettle drums, zurnas and cymbals growing closer, the deep murmur of the army, hoofbeats."),
 S(1,2,7.0,8.0, "Medium-wide shot of the arch from inside, 35mm lens", "The band and the standard-bearers halt outside and part to both sides of the road; the Sultan rides into the arch passage between his solak guards and halts in the middle of it, rim-lit by the golden backlight, horse and rider half silhouette; Akşemseddin stops at his right stirrup (screen left), the mounted pashas and banners behind. Everything holds still for the final 1.5 seconds.", "Locked-off camera.", "The march ends on a last drum beat; hoofbeats echo in the stone passage and stop; the murmur fades into a heavy silence."),
 S(2,1,0.0,6.5, "Medium-wide shot of the arch from inside, 35mm lens", "Same framing as the end of block 1: the Sultan motionless on his white horse in the arch, rim-lit; Akşemseddin at his right stirrup. After 1.5 seconds of stillness Akşemseddin turns his face up to the Sultan and speaks.", "Locked-off camera.", f'Silence, a faint wind; Akşemseddin (S2): "{L1}"'),
 S(2,2,6.5,4.5, "Medium close-up of the Sultan from below, 50mm lens", "The Sultan's face half in shadow, the golden backlight on his helmet plume and shoulders; he breathes in and answers calmly, looking down at Akşemseddin.", "Locked-off camera, slightly low.", f'A breath; the Sultan (S1): "{L2}"'),
 S(2,3,11.0,4.0, "Medium-wide shot of the arch from inside, 35mm lens", "Back to the medium-wide: the Sultan lifts his gaze from Akşemseddin and looks ahead into the shadowed square, toward the camera. Holds still.", "Locked-off camera.", "Silence, wind, the horse's breathing."),
 S(3,1,0.0,4.5, "Medium-wide shot of the arch from inside, 35mm lens", "Same framing as the end of block 2 for 1.5 seconds; then the Sultan nudges the horse and rides a few steps out of the arch into the shadow of the square, Akşemseddin walking with him, and stops.", "Locked-off camera.", "Slow hoofbeats on paving stones, then stillness."),
 S(3,2,4.5,4.5, "Wide over-the-shoulder shot from behind the Sultan, 28mm lens", "Over the Sultan's shoulder and plume: the whole square, hundreds of Greek townspeople kneeling with bowed heads in the shadow, golden light spilling past the Sultan onto their backs.", "Slow, gentle push-in.", "Faint wind; a child's soft whimper."),
 S(3,3,9.0,3.5, "Close-up of the young mother and her son, 50mm lens", "The mother kneels pressing her son to her chest, trembling; her eyes lift toward the Sultan for a moment, then drop.", "Locked-off camera.", "Her shaky breath."),
 S(3,4,12.5,2.5, "Medium close-up of the Sultan, 50mm lens", "Facing the crowd, the Sultan's stern expression softens; he holds still.", "Locked-off camera.", "Silence."),
 S(4,1,0.0,10.5, "Medium close-up of the Sultan, 50mm lens", "Same framing as the end of block 3 for 1.5 seconds; then the Sultan speaks to the crowd, loud, calm and reassuring, Akşemseddin's turban at the edge of the frame.", "Locked-off camera.", f'The Sultan (S1): "{L3}"'),
 S(4,2,10.5,4.5, "Wide over-the-shoulder shot from behind the Sultan, 28mm lens", "The townspeople lift their heads in astonishment and slowly rise; the mother rises holding her son. Everyone settles, standing, for the final 0.5 seconds.", "Locked-off camera.", "Rustle of wool, a relieved murmur spreading across the square."),
]
plan = {"world_anchor": hikaye.dunya_capasi(kart), "shots": shots}

gorseller = hikaye.gorsel_listesi(kart, MUSE_DIZIN + "/gorseller")
print([ (g["id"], g["rol"]) for g in gorseller])
roller = [{"role": g["rol"], "name": g["ad"]} for g in gorseller]

# ---- H3 prompt'ları (Ref2VA; Picture 1 Sultan, 2 Akşemseddin, 3 anne, 4 mekân)
DEF = ("subject_definitions:\n"
 f"<Subject 1> is Sultan II. Mehmed from <Picture 1> (Reference role: identity anchor): {SULTAN_G}. He wears a {SULTAN_K}. Follow his face, beard, armour, helmet and plume exactly; the plain background of <Picture 1> is not carried over.\n"
 f"<Subject 2> is Akşemseddin from <Picture 2> (Reference role: identity anchor): {AKS_G}. He wears a {AKS_K}. The background of <Picture 2> is not carried over.\n"
 f"<Subject 3> is the young Greek mother and her son from <Picture 3> (Reference role: identity anchor): {ANNE_G}; {ANNE_K}. The background of <Picture 3> is not carried over.\n"
 f"<Subject 4> is the place from <Picture 4> (Reference role: scene anchor): {MEKAN} Never create a person from <Picture 4>; the janissary ranks stay outside on the road exactly where <Picture 4> shows them.\n")
RET = ("retention_analysis:\n<Subject 1>: fully_preserved - face, beard, armour, helmet, plume and the white horse stay identical.\n"
 "<Subject 2>: fully_preserved - face, white beard, turban and navy robe stay identical.\n"
 "<Subject 3>: fully_preserved - the mother's face, veil, indigo dress and brown shawl, and the boy's curly hair and beige tunic stay identical.\n"
 "<Subject 4>: fully_preserved - the inner face of the gate, the open arch, the sunlit road with the janissary ranks and the shadowed square stay identical.\n")
STYLE = (f"The target video is a photoreal, cinematic historical film shot on 35mm film with natural light. {ISIK} "
 f"Colour palette: {PALET}. Faces, armour, robes, the horse and the place stay exactly the same as in the reference pictures. "
 f"{VEZIR[0].upper() + VEZIR[1:]}. {NO_TEXT}")

def prompt(summary, shots_txt, sound):
    return (DEF + "\nsummary:\n[reference generation] " + summary + "\n\n" + RET + "\ndetailed_description:\n" + STYLE + "\n"
            + shots_txt + "\n\noverall_soundscape:\n" + sound + "\n\nnon_diegetic_music:\nN/A")

P1 = prompt(
 "Seen from inside the city through the open arch of <Subject 4>, <Subject 1> rides his white horse up the sunlit road between the janissary ranks with <Subject 2> walking beside him, while the kneeling townspeople wait in the shadowed square; he halts inside the arch in golden backlight.",
 "[Shot 1] At 00:00.000, a locked-off wide low-angle shot from inside the shadowed square, 24mm lens, at kneeling height. In the foreground, the bowed heads and wool-covered shoulders of kneeling townspeople fill the lower third of the frame, dark against the light. Through the open brick arch of <Subject 4>, the packed-earth road outside glows golden, lined on both sides by motionless ranks of janissaries in crimson kaftans and white börk caps with plain crimson single-crescent banners stirring in the wind. Up the road comes the Sultan's full ceremonial procession, slowly and in strict order: at its head the mehter band on foot playing a slow march on kettle drums, big drums, zurnas and cymbals; behind them mounted heralds and standard-bearers with tall crimson single-crescent banners and a gilded alem; then <Subject 1> on his white Arabian stallion, the reins in his left hand, flanked on foot by two rows of solak guards in identical red kaftans and tall white plumed caps; <Subject 2> walks at his right stirrup; behind them the mounted viziers and pashas in green and blue kaftans with white turbans and rows of janissaries. The procession grows closer step by step; every horse walks with a natural four-beat gait.\n"
 "[Shot 2] At 00:07.000, a locked-off medium-wide shot of the arch from inside the square, 35mm lens. Just outside the arch the band and the standard-bearers halt and step aside to both edges of the road, the banners framing the opening. <Subject 1> rides into the stone gate passage between his solak guards and draws the reins gently; the white horse stops in the middle of the arch. The golden backlight rims his helmet plume, his shoulders and the horse's mane, horse and rider half in silhouette. <Subject 2> stops at the Sultan's right stirrup on screen left; the solak guards stand still along both walls of the passage, the mounted pashas and banners wait behind in the sunlight. At about 13.5 seconds everything holds completely still until the end of the shot.",
 "A slow, heavy mehter march of kettle drums, zurnas and cymbals growing closer, the deep murmur of a great army, hoofbeats and banners flapping in the wind; the march ends on a last deep drum beat, the hoofbeats echo off the stone of the arch and stop, and the murmur fades into a heavy silence.")
P2 = prompt(
 "Under the arch of <Subject 4>, in golden backlight, <Subject 2> speaks to <Subject 1> and the Sultan answers; then he looks ahead into the shadowed square.",
 "[Shot 1] At 00:00.000, a locked-off medium-wide shot of the arch from inside the square, 35mm lens, exactly the framing of the end of the previous block: <Subject 1> sits motionless on his white horse in the middle of the arch, rim-lit by the golden backlight, <Subject 2> at his right stirrup on screen left, solak guards along both walls of the passage, the mounted pashas and banners behind in the sunlight, the janissary ranks beyond. For the first 1.5 seconds nobody moves. At about 2 seconds, <Subject 2> turns his face up to the Sultan and, with a warm, deep, slightly weathered baritone voice and a slow reverent pace (S2), says: <d>[Turkish] " + L1 + "</d> His lips move only while he speaks.\n"
 "[Shot 2] At 00:06.500, a locked-off medium close-up of <Subject 1> from slightly below, 50mm lens. His face is half in shadow, the golden backlight glowing on his helmet plume and armoured shoulders. He breathes in slowly, looks down at <Subject 2>, and at about 7.5 seconds, with a measured, resonant young baritone voice and a calm commanding pace (S1), says: <d>[Turkish] " + L2 + "</d> He closes his mouth and keeps looking down.\n"
 "[Shot 3] At 00:11.000, back to the locked-off medium-wide shot of the arch from inside. <Subject 1> lifts his gaze from <Subject 2> and looks ahead into the shadowed square, toward the camera. Horse, rider and scholar hold still until the end of the shot.",
 "A heavy silence under the stone arch, a faint wind, the horse's slow breathing, the creak of saddle leather; the two spoken lines are close and clear.")
P3 = prompt(
 "<Subject 1> rides out of the arch of <Subject 4> into the shadowed square and sees the kneeling townspeople; <Subject 3>, a young mother, presses her son to her chest; the Sultan's face softens.",
 "[Shot 1] At 00:00.000, a locked-off medium-wide shot of the arch from inside, 35mm lens, exactly the framing of the end of the previous block: <Subject 1> motionless on his white horse in the arch, looking ahead, <Subject 2> at his right stirrup. For the first 1.5 seconds nobody moves. Then <Subject 1> nudges the horse gently; it walks a few steps out of the arch into the shadow of the square, <Subject 2> walking beside it, and stops; the solak guards follow and form two still lines on either side of him, the mounted pashas and standard-bearers fill the arch behind.\n"
 "[Shot 2] At 00:04.500, a wide over-the-shoulder shot from behind <Subject 1>, 28mm lens, with a slow gentle push-in. Past his armoured shoulder and white plume, with the lines of solak guards at the edges of the frame, the whole square opens up: hundreds of Greek townspeople, men, women and old people in plain undyed wool, kneel on the paving stones with bowed heads in the cool shadow; the golden backlight spills past the Sultan onto their backs. Nobody moves except for small trembling.\n"
 "[Shot 3] At 00:09.000, a locked-off close-up of <Subject 3>, 50mm lens: the young mother kneels among the crowd, pressing her son's curly head to her chest with both arms, her hands trembling. Her eyes lift toward the Sultan for a moment, then drop again.\n"
 "[Shot 4] At 00:12.500, a locked-off medium close-up of <Subject 1>, 50mm lens, facing the crowd, rim-lit from behind. His stern expression softens; he holds completely still until the end of the shot.",
 "Slow hoofbeats on worn paving stones, then a deep, frightened silence in the shaded square: faint wind, the rustle of wool, a child's soft whimper, the mother's shaky breath.")
P4 = prompt(
 "In the shadowed square in front of the arch of <Subject 4>, <Subject 1> tells the kneeling townspeople to rise and fear nothing; they lift their heads and slowly stand, <Subject 3> rising with her son.",
 "[Shot 1] At 00:00.000, a locked-off medium close-up of <Subject 1>, 50mm lens, exactly the framing of the end of the previous block: the Sultan on his white horse, rim-lit from behind, the white turban of <Subject 2> at the lower edge of the frame. For the first 1.5 seconds he holds still. At about 1.5 seconds, with a loud, calm and reassuring measured young baritone voice (S1), he says to the crowd: <d>[Turkish] " + L3 + "</d> His lips move clearly and only while he speaks.\n"
 "[Shot 2] At 00:10.500, a locked-off wide over-the-shoulder shot from behind <Subject 1>, 28mm lens. Across the shaded square, between the still lines of solak guards, the townspeople lift their heads in astonishment and slowly rise to their feet; <Subject 3> rises holding her son close. Everyone stands still, faces turned to the Sultan, for the final 0.5 seconds.",
 "The Sultan's voice carries across the silent square; then the soft rustle of wool as hundreds of people stand up, and a quiet, relieved murmur spreading through the crowd.")

istekler = []
for b in pw.blocks_from_plan(plan):
    ist = pw.block_request(b, style="real", idea=FIKIR)
    ist = "\n".join(NO_TEXT and ("Signage rule: " + NO_TEXT) if l.startswith("Signage rule:") else l for l in ist.splitlines())
    istekler.append((b, ist))
bloklar = []
for (b, ist), p in zip(istekler, (P1, P2, P3, P4)):
    req = ist
    probs = pw.check(p, req, len(gorseller), "real", roles=roller)
    print(b["block"], b["seconds"], "sorunlar:", probs)
    bloklar.append({"blok": b["block"], "sure": b["seconds"], "istek": ist, "prompt": p, "sorunlar": probs})

senaryo = {
 "surum": 2, "tur": "uzun", "olusturma": datetime.datetime.now().isoformat(timespec="seconds"),
 "h3app_surum": ortak.h3app_surum(), "fikir": FIKIR, "sure": 60, "stil": "real", "yontem": "pika",
 "cozunurluk": ortak.COZUNURLUKLER["yatay"], "seed": 22,
 "referanslar": [{"dosya": g["dosya"], "rol": g["rol"], "ad": g["ad"]} for g in gorseller],
 "hikaye": {k: v for k, v in kart.items() if not k.startswith("_")},
 "dunya_capasi": plan["world_anchor"], "plan": plan,
 "kollar": {"ref": {"ref": True, "bloklar": bloklar}},
 "yeniden_uretim": 1, "kopru": False, "deney": False, "brief": hikaye.plan_fikri(kart),
 "sorunlar": [s for b in bloklar for s in b["sorunlar"]],
 "modeller": {"hikâye kartı": "elle yazıldı (Claude)", "H3 prompt'u": "elle yazıldı (Claude)"},
 "yedek_model": [], "notlar": ["Kart, çekim planı ve dört H3 prompt'u elle yazıldı; köprü kapalı (Gemini köprüde prompt'u yeniden yazıp bu ayrıntıyı kaybederdi)."],
 "sahte": False, "durum": "hazir",
}
assert not senaryo["sorunlar"], senaryo["sorunlar"]
json.dump(kart, open(f"{OUT}/hikaye.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
json.dump(senaryo, open(f"{OUT}/uzun_senaryo.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("h3app_surum", senaryo["h3app_surum"], "· kelime/sn blok4:", len(L3.split()))
