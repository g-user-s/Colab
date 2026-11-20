"""Fatih'in İstanbul'a girişi — ANAHTAR KARE yöntemi (FL2VA), 2. sürüm. 1. sürümden farklar (20.11.2026 inceleme):
- Mekân plakası P_YOL: kapıyı gören bütün kareler bu ana kareden ya da tabandan türetilir (1. sürümde kapı her çekimde
  başka bir yapıydı); plakayı gören karelere MEKAN görseli ayrıca verilmez.
- Sancaklar sembolsüz, düz kırmızı ve yeşil (1. sürümde model hilali Türk bayrağına tamamladı: yıldız). "Yıldız" sözcüğü
  hiç yazılmaz; olumsuz ifade nesneyi çağırır.
- Anne çekimlerinde (C2, C8) kamera kapıya bakmaz: kapı kadraj dışında, ışık yandan.
Bundan sonrası 1. sürümün açıklaması: Aynı sahne (fatih4) 10 tek çekime bölünür; her çekimin
ilk ve son karesi önce Gemini ile görsel olarak üretilir (fatih4'ün karakter/mekân görselleri ve Zonaro tablosu girdi),
H3 iki kare arasını doldurur. Prompt'lar MiniMax H3 rehberinin FL2VA biçiminde (ilk satır hizalama talimatı, tek çekim).
Çalıştır: python3 muse_gorevleri/20261120_fatih_kare/olustur.py  →  aynı klasöre uzun_senaryo.json"""
import datetime, json, os, sys
DEPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(DEPO, "h3")); sys.path.insert(0, os.path.join(DEPO, "muse"))
os.environ.setdefault("H3APP_WORK_DIR", os.path.expanduser("~/.cache/h3muse"))
from h3app import kare
import ortak

MUSE_DIZIN = "/home/hatch/workspace/h3uretim/20261120_fatih_kare2"
F4 = "/home/hatch/workspace/h3uretim/20261119_fatih4/gorseller"
TABLO = "/home/hatch/workspace/h3uretim/20261119_fatih/ilham/tablo.jpg"
OUT = os.path.dirname(os.path.abspath(__file__))
kart = json.load(open(os.path.join(DEPO, "muse_gorevleri/20261119_fatih4/hikaye.json"), encoding="utf-8"))
kart = {k: v for k, v in kart.items() if not k.startswith("_")}

L1 = "Hünkârım, Peygamber efendimizin müjdesi bugün gerçek oldu."
L2 = "Bu zafer bizim değil, Allah'ındır."
L3 = ("Kalkınız ve müsterih olunuz. Ben Sultan Mehmed; hepinize söylüyorum ki bu andan itibaren ne hürriyetleriniz "
      "ne de hayatlarınız hakkında korkmayınız.")

AKS, SUL, ANNE, MEK = ({"etiket": "Akşemseddin (elderly scholar, white beard, white turban, navy robe)", "dosya": f"{F4}/K1.png"},
                       {"etiket": "Sultan Mehmed II and his white horse", "dosya": f"{F4}/K2.png"},
                       {"etiket": "the young Greek mother and her son", "dosya": f"{F4}/K3.png"},
                       {"etiket": "the place: the inner face of the gate, the road, the square, the cordon and the crowd", "dosya": f"{F4}/MEKAN.png"})
ISIK = ("Late afternoon, June 1453; the low sun is directly behind the gate: hazy golden light and dust pour through the "
        "arch toward the camera, the passage under the arch is in deep shade, every figure on the road is rim-lit.")
STIL = "Live-action, cinematic historical feature film, 35mm film with anamorphic lenses, natural light only"
SAHNE = ("the great limestone-and-red-brick arch of the city gate with its faded Byzantine fresco exactly as in the master plate, the stone road and "
         "square, the crimson janissary cordon with tall plain crimson and plain green silk banners with no emblem, and thousands of Greek townspeople behind it on rubble, roofs and the wall-walk")
BAYRAK = "Every banner is a plain solid crimson or plain solid green silk cloth with no emblem or mark of any kind."
YOK = (f"{BAYRAK} No readable text or calligraphy anywhere; no blood, wounds or bodies.")
# Kalabalığın içindeki çekimlerde kamera kapıya bakmaz: kapı kadrajın dışında, solda; ışık oradan yandan vurur.
ISIK_YAN = ("Late afternoon, June 1453; the camera faces away from the gate, which is out of frame to the left: the low "
            "sun shines from screen left, warm golden side light across faces and clothes, soft shade on the right side. "
            "Behind the people there are only more townspeople and the stone-and-brick wall of a house with a shuttered "
            "window.")

KARELER = []   # üretim sırası önemli: taban önce gelir


def K(kimlik, tarif, girdiler=(), taban=None, kompozisyon=None, ana=None, kapi=True, plaka=False):
    isik = ISIK if kapi else ISIK_YAN
    KARELER.append({"id": kimlik, "dosya": f"{MUSE_DIZIN}/kareler/{kimlik}.png", "tarif": f"{tarif} {CANLI_KARE if not plaka else ''} {isik} {YOK}".replace("  ", " "),
                    "girdiler": list(girdiler), "taban": taban, "kompozisyon": kompozisyon, "ana": ana,
                    "plaka": plaka})


CEKIMLER = []


# Kalabalık tablo gibi donmasın (orhan, 20.11.2026): her çekimde figüranlar kendi ritimleriyle küçük hareketler yapar.
CANLI = ("The crowd and the extras are never frozen: throughout the shot each person makes small, natural movements at "
         "their own rhythm (breathing, shifting weight, turning heads, whispering to a neighbour, adjusting a shawl, "
         "children fidgeting), while keeping their place.")
CANLI_KARE = ("Background people are caught in varied, candid mid-gesture poses, looking in slightly different "
              "directions, never posed uniformly.")


def C(n, sure, ilk, son, istek, aciklama, ses, muzik="N/A", replikler=()):
    p = kare.prompt_kur(sure, f"[Shot 1] {STIL}. {aciklama} {CANLI} {YOK}", ses, muzik)
    CEKIMLER.append({"blok": n, "sure": sure, "ilk": ilk, "son": son, "istek": istek, "prompt": p,
                     "sorunlar": kare.kontrol(p, sure, replikler=replikler)})


# ---------- Anahtar kareler ----------
K("P_YOL", "MASTER PLATE of the place (not used in the video): the inner, city-side face of the great gate seen from the "
  "middle of the stone road at standing eye level about forty metres away, 32mm lens, looking straight west into the "
  "gate along its axis. Keep the architecture of the reference image: the massive round arch of pale limestone with "
  "bands of red brick, scarred by cannon fire, the faded Byzantine fresco of a haloed figure on the plastered face "
  "above the arch, the wall and its towers. Through the deep shadowed passage the sky blazes white-gold. The road and "
  "the square in front of the gate are completely empty. A continuous cordon of janissaries in crimson kaftans and "
  "tall white felt börk caps lines both sides of the road, facing inward, holding tall plain crimson and plain green "
  "silk banners with no emblem; behind them thousands of townspeople stand packed on rubble, on the wall-walk, on flat "
  "roofs and in windows.", [MEK], plaka=True)
K("C1a", "A high wide view from a flat rooftop inside the city, about fifteen metres up, 24mm lens, looking straight "
  "along the road west into the gate. The great arch fills the upper middle of the frame and the sky beyond it blazes "
  "white-gold. The stone road and the wide square below are completely empty. Along both sides of the road stands the "
  "crimson janissary cordon with its tall crimson and green banners; behind it thousands of townspeople are packed on "
  "heaps of fallen masonry, on the wall-walk above the gate, on flat roofs and in windows, fathers holding children on "
  "their shoulders. The crowd is hushed but alive, most faces turned toward the gate.", ana="P_YOL")
K("C1b", "The camera has descended about five metres in the same shot: the arch now sits a little higher in the frame, "
  "the near roof edge has left the bottom of the frame, and the crowd along the road is closer and larger. The "
  "place is unchanged; in the crowd a few people have shifted, turned their heads or leaned to whisper.", taban="C1a")
K("C2a", "An eye-level medium shot inside the packed crowd standing at the side of the road, 50mm lens, shallow depth "
  "of field. Slightly right of centre stands the young mother in three-quarter view, holding her son on her hip, his "
  "face turned into her shoulder; her face is tense and she looks off-screen to the left, toward the gate. An old man "
  "beside her grips his cap with both hands. Behind them, softly out of focus, more silent townspeople stand packed "
  "shoulder to shoulder.", [ANNE], kapi=False)
K("C2b", "The mother has pulled her son tighter and lifted her chin, still looking off-screen to the left; the boy has "
  "turned his head to look the same way, and the people behind them crane their necks toward the left.",
  [ANNE], taban="C2a", kapi=False)
K("C3a", "A low frontal wide shot on the axis of the road, 32mm lens, facing the arch from about thirty metres. Out of "
  "the deep shade of the passage the mehter band marches toward the camera on foot in strict ranks: kettle drums and "
  "big drums carried on straps, zurnas raised, cymbals, red and green kaftans and tall caps. Behind them mounted "
  "standard-bearers hold tall crimson and green banners and a gilded alem finial. The cordon and the waiting crowd line "
  "both edges of the frame; the centre of the road is open.", ana="P_YOL")
K("C3b", "The band has advanced ten metres closer and is splitting to both sides of the road, leaving the centre open; "
  "behind them, inside the shadow of the arch, the white horse and the plumed rider are just becoming visible.",
  taban="C3a")
K("C4b", "Zonaro's composition as a real photograph. A low frontal wide shot on the axis of the road, 32mm lens, facing "
  "the arch. Sultan Mehmed II rides out of the shadow of the passage into the golden light straight toward the camera, "
  "slightly left of centre, on his tall white stallion; the horse steps high and proud, its mane and the Sultan's white "
  "plume rim-lit; he sits upright, his right hand slightly raised, his face calm. A few steps ahead of him on the left "
  "walks Akşemseddin, head bowed, right hand on his chest. Behind them the whole passage of the arch is packed with "
  "mounted pashas in large white turbans, solak guards in red kaftans and white plumed caps, and a dense forest of "
  "upright spears and crimson and green banners against the blazing white-gold sky. The faded fresco of a haloed figure "
  "hangs on the arch above them. In the left foreground, close to the lens, a guard in a red kaftan and a red-and-gold "
  "turban stands half turned toward the procession. The mehter band stands at both sides of the road.",
  [SUL, AKS], kompozisyon=TABLO, ana="P_YOL")
K("C4a", "A few seconds EARLIER in the same shot: the Sultan on his white horse and Akşemseddin are still deep inside "
  "the shadowed passage of the arch, about ten metres further back and smaller in the frame, seen mostly as rim-lit "
  "outlines with the white horse glowing faintly; the guard in the foreground, the arch, the soldiers, spears and "
  "banners behind and the band at the sides are exactly the same.", [SUL, AKS], taban="C4b")
K("C5a", "A wide shot from just behind the cordon on the left side of the road, 35mm lens, looking diagonally across "
  "the road toward the square, the arch blazing in the background on the left. In the foreground the townspeople stand "
  "packed behind the janissaries' red backs. In the middle ground the Sultan on his white horse rides from left to "
  "right, Akşemseddin walking at his right stirrup, solak guards on foot around them, mounted pashas following.",
  [SUL, AKS], ana="P_YOL")
K("C5b", "The Sultan has halted in the middle of the square, now at the centre of the frame, the procession standing "
  "still behind him. Every townsperson in the frame now kneels on the paving with head bowed; the janissaries remain "
  "standing.", [SUL], taban="C5a")
K("C6a", "A medium two-shot from the front-right of the halted procession, 50mm lens. The Sultan sits motionless on his "
  "white horse on the right of the frame, rim-lit by the golden light; Akşemseddin stands at his right stirrup on the "
  "left of the frame, looking up at him, lips closed. Behind them, softly out of focus, the great arch with its faded "
  "fresco and the massed spears and banners; solak guards in red kaftans beyond; kneeling townspeople at the edges.",
  [AKS, SUL], ana="P_YOL")
K("C6b", "Akşemseddin has finished speaking: his lips are closed and his head is bowed slightly lower; the Sultan "
  "looks down at him.", [AKS, SUL], taban="C6a")
K("C7a", "A medium close-up of the Sultan from slightly below, 50mm lens, chest up, on his white horse; his face half "
  "in warm shade, the golden backlight on his white plume and silver shoulders, the bright arch soft behind him. He "
  "looks down toward screen left, lips closed.", [SUL], ana="P_YOL")
K("C7b", "His lips are closed again after speaking and his gaze has lifted from screen left toward the crowd in front "
  "of him.", [SUL], taban="C7a")
K("C8a", "A close-up of the young mother kneeling on the stone paving among the crowd behind the cordon, 50mm lens: "
  "she presses her son's curly head to her chest with both arms, her eyes cast down, trembling; other kneeling "
  "townspeople soft behind her.", [ANNE], kapi=False)
K("C8b", "She has slowly lifted her eyes toward the Sultan off-screen right, lips parted, still holding her son tight; "
  "the boy has turned his face to look too.", [ANNE], taban="C8a", kapi=False)
K("C9a", "A medium shot of the Sultan from slightly below, 50mm lens, from the waist up with the white horse's neck "
  "and mane in the lower frame; he sits straight in the saddle and looks out over the kneeling crowd in front of him, "
  "lips closed; rim-lit, the blazing arch soft behind his shoulder.", [SUL], ana="P_YOL")
K("C9b", "The camera has pushed in: the framing is tighter, from the chest up; he has finished speaking, lips closed, "
  "his face calm and kind.", [SUL], taban="C9a")
K("C10a", "The same high rooftop view as the base frame, but now the procession stands halted in the middle of the "
  "square with the white horse at its centre, the mehter band and banners at the sides, and every townsperson along "
  "the road, on the rubble, on the roofs and on the wall-walk kneels with head bowed.", taban="C1b")
K("C10b", "The camera has risen about five metres: the arch sits lower in the frame and more of the city roofs are "
  "visible. Every townsperson now stands upright with head lifted; the procession is unchanged.", taban="C10a")

# ---------- Çekimler (her biri tek çekim, FL2VA) ----------
C(1, 5, "C1a", "C1b", "Damdan yüksek geniş plan: binlerce kişi sessizce bekliyor, kamera yavaşça alçalıyor.",
  f"A high wide shot from a rooftop inside the city; the shot begins exactly on Picture 1: {SAHNE}, the road and the "
  "square empty, thousands waiting in silence. The camera pedestals down with small amplitude at slow speed. The "
  "waiting crowd is alive with small natural movements: people shift their weight, lean to whisper, lift children "
  "higher and shade their eyes against the sun; the banners stir in the wind and dust drifts in the golden light "
  "pouring through the arch. A child on "
  "his father's shoulders turns his head toward the gate. The descent slows and the shot settles exactly into the "
  "framing of Picture 2.",
  "Wind over the rooftops, banners flapping, the vast low murmur of thousands of silent people; far beyond the walls, "
  "the slow heavy beat of mehter drums, muffled.",
  "A low sustained drone of bowed double basses at a very slow tempo.")
C(2, 5, "C2a", "C2b", "Kalabalığın içinde anne ve oğlu; mehter yaklaşıyor, herkes kapıya doğru bakıyor (kapı kadraj dışında).",
  "A static eye-level medium shot inside the packed crowd at the side of the road, 50mm lens, shallow depth of field, "
  "beginning on Picture 1: the young mother with her son on her hip among tense, silent townspeople, looking off-screen "
  "to the left toward the gate, warm low sunlight from the left on their faces; behind them only more townspeople and "
  "a house wall. The mehter music grows louder; she swallows and pulls her son tighter; the boy lifts his head and "
  "looks left, and the people behind them crane their necks the same way. The shot ends on Picture 2.",
  "The mehter march grows louder and echoes through the arch; close whispers are hushed; the boy breathes quickly "
  "against his mother's shoulder.",
  "A low sustained drone of bowed double basses, a soft frame-drum pulse joining underneath.")
C(3, 5, "C3a", "C3b", "Mehter takımı kemerden kameraya doğru çıkıyor, yolun iki yanına açılıyor.",
  "A low frontal wide shot on the axis of the road, 32mm lens, beginning on Picture 1: the mehter band marches out of "
  "the shadowed passage toward the camera in strict ranks, drummers striking the kettle drums and big drums, zurnas "
  "raised, cymbals flashing in the backlight, mounted standard-bearers with tall banners and a gilded alem behind them. "
  "The camera holds a static shot. The ranks advance with a heavy measured step and split to both sides of the road, "
  "opening the centre; deep in the shadow of the arch a white horse appears, and the shot ends on Picture 2.",
  "A loud, slow, heavy mehter march of kettle drums, big drums, zurnas and crashing cymbals echoing in the arch; "
  "marching feet on stone; banners snapping in the wind.")
C(4, 8, "C4a", "C4b", "Tablonun anı: Sultan beyaz atıyla kemerin gölgesinden ışığa, kameraya doğru çıkıyor.",
  "A low frontal wide shot on the axis of the road, 32mm lens, beginning on Picture 1: deep in the shadowed passage of "
  "the great arch, the rim-lit outlines of the Sultan on his white horse and of Akşemseddin walking ahead of him on the "
  "left; behind them mounted pashas in white turbans, solak guards and a forest of upright spears and crimson and green "
  "banners against the blazing white-gold sky; a guard in a red-and-gold turban in the left foreground. The camera "
  "pushes in with small amplitude at slow speed. The white stallion steps high and slow out of the shadow into the "
  "golden light, its mane and the Sultan's white plume catching the sun; the Sultan sits upright and slightly raises "
  "his right hand; Akşemseddin walks with his head bowed and his right hand on his chest. The horse walks with a natural "
  "four-beat gait. At the end the composition lands exactly on Picture 2, the moment of Zonaro's painting.",
  "The mehter march at full strength on both sides of the road, slow hoofbeats ringing on stone under the arch, harness "
  "jingling, banners in the wind, a rising murmur from thousands of people.",
  "N/A")
C(5, 5, "C5a", "C5b", "Sultan geçerken kalabalık dalga dalga diz çöküyor; alay meydanda duruyor.",
  "A wide shot from just behind the cordon, 35mm lens, beginning on Picture 1: the townspeople stand packed in the "
  "foreground as the Sultan rides from left to right across the middle ground on his white horse, Akşemseddin at his "
  "right stirrup. The camera pans right with small amplitude at slow speed, following him. As he passes, the crowd "
  "sinks to its knees in a slow wave that follows the horse. The Sultan halts in the middle of the square, the mehter "
  "ends on one last deep drum beat; the procession stands still while the kneeling crowd keeps breathing, trembling "
  "and glancing up as the shot ends on Picture 2.",
  "The mehter march, then one last deep drum beat; the soft rustle of thousands of people kneeling; hooves stop; a "
  "heavy silence with only wind.")
C(6, 6, "C6a", "C6b", "Akşemseddin başını kaldırıp Sultan'a konuşuyor.",
  "A static medium two-shot, 50mm lens, beginning on Picture 1: the Sultan motionless on his white horse on the right, "
  "rim-lit, Akşemseddin at his right stirrup on the left, the arch and the massed spears soft behind them. At about "
  "00:01.000, Akşemseddin, an elderly scholar with a warm, deep, slightly weathered baritone voice and a slow, "
  "reverent pace (S1), looks up at the Sultan and says: <d>[Turkish] " + L1 + "</d> His lips move only while he "
  "speaks; then he closes his mouth and bows his head slightly, and the shot ends on Picture 2.",
  "A deep silence over the square: faint wind through the arch, a horse snorting softly, the creak of saddle leather.",
  replikler=(L1,))
C(7, 5, "C7a", "C7b", "Sultan sakin bir sesle cevap veriyor.",
  "A static medium close-up of the Sultan from slightly below, 50mm lens, beginning on Picture 1: his face half in warm "
  "shade, the golden backlight on his white plume and silver shoulders. He breathes in, and at about 00:01.000, the "
  "young Sultan with a measured, resonant young baritone voice (S1) says calmly: <d>[Turkish] " + L2 + "</d> His lips "
  "then close and his gaze lifts toward the crowd, ending on Picture 2.",
  "Silence, faint wind, a banner flapping once; the horse shifts its weight.")
C(8, 5, "C8a", "C8b", "Diz çökmüş anne oğlunu göğsüne bastırıyor; gözlerini Sultan'a kaldırıyor.",
  "A static close-up of the young mother kneeling on the paving among the crowd, 50mm lens, facing away from the gate, "
  "beginning on Picture 1: "
  "she presses her son's curly head to her chest with both arms, trembling, eyes cast down. She takes a shaky breath, "
  "then slowly lifts her eyes toward the Sultan off-screen right, lips parting; the boy turns his face to look too. "
  "The shot ends on Picture 2.",
  "Silence; the mother's shaky breath; the soft rustle of cloth; far off, a horse snorts.")
C(9, 11, "C9a", "C9b", "Sultan'ın hitabı: Kalkınız ve müsterih olunuz…",
  "A medium shot of the Sultan from slightly below, 50mm lens, beginning on Picture 1: he sits straight in the saddle, "
  "rim-lit, the blazing arch soft behind his shoulder, looking out over the kneeling crowd. The camera pushes in with "
  "small amplitude at slow speed. At about 00:00.800, the young Sultan with a measured, resonant young baritone voice "
  "(S1), raised loud enough to carry across the square yet calm and reassuring, says: <d>[Turkish] " + L3 + "</d> His "
  "lips move clearly and only while he speaks; after the last word he holds still with a calm, kind face, and the shot "
  "ends on Picture 2.",
  "The Sultan's voice carries across the silent square and echoes softly in the arch; wind; the horse breathes.")
C(10, 5, "C10a", "C10b", "Yüksekten: binlerce kişi başını kaldırıp ayağa kalkıyor.",
  "A high wide shot from the rooftop on the axis of the road, beginning on Picture 1: the procession halted in the "
  "square with the white horse at its centre and thousands of townspeople kneeling everywhere along the road, on the "
  "rubble, on the roofs and on the wall-walk. The camera pedestals up with small amplitude at slow speed. Row after row, "
  "the people lift their heads and slowly rise to their feet, until the whole crowd stands, and the shot ends on "
  "Picture 2.",
  "The vast soft rustle of thousands of people standing up, a relieved murmur rolling through the crowd, wind.",
  "A slow, warm string chord swells gently and sustains to the end, with a single low ney note above it.")

assert sum(c["sure"] for c in CEKIMLER) == 60
ids = [k["id"] for k in KARELER]
sorun = kare.kare_denetle(KARELER)
assert not sorun, sorun
assert not any(w in json.dumps(KARELER + CEKIMLER).lower() for w in ("star", "crescent")), "sancak sembolü kaldı"
for c in CEKIMLER:
    print("çekim", c["blok"], c["sure"], "sn ·", round(kare.sure_sn(c["sure"]), 2), "·", len(c["prompt"].split()),
          "kelime · sorunlar:", c["sorunlar"])

senaryo = {
 "surum": 2, "tur": "uzun", "olusturma": datetime.datetime.now().isoformat(timespec="seconds"),
 "h3app_surum": ortak.h3app_surum(), "fikir": "Fatih'in İstanbul'a girişi — anahtar kare yöntemi, 2. sürüm (plaka, sembolsüz sancak, annede kapı yok)",
 "sure": 60, "stil": "real", "yontem": "pika", "cozunurluk": ortak.COZUNURLUKLER["yatay"], "seed": 22,
 "referanslar": [], "kareler": KARELER, "hikaye": kart,
 "dunya_capasi": "", "plan": {"shots": [{k: c[k] for k in ("blok", "sure", "ilk", "son", "istek")} for c in CEKIMLER]},
 "kollar": {"kare": {"ref": False, "kare": True, "bloklar": CEKIMLER}},
 "yeniden_uretim": 1, "kopru": False, "deney": False, "brief": "",
 "sorunlar": [s for c in CEKIMLER for s in c["sorunlar"]],
 "modeller": {"çekim planı ve prompt'lar": "elle yazıldı (Claude, MiniMax H3 rehberi FL2VA)"},
 "yedek_model": [], "notlar": ["Anahtar kare yöntemi 2. sürüm: 1 plaka + 20 anahtar kare, 10 tek çekim; köprü yok."],
 "sahte": False, "durum": "hazir",
}
assert not senaryo["sorunlar"], senaryo["sorunlar"]
json.dump(senaryo, open(os.path.join(OUT, "uzun_senaryo.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("h3app_surum", senaryo["h3app_surum"], "·", ortak.tahmini_maliyet(senaryo, "a100"))
