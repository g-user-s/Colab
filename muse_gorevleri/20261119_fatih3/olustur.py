"""Fatih'in İstanbul'a girişi — elle yazılmış hikâye kartı, çekim planı ve H3 prompt'ları (60 sn, 4 blok).
Çalıştır: python3 muse_gorevleri/20261119_fatih3/olustur.py  →  aynı klasöre hikaye.json ve uzun_senaryo.json"""
import datetime, json, os, sys
DEPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(DEPO, "h3")); sys.path.insert(0, os.path.join(DEPO, "muse"))
os.environ.setdefault("H3APP_WORK_DIR", os.path.expanduser("~/.cache/h3muse"))
from h3app import hikaye, prompt_writer as pw
import ortak

MUSE_DIZIN = "/home/hatch/workspace/h3uretim/20261119_fatih3"
OUT = os.path.dirname(os.path.abspath(__file__))

L1 = "Hünkârım, Peygamber efendimizin müjdesi bugün gerçek oldu."
L2 = "Bu zafer bizim değil, Allah'ındır."
L3 = ("Kalkınız ve müsterih olunuz. Ben Sultan Mehmed; hepinize söylüyorum ki bu andan itibaren ne hürriyetleriniz "
      "ne de hayatlarınız hakkında korkmayınız.")

FIKIR = ("Profesyonel bir tarih filmi sahnesi, 60 saniye. Fethin üçüncü günü, Haziran 1453, öğleden sonra. Topkapı'dan "
 "şehrin içine uzanan uzun, taş döşeli bir cadde; iki yanında balkonlu taş ve tuğla evler. Caddenin iki kenarında omuz "
 "omuza dizilmiş yeniçeri kordonu, ellerinde yalnızca tek beyaz hilalli, yıldızsız, yazısız kırmızı sancaklar; "
 "kordonun arkasında, balkonlarda ve pencerelerde binlerce Rum padişahı bekliyor: erkekler, kadınlar, yaşlılar, "
 "omuzlarda çocuklar; aralarında altı yaşındaki oğlunu kucağında tutan genç bir anne. Güneş caddenin sonundaki kapının "
 "arkasında; kapı puslu altın ışıkta parlıyor. Yüksek bir açıdan açılıyor: tören alayı kapıdan giriyor; önde ağır bir "
 "marş çalan mehter takımı, atlı çavuşlar, sancaktarlar ve yaldızlı alem; ortada beyaz atının üstünde genç Sultan "
 "II. Mehmed (21 yaşında, ince bıyıklı, kısa sakallı, gümüş zırh, kırmızı kaftan, beyaz sorguçlu miğfer), iki yanında "
 "yaya solaklar, sağ üzengisinde hocası Akşemseddin; arkada atlı vezirler ve paşalar, yeniçeri ağası. Alay caddeden "
 "kameraya doğru ilerledikçe kalabalık dalga dalga diz çöküyor. Alay caddenin ortasındaki küçük meydanda duruyor; "
 "mehter susuyor, ağır bir sessizlik. "
 f"Akşemseddin: \"{L1}\" Sultan: \"{L2}\" Sultan diz çökmüş binlerce kişiye bakıyor; anne oğlunu sıkıca tutuyor. "
 f"Sultan yüksek, sakin ve güven veren bir sesle: \"{L3}\" Binlerce kişi yavaşça ayağa kalkıyor; yine yüksek açıdan, "
 "bütün cadde. Kan, ceset, yaralı ya da yağma yok; ağırbaşlı, törensel ve gerçekçi.")

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
ALAY = ("The Sultan's ceremonial procession moves in strict order: at its head a mehter band on foot (kettle drums, big "
 "drums, zurnas, cymbals; red and green kaftans, tall caps) playing a slow, heavy march; then mounted heralds and "
 "standard-bearers with tall plain crimson banners bearing a single white crescent and a gilded alem finial; then the "
 "Sultan on his white horse, flanked on foot by two rows of solak guards in identical red kaftans and tall white plumed "
 "börk caps with bows across their backs, Akşemseddin walking at his right stirrup; behind him the viziers and pashas on "
 "horseback in long dark-green and deep-blue kaftans with large white turbans and grey beards, and the janissary ağa. "
 "Each group wears identical uniforms.")
MEKAN = ("A long, straight, gently rising street of worn stone paving inside Constantinople, seen from a high vantage "
 "point at its eastern end looking west down its whole length toward Topkapı. At the far end of the street the open "
 "brick-arched city gate in the land walls (pale limestone with red-brick bands) glows in hazy golden backlight. Both "
 "sides of the street are lined with two- and three-storey Byzantine stone-and-brick houses with timber balconies, "
 "wooden shutters and climbing vines. A continuous cordon of janissaries in crimson kaftans and tall white felt börk "
 "caps stands shoulder to shoulder along both edges of the street, facing inward, holding tall plain crimson banners "
 "that each bear only a single white crescent, no star and no writing. Behind the cordon, on the balconies and in the "
 "windows, thousands of townspeople stand packed and waiting: Greek men, women, old people and children on shoulders, "
 "in plain wool clothes of muted earth tones. The stone-paved centre of the street is empty. Halfway along, the street "
 "widens into a small square around an old marble fountain.")
ISIK = ("Late afternoon, June 1453. The sun is low in the west, directly behind the gate at the far end of the street: "
 "a long corridor of hazy golden light and drifting dust runs down the street, the facades and the crowd are in soft "
 "warm shade, and every figure in the middle of the street is rim-lit from behind.")
PALET = "crimson red, warm limestone cream, terracotta brick, earth-brown and grey wool, burnished silver, golden haze"
NO_TEXT = ("No readable text, signboards, logos or lettering anywhere in the frame, including on walls, houses and "
 "balconies; the banners carry only a single plain white crescent, with no star and no writing.")

kart = {
 "baslik": "Fethin Üçüncü Günü",
 "karakterler": [
  {"id": "K1", "ad": "Sultan II. Mehmed", "konusmaci": "S1", "gorunum": SULTAN_G, "kiyafet": SULTAN_K,
   "ses": "measured, resonant young baritone, calm and commanding, clear formal Istanbul Turkish"},
  {"id": "K2", "ad": "Akşemseddin", "konusmaci": "S2", "gorunum": AKS_G, "kiyafet": AKS_K,
   "ses": "warm, deep, slightly weathered baritone, slow and reverent, Istanbul Turkish"},
  {"id": "K3", "ad": "Rum anne ve oğlu", "konusmaci": "", "gorunum": ANNE_G, "kiyafet": ANNE_K, "ses": ""},
 ],
 "mekan": {"ad": "Topkapı'dan şehre uzanan cadde", "tarif": MEKAN},
 "zaman_isik": ISIK, "renk_paleti": PALET,
 "bloklar": [
  {"blok": 1, "sure": 15, "ozet": "High wide shot down the packed street: the ceremonial procession enters through the "
   "backlit gate, mehter playing. Then at street level among the waiting crowd: tense faces, the young mother with her "
   "son on her hip, the procession small and far away in the haze.", "replikler": []},
  {"blok": 2, "sure": 15, "ozet": "The procession advances up the street toward the camera in a symmetrical frontal "
   "composition, the Sultan centred on his white horse. As it passes, the crowd behind the cordon sinks to its knees in "
   "a wave. The procession halts in the small square; the mehter stops; heavy silence.", "replikler": []},
  {"blok": 3, "sure": 15, "ozet": "In the silent square, Akşemseddin looks up and speaks; the Sultan answers calmly. "
   "Close on the kneeling young mother pressing her son to her chest. The Sultan looks over the kneeling thousands.",
   "replikler": [{"konusmaci": "S2", "metin": L1}, {"konusmaci": "S1", "metin": L2}]},
  {"blok": 4, "sure": 15, "ozet": "The Sultan addresses the kneeling crowd in a loud, calm, reassuring voice. As he "
   "finishes, the thousands lift their heads and slowly rise, seen again from high above the whole street. No violence.",
   "replikler": [{"konusmaci": "S1", "metin": L3}]},
 ],
}
kart["_meta"] = {"fikir": FIKIR, "sure": 60, "stil": "real", "sahte": False,
                 "modeller": {"hikâye kartı": "elle yazıldı (Claude)"},
                 "olusturma": datetime.datetime.now().isoformat(timespec="seconds")}
sorun = hikaye.kart_denetle(kart, 60, FIKIR)
assert not sorun, sorun

def S(b, n, st, d, fr, act, cam, snd):
    return {"block": b, "shot": n, "start_sec": st, "duration": d, "framing": fr, "action": act, "camera": cam, "sound": snd}
HIGH = "High wide shot from a rooftop at the eastern end of the street, 24mm lens"
CROWD = "Street-level medium shot inside the crowd behind the cordon, 50mm lens"
FRONT = "Low symmetrical frontal wide shot in the middle of the street, 32mm lens"
TWO = "Medium two-shot of the Sultan and Akşemseddin, 50mm lens"
MCU = "Medium close-up of the Sultan from slightly below, 50mm lens"
shots = [
 S(1,1,0.0,8.0,HIGH,"The whole street: thousands waiting behind the janissary cordon; far away the procession enters through the backlit gate, mehter first.","Slow crane-down from the rooftop.","Distant heavy mehter march echoing off the houses, a vast uneasy murmur."),
 S(1,2,8.0,7.0,CROWD,"Tense faces in the crowd; the young mother with her son on her hip in the foreground; the procession small in the golden haze far down the street. Holds still for the final 1.5 seconds.","Locked-off, shallow depth of field.","The march grows louder; whispers, a child's question hushed."),
 S(2,1,0.0,6.0,CROWD,"Same framing as the end of block 1 for 1.5 seconds; then the mother turns her head toward the approaching music.","Locked-off.","The march, louder."),
 S(2,2,6.0,5.0,FRONT,"The procession advances toward the camera: mehter, standard-bearers, then the Sultan centred on his white horse between his solaks, Akşemseddin at his right stirrup.","Slow dolly back, keeping the Sultan centred.","The march, hoofbeats, banners in the wind."),
 S(2,3,11.0,4.0,FRONT,"The procession halts in the small square by the fountain; along both sides the crowd sinks to its knees in a wave. The march ends; everything holds still.","Locked-off.","A last drum beat; heavy silence; the rustle of thousands kneeling."),
 S(3,1,0.0,6.5,TWO,"Same moment as the end of block 2, closer: the Sultan motionless on his horse, rim-lit; after 1.5 seconds Akşemseddin looks up and speaks.","Locked-off.",f'Silence, wind; Akşemseddin (S2): "{L1}"'),
 S(3,2,6.5,4.0,MCU,"The Sultan breathes in and answers calmly, looking down at Akşemseddin.","Locked-off, slightly low.",f'The Sultan (S1): "{L2}"'),
 S(3,3,10.5,2.5,"Close-up of the kneeling young mother and her son, 50mm lens","She presses her son to her chest, trembling; her eyes lift toward the Sultan, then drop.","Locked-off.","Her shaky breath."),
 S(3,4,13.0,2.0,MCU,"The Sultan looks over the kneeling thousands; his stern face softens. Holds still.","Locked-off.","Silence."),
 S(4,1,0.0,10.5,MCU,"Same framing as the end of block 3 for 1.5 seconds; then the Sultan speaks to the crowd.","Locked-off.",f'The Sultan (S1): "{L3}"'),
 S(4,2,10.5,4.5,HIGH,"From high above: the whole street, the thousands lift their heads and slowly rise; the procession still in the square. Holds still for the final 0.5 seconds.","Slow crane-up.","The rustle of thousands standing, a relieved murmur rolling down the street."),
]
plan = {"world_anchor": hikaye.dunya_capasi(kart), "shots": shots}
gorseller = hikaye.gorsel_listesi(kart, MUSE_DIZIN + "/gorseller")
roller = [{"role": g["rol"], "name": g["ad"]} for g in gorseller]

DEF = ("subject_definitions:\n"
 f"<Subject 1> is Sultan II. Mehmed from <Picture 1> (Reference role: identity anchor): {SULTAN_G}. He wears a {SULTAN_K}. Follow his face, beard, armour, helmet and plume exactly; the plain background of <Picture 1> is not carried over.\n"
 f"<Subject 2> is Akşemseddin from <Picture 2> (Reference role: identity anchor): {AKS_G}. He wears a {AKS_K}. The background of <Picture 2> is not carried over.\n"
 f"<Subject 3> is the young Greek mother and her son from <Picture 3> (Reference role: identity anchor): {ANNE_G}; {ANNE_K}. The background of <Picture 3> is not carried over.\n"
 f"<Subject 4> is the street from <Picture 4> (Reference role: scene anchor): {MEKAN} Never create a main character from <Picture 4>; the janissary cordon and the waiting crowd stay along the sides exactly where <Picture 4> shows them.\n")
RET = ("retention_analysis:\n<Subject 1>: fully_preserved - face, beard, armour, helmet, plume and the white horse stay identical.\n"
 "<Subject 2>: fully_preserved - face, white beard, turban and navy robe stay identical.\n"
 "<Subject 3>: fully_preserved - the mother's face, veil, indigo dress and brown shawl, and the boy's curly hair and beige tunic stay identical.\n"
 "<Subject 4>: fully_preserved - the street, the houses, the gate at the far end, the janissary cordon and the crowd along the sides stay identical.\n")
STYLE = ("The target video is a photoreal historical feature film, shot on 35mm film with anamorphic lenses, natural light, "
 f"rich detail and real crowds of extras. {ISIK} Colour palette: {PALET}. {ALAY} Faces, armour, robes, the horse, "
 f"the street and the crowd stay exactly the same as in the reference pictures. {NO_TEXT}")

def prompt(summary, shots_txt, sound):
    return (DEF + "\nsummary:\n[reference generation] " + summary + "\n\n" + RET + "\ndetailed_description:\n" + STYLE
            + "\n" + shots_txt + "\n\noverall_soundscape:\n" + sound + "\n\nnon_diegetic_music:\nN/A")

P1 = prompt(
 "On the packed street of <Subject 4>, thousands wait behind the janissary cordon as the Sultan's ceremonial procession enters through the backlit gate; at street level, <Subject 3> waits among the crowd.",
 "[Shot 1] At 00:00.000, a high wide shot from a rooftop at the eastern end of the street, 24mm lens, with a slow crane-down. The whole length of <Subject 4> lies below: the empty stone-paved centre, the crimson janissary cordon with its single-crescent banners along both edges, thousands of townspeople packed behind it, on balconies and at windows, some children on their fathers' shoulders. At the far end, in the hazy golden backlight of the open gate, the procession enters: first the mehter band, then the mounted standard-bearers with banners and a gilded alem, then <Subject 1> on his white horse between two rows of solak guards, <Subject 2> walking at his right stirrup, the mounted pashas behind. Small figures, moving slowly and in strict order.\n"
 "[Shot 2] At 00:08.000, a locked-off street-level medium shot inside the crowd behind the cordon, 50mm lens, shallow depth of field. In the foreground <Subject 3> stands among tense, silent townspeople, her son on her hip; an old man beside her grips his cap; the red backs of the janissary cordon are just in front of them. Far down the street, out of focus in the golden haze, the procession approaches. At about 13.5 seconds everyone holds still until the end of the shot.",
 "A slow, heavy mehter march of kettle drums, zurnas and cymbals, distant at first and echoing off the stone houses, growing closer; the vast, uneasy murmur of thousands; at street level, whispers and a child's question hushed by its mother.")
P2 = prompt(
 "The procession advances up <Subject 4> toward the camera, <Subject 1> centred on his white horse; as it passes, the crowd sinks to its knees in a wave; it halts in the small square and silence falls.",
 "[Shot 1] At 00:00.000, a locked-off street-level medium shot inside the crowd, 50mm lens, exactly the framing of the end of the previous block: <Subject 3> with her son on her hip among the tense townspeople, the procession out of focus far down the street. For the first 1.5 seconds nobody moves. Then <Subject 3> slowly turns her head toward the approaching music, holding her son tighter.\n"
 "[Shot 2] At 00:06.000, a low symmetrical frontal wide shot in the middle of the street, 32mm lens, with a slow dolly back. The procession comes straight toward the camera in strict order: the mehter band playing, the mounted standard-bearers, then <Subject 1> perfectly centred on his white horse, rim-lit by the golden backlight, two rows of solak guards in red kaftans and white plumed caps on either side, <Subject 2> walking at his right stirrup, the mounted pashas behind; the janissary cordon and the crowd line both edges of the frame. Every horse walks with a natural four-beat gait.\n"
 "[Shot 3] At 00:11.000, the same frontal wide shot, locked-off. The procession halts in the small square by the old marble fountain; the band and standard-bearers step aside to both sides. Along both edges of the street the crowd behind the cordon sinks to its knees in a slow wave rolling outward from the Sultan. The march ends on a last deep drum beat and everything holds still.",
 "The heavy mehter march close and loud, hoofbeats on stone, banners snapping in the wind; then one last deep drum beat, the soft rustle of thousands of people kneeling, and a heavy silence.")
P3 = prompt(
 "In the silent square of <Subject 4>, <Subject 2> speaks to <Subject 1> and the Sultan answers; <Subject 3> kneels pressing her son to her chest; the Sultan looks over the kneeling thousands.",
 "[Shot 1] At 00:00.000, a locked-off medium two-shot, 50mm lens, of the same moment as the end of the previous block: <Subject 1> motionless on his white horse by the fountain, rim-lit by the golden backlight, <Subject 2> at his right stirrup on screen left, solak guards behind them and the kneeling crowd beyond. For the first 1.5 seconds nobody moves. At about 2 seconds, <Subject 2> looks up at the Sultan and, with a warm, deep, slightly weathered baritone voice and a slow reverent pace (S2), says: <d>[Turkish] " + L1 + "</d> His lips move only while he speaks.\n"
 "[Shot 2] At 00:06.500, a locked-off medium close-up of <Subject 1> from slightly below, 50mm lens, his face half in shade, the golden backlight on his white plume and armoured shoulders. He breathes in, looks down at <Subject 2>, and at about 7.5 seconds, with a measured, resonant young baritone voice (S1), says calmly: <d>[Turkish] " + L2 + "</d>\n"
 "[Shot 3] At 00:10.500, a locked-off close-up of <Subject 3>, 50mm lens: kneeling among the crowd, she presses her son's curly head to her chest with both arms, trembling; her eyes lift toward the Sultan for a moment, then drop.\n"
 "[Shot 4] At 00:13.000, a locked-off medium close-up of <Subject 1>: he looks over the kneeling thousands; his stern face softens. He holds completely still until the end of the shot.",
 "A deep silence over the whole street: faint wind, a horse snorting softly, the creak of saddle leather, the mother's shaky breath; the two spoken lines are close and clear.")
P4 = prompt(
 "<Subject 1> tells the kneeling crowd of <Subject 4> to rise and fear nothing; the thousands lift their heads and slowly stand, seen from high above the whole street.",
 "[Shot 1] At 00:00.000, a locked-off medium close-up of <Subject 1> from slightly below, 50mm lens, exactly the framing of the end of the previous block, rim-lit from behind. For the first 1.5 seconds he holds still. At about 1.5 seconds, with a loud, calm and reassuring measured young baritone voice (S1), he says to the crowd: <d>[Turkish] " + L3 + "</d> His lips move clearly and only while he speaks.\n"
 "[Shot 2] At 00:10.500, a high wide shot from the rooftop at the eastern end of the street, 24mm lens, with a slow crane-up: the whole length of <Subject 4> in the golden haze, the procession standing still in the small square, and on both sides thousands of townspeople lifting their heads and slowly rising to their feet behind the janissary cordon, <Subject 3> among them with her son. Everyone stands still for the final 0.5 seconds.",
 "The Sultan's voice carries across the silent street; then the vast soft rustle of thousands of people standing up, and a relieved murmur rolling down the street.")

bloklar = []
for b, p in zip(pw.blocks_from_plan(plan), (P1, P2, P3, P4)):
    ist = pw.block_request(b, style="real", idea=FIKIR)
    ist = "\n".join(("Signage rule: " + NO_TEXT) if l.startswith("Signage rule:") else l for l in ist.splitlines())
    probs = pw.check(p, ist, len(gorseller), "real", roles=roller)
    print("blok", b["block"], b["seconds"], "sn · sorunlar:", probs)
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
 "modeller": {"hikâye kartı": "elle yazıldı (Claude)", "H3 prompt'u": "elle yazıldı (Claude)"},
 "yedek_model": [], "notlar": ["Kart, çekim planı ve dört H3 prompt'u elle yazıldı; köprü kapalı."],
 "sahte": False, "durum": "hazir",
}
assert not senaryo["sorunlar"], senaryo["sorunlar"]
json.dump(kart, open(os.path.join(OUT, "hikaye.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
json.dump(senaryo, open(os.path.join(OUT, "uzun_senaryo.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("h3app_surum", senaryo["h3app_surum"], "·", ortak.tahmini_maliyet(senaryo, "a100"))
