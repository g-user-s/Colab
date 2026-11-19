# Görev: Fatih'in İstanbul'a girişi — Zonaro'nun tablosunun canlı hâli (60 sn, 4 blok, elle yazılmış senaryo)

**Depo:** https://github.com/g-user-s/Colab (dal `claude/trusting-johnson-c5d0tf`). Önce: `cd ~/workspace/Colab && git pull`.

**Önceki Fatih görevlerinin hepsi iptal** (`20261119_fatih`, `fatih2`, `fatih3`). Yalnızca `20261119_fatih4`.

## Sahne

Fausto Zonaro'nun "Fatih'in İstanbul'a Girişi" tablosu, film sahnesi olarak canlanıyor. Mekân, Topkapı'nın **şehir içinden** görülen büyük kemeri:
- kireç taşı ve kırmızı tuğla bantlı, top izli; kemerin iç yüzünde solmuş bir Bizans freskosu;
- güneş kemerin arkasında: kemerin içinden altın ışık ve pus giriyor, alay ters ışıkta;
- kemerden şehre uzanan taş yol ve meydan; iki yanda yeniçeri kordonu, tek beyaz hilalli, yıldızsız kırmızı ve yeşil sancaklar;
- kordonun arkasında, yıkıntılarda, surun üstünde, damlarda ve pencerelerde **binlerce Rum** bekliyor.

| Blok | Ne oluyor | Kamera |
|---|---|---|
| 1 (0–15) | Sessiz bekleyiş; surların ötesinden mehter. Kalabalığın içinde anne ve oğlu; kemerden ilk sancaklar ve mehter çıkıyor | Damdan yüksek geniş plan, yavaş alçalma; sonra kalabalığın içinden sığ odak |
| 2 (15–30) | **Tablonun anı:** Sultan beyaz atıyla kemerin gölgesinden ışığa, kameraya doğru çıkıyor; önde solda Akşemseddin; arkada parlak göğe karşı mızrak ve sancak ormanı; ön planda solda kırmızı-altın sarıklı muhafız. Sonra kalabalık dalga dalga diz çöküyor, alay duruyor, sessizlik | Tablonun açısı: yol ekseninde alçak cephe, yavaş itme; sonra yandan takip |
| 3 (30–45) | Akşemseddin ve Sultan konuşuyor (arkada kemer); diz çökmüş annenin yakın planı; Sultan'ın yüzü yumuşuyor | İkili plan, yakın planlar |
| 4 (45–60) | Sultan'ın hitabı: "Kalkınız ve müsterih olunuz…"; binlerce kişi ayağa kalkıyor | Yakın plan; kapanışta damdan yüksek açı, yavaş yükselme |

Prompt'lar MiniMax'in resmî H3 prompt rehberine göre yazıldı:
- altı bölüm doğru sırada;
- her blokta 350–500 kelimelik ayrıntılı tarif;
- rehberin kamera dili;
- konuşmacılar filmdeki konuşma sırasıyla: Akşemseddin S1, Sultan S2.

Blok sınırları bilinçli kesmelerdir: her blok farklı bir açıyla başlar. Dosyalar depoda hazır: `muse_gorevleri/20261119_fatih4/` (üretici betik `olustur.py`).

**Ayarlar:**
- 60 sn, 4 blok, görsel referanslı (ref), Pika, seed 22;
- eşik **yüksek**;
- **köprü kapalı** (Gemini prompt'u yeniden yazıp elle yazılmış ayrıntıyı kaybederdi).

**Tahmini maliyet:**
- A100'de ~52–96 dk, **~6–11 CCU**;
- Gemini ~9 istek: 4 görsel, 4 blok izlemesi, 1 süreklilik.

**Önemli:** Bu sahne H3'te ilk kez büyük bir kalabalık ve atlı bir alay deniyor. Modelin buradaki sınırını henüz bilmiyoruz; bu üretim onu gösterecek. Gözlemlerini ayrıntılı yaz.

**Onay noktaları:**
1. görseller;
2. üretim.

---

## 1. Dosyaları yerleştir

```bash
D=~/workspace/h3uretim/20261119_fatih4
mkdir -p $D
cp ~/workspace/Colab/muse_gorevleri/20261119_fatih4/hikaye.json ~/workspace/Colab/muse_gorevleri/20261119_fatih4/uzun_senaryo.json $D/
~/workspace/tools/h3muse-venv/bin/python -c "import json; s=json.load(open('$D/uzun_senaryo.json')); print(s['h3app_surum'], s['durum'], s['kopru'], [r['dosya'] for r in s['referanslar']])"
```

**Beklenen:** `f204aa2cbaab hazir False` ve dört yol, hepsi `/home/hatch/workspace/h3uretim/20261119_fatih4/gorseller/` altında.

**`plan` adımını ÇALIŞTIRMA.** Kartı ve `uzun_senaryo.json`'u elle düzenleme.

## 2. Görseller (4 tane)

Sıra değişti: **K1 Akşemseddin, K2 Sultan**, K3 anne ve oğlu, MEKAN.

```bash
cd ~/workspace/Colab
~/workspace/tools/h3muse-venv/bin/python muse/uzun_senaryo.py gorsel --dizin ~/workspace/h3uretim/20261119_fatih4 \
  --ilham K1=~/workspace/h3uretim/20261119_fatih/ilham/tablo.jpg \
  --ilham K2=~/workspace/h3uretim/20261119_fatih/ilham/tablo.jpg \
  --ilham MEKAN=~/workspace/h3uretim/20261119_fatih/ilham/kapi.jpg
```

Bu kez MEKAN'a kapı fotoğrafını ilham olarak **ver**: mekân artık kapının kendisi.

Kontrol et:
- **K1 (Akşemseddin):** ak sakal, beyaz sarık, lacivert cübbe; tam boy, tek kişi, gerçekçi.
- **K2 (Sultan):** 21 yaşında; ince bıyık, kısa sakal; gümüş zırh, kırmızı kaftan, **beyaz sorguçlu** miğfer; tam boy, tek kişi, gerçekçi.
- **K3 (anne ve oğlu):** 30 yaşlarında Rum kadın, ham keten başörtüsü, çivit yün elbise, kahverengi şal; **kucağında** 6 yaşlarında, kıvırcık saçlı, bej tunikli oğlu. Bu görselde iki kişi olması doğru.
- **MEKAN, en önemlisi:**
  - görüntü **şehrin içinden, göz hizasından**, kemere tam karşıdan bakıyor;
  - kemer kadrajın üst ortasını dolduruyor: taş ve tuğla bantlar, top izleri, iç yüzde **solmuş fresko**;
  - kemerin içinden parlak altın gökyüzü, kemerin altı gölgede;
  - iki yanda yeniçeri kordonu ve **yıldızsız**, tek hilalli kırmızı ve yeşil sancaklar;
  - kordonun arkasında, yıkıntılarda, surun üstünde, damlarda **ayakta bekleyen kalabalık**;
  - yolun ve meydanın ortası **boş**: alay yok, Sultan yok, at yok;
  - yazı yok, ceset yok, modern bir şey yok.

Gerekirse `--yeniden` ile tekrar üret (her görsel için en fazla 2 kez). Dördünü orhan'a göster.

## 3. Onay mesajı

```
Fatih film sahnesi hazır (Zonaro'nun tablosunun canlı hâli): 60 sn, 4 blok, binlerce kişinin beklediği Topkapı, ters ışıkta kemerden giren tören alayı,
dalga dalga diz çöken kalabalık, hitap ve ayağa kalkış. Köprü kapalı, eşik yüksek.
GPU: A100 (yoksa G4). Tahmini ~52–96 dk, ~6–11 CCU. Güncel bakiye: <colab usage>. Görseller ekte. Başlayayım mı?
```

## 4. Üretim

```bash
~/workspace/tools/h3muse-venv/bin/python muse/h3_uret.py uret --senaryo ~/workspace/h3uretim/20261119_fatih4/uzun_senaryo.json \
  --oturum-dizini ~/workspace/h3uretim/20261119_fatih4/oturum --gpu a100,g4
```

## 5. İnceleme

Rapor ve süreklilik puanı. Sınır kareleri: 14,9 / 15,2 / 29,9 / 30,2 / 44,9 / 45,2.

```bash
cd ~/workspace/h3uretim/20261119_fatih4
for t in 14.9 15.2 29.9 30.2 44.9 45.2; do ffmpeg -v error -y -ss $t -i oturum/cikti/ref_pika_h3_flex_birlesik.mp4 -frames:v 1 sinir_$t.png; done
```

Modelin sınırını öğrenmek için şunları ayrı ayrı ve ayrıntılı yaz:
- **Kalabalık:** "binlerce" gibi duruyor mu? Kopya yüzler, birbirine kaynaşan figürler, bulanık "duvar kâğıdı" kalabalık var mı? Diz çökme dalgası (2. blok) ve ayağa kalkış (4. blok) gerçekçi mi?
- **Alay:** sıra doğru mu (mehter → çavuşlar ve sancaktarlar → Sultan ve solaklar → atlı paşalar)? Solaklar tek tip ve tutarlı mı?
- **Atlar:** yürüyüş doğal mı, bacaklar doğru mu, binici sabit mi?
- **Işık:** kemerden gelen ters ışık ve pus var mı? Sultan'ın kenarları parlıyor mu?
- **Tablo anı (2. blok, 15–24. sn):** Zonaro'nun tablosuna benziyor mu? Kemerin gölgesinden ışığa çıkış, önde solda Akşemseddin, arkada mızrak ve sancak ormanı, ön planda muhafız, freskolu kemer.
- **Kamera:** yüksek açı, tablo açısı ve yakın planlar istenen gibi mi? Alçalma, itme, takip ve yükselme hareketleri oldu mu?
- **Anne:** yakın planı (3. blok, ~40,5–43. sn) K3'e uyuyor mu, eller doğal mı?
- **Sultan'ın sözü:** bölünmeden ~46,5–55. sn arasında mı, halk sonra mı kalkıyor?
- Sancaklarda yıldız ya da yazı var mı? Kan, ceset var mı?

## 6. Teslim ve sorular

Drive: `H3_Video_Studyosu/20261119_fatih4/`. Şunları yükle:
- birleşik video;
- `rapor.md`;
- `uzun_sonuc.json`;
- `hikaye.json`;
- `uzun_senaryo.json`;
- `gorseller/`;
- `_kontrol.jpg`;
- sınır kareleri.

orhan'a sor:
- **Film sahnesi gibi mi, tablonun canlı hâli gibi mi?** Işık, kamera, kalabalık, duygu, tarihî görünüm;
- **geçişler** (15., 30. ve 45. sn): akıcı / fark ediliyor ama rahatsız etmiyor / rahatsız ediyor;
- **gözüne batan:** ne varsa.

## 7. Sonuç mesajı

Başlık `FATİH SONUCU`. Şunları içersin:
- video bağlantısı;
- GPU, süre, CCU;
- süreklilik puanları;
- blok blok adaylar ve kusurlar;
- 5. adımdaki gözlemlerin;
- orhan'ın cevapları;
- hatalar ve uyarılar.
