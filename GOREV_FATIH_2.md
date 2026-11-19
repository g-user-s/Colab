# Görev: Fatih'in İstanbul'a girişi — elle yazılmış senaryo (60 sn, 4 blok)

**Depo:** https://github.com/g-user-s/Colab (dal `claude/trusting-johnson-c5d0tf`). Önce: `cd ~/workspace/Colab && git pull`.

**Neden yeni görev:** Önceki planı (`20261119_fatih`) uzman gözüyle inceledik; üretimi bozacak sorunlar çıktı:
- 3. blokta Sultan'ın sözü geç başlıyordu (prompt'ta 4,5 sn yazıyordu, olması gereken 2,5 sn) ve halkın ayağa kalkmasıyla çakışıyordu;
- yeniçerilere konuşmacı kimliği (S4) verilmişti;
- yazı yasağı yanlış kurala düşmüştü;
- 2. ve 3. blokların prompt'ları 1. bloğa göre çok zayıftı;
- tek mekân görseli kapıyı dışarıdan gösteriyordu, ama 3. blok içeride geçiyordu;
- güneş yönü fiziksel olarak yanlıştı;
- duygusal sahneler (korku, tepki planları) yoktu.

**Bu kez kart, çekim planı ve dört H3 prompt'u elle yazıldı.** Dosyalar depoda hazır: `muse_gorevleri/20261119_fatih2/`. Gemini bu görevde yalnızca görsel üretir ve videoyu izler; senaryo ve plan yazmaz.

**Yeni kurgu:**
- **Kamera yönü:** bütün sahne şehrin içinden, kapının kemerinden dışarı (batıya) bakan kameralarla çekiliyor (Zonaro'nun bakışı).
- **Işık:** güneş kapının arkasında; Sultan kemerden ters ışıkla, kenarları parlayan bir siluet olarak giriyor, meydan gölgede.
- **Duygusal odak:** oğlunu bağrına basan genç bir Rum anne, kendi görseliyle sabitlenen sessiz bir karakter (K3).
- **Tören alayı:**
  - önde ağır bir marş çalan mehter takımı (kös, zurna, zil), atlı çavuşlar, sancaktarlar ve yaldızlı alem;
  - Sultan'ın iki yanında yaya solaklar (kırmızı kaftan, beyaz sorguçlu börk, sırtta yay), sağ üzengisinde Akşemseddin;
  - arkada atlı vezirler ve paşalar, yeniçeri ağası ve yeniçeriler.

  Her grup tek tip giyinik. Kalabalık geniş planlarda görünüyor, yakın planlarda az kişi var.

**Bloklar:**
1. Tören alayının kemerin ardından yaklaşması; mehter kapının önünde susuyor.
2. Kemerin altında iki replik.
3. Meydana çıkış: kalabalığın görülmesi, annenin yakın planı, Sultan'ın yüzünün yumuşaması.
4. Sultan'ın hitabı ve halkın ayağa kalkması.

**Ayarlar:**
- 60 sn, 4 blok, görsel referanslı (ref), Pika, seed 22;
- yeniden üretim eşiği **yüksek**;
- **köprü kapalı.** Köprüde Gemini blok prompt'unu yeniden yazar; elle yazılmış bu ayrıntıyı kaybederdi. Her blok zaten önceki bloğun son kadrajıyla ve 1,5 sn'lik sabit bir açılışla başlıyor.

**Tahmini maliyet:**
- A100'de ~55–100 dk, **~6–11 CCU**;
- Gemini ~9 istek: 4 görsel, 4 blok izlemesi, 1 süreklilik.

**Onay noktaları:**
1. görseller;
2. üretim.

---

## 1. Dosyaları yerleştir

```bash
D=~/workspace/h3uretim/20261119_fatih2
mkdir -p $D/ilham
cp ~/workspace/Colab/muse_gorevleri/20261119_fatih2/hikaye.json ~/workspace/Colab/muse_gorevleri/20261119_fatih2/uzun_senaryo.json $D/
cp ~/workspace/h3uretim/20261119_fatih/ilham/kapi.jpg ~/workspace/h3uretim/20261119_fatih/ilham/tablo.jpg $D/ilham/
~/workspace/tools/h3muse-venv/bin/python -c "import json; s=json.load(open('$D/uzun_senaryo.json')); print(s['h3app_surum'], s['durum'], s['kopru'], [r['dosya'] for r in s['referanslar']])"
```

**Beklenen:**
- `f204aa2cbaab hazir False` ve dört görsel yolu, hepsi `/home/hatch/workspace/h3uretim/20261119_fatih2/gorseller/` altında;
- kullanıcı adın `hatch` değilse dur ve bana bildir.

**`plan` adımını ÇALIŞTIRMA.** Plan, elle yazılmış prompt'ların üzerine Gemini'nin yazdığını koyar. Kartı ve `uzun_senaryo.json`'u da elle düzenleme.

## 2. Görseller (4 tane, ilhamlı)

```bash
cd ~/workspace/Colab
~/workspace/tools/h3muse-venv/bin/python muse/uzun_senaryo.py gorsel --dizin ~/workspace/h3uretim/20261119_fatih2 \
  --ilham MEKAN=~/workspace/h3uretim/20261119_fatih2/ilham/kapi.jpg \
  --ilham K1=~/workspace/h3uretim/20261119_fatih2/ilham/tablo.jpg \
  --ilham K2=~/workspace/h3uretim/20261119_fatih2/ilham/tablo.jpg
```

Dünkü görev için üretilip orhan'ın onayladığı K1 ve K2 görselleri varsa, Gemini isteğinden tasarruf için onları `--ref K1=…/20261119_fatih/gorseller/K1.png --ref K2=…/K2.png` ile kullanabilirsin.

Kontrol et:
- **K1 (Sultan):** 21 yaşında; ince bıyık, kısa sakal; gümüş zırh, kırmızı kaftan, **beyaz sorguçlu** miğfer; tam boy, tek kişi, gerçekçi.
- **K2 (Akşemseddin):** ak sakal, beyaz sarık, lacivert cübbe; tam boy, tek kişi, gerçekçi.
- **K3 (anne ve oğlu):** 30 yaşlarında Rum kadın, ham keten başörtüsü, solgun çivit yün elbise, kahverengi şal; kucağında 6 yaşlarında, kıvırcık saçlı, bej tunikli oğlu. Tam boy, gerçekçi. Bu görselde iki kişi olması doğru.
- **MEKAN, en önemlisi:**
  - görüntü **şehrin içinden, kapının kemerinden dışarı bakıyor**;
  - kemerin ardında güneşli toprak yol ve yolun iki yanında saf tutmuş yeniçeriler, tek beyaz hilalli, **yıldızsız** sancaklar;
  - önde, gölgede, **boş** meydan ve taş evler;
  - güneş kapının arkasında (ters ışık);
  - kapı kanatları açık;
  - halk, Sultan, at ve yazı yok.

  Görsel kapıyı dışarıdan gösteriyorsa ya da meydanda insan varsa `--yeniden MEKAN --ilham MEKAN=…` ile yeniden üret.

Her görsel için en fazla 2 kez yeniden üret. Dördünü orhan'a göster.

## 3. Onay mesajı

```
Fatih videosu hazır (elle yazılmış senaryo): 60 sn, 4 blok, kamera şehrin içinden kemerden dışarı bakıyor,
ters ışık, sessiz Rum anne karakteri. Köprü kapalı, eşik yüksek.
GPU: A100 (yoksa G4). Tahmini ~55–100 dk, ~6–11 CCU. Güncel bakiye: <colab usage>. Görseller ekte. Başlayayım mı?
```

## 4. Üretim

```bash
~/workspace/tools/h3muse-venv/bin/python muse/h3_uret.py uret --senaryo ~/workspace/h3uretim/20261119_fatih2/uzun_senaryo.json \
  --oturum-dizini ~/workspace/h3uretim/20261119_fatih2/oturum --gpu a100,g4
```

## 5. İnceleme

Rapor ve süreklilik puanı her zamanki gibi. Sınır kareleri: 14,9 / 15,2 / 29,9 / 30,2 / 44,9 / 45,2.

```bash
cd ~/workspace/h3uretim/20261119_fatih2
for t in 14.9 15.2 29.9 30.2 44.9 45.2; do ffmpeg -v error -y -ss $t -i oturum/cikti/ref_pika_h3_flex_birlesik.mp4 -frames:v 1 sinir_$t.png; done
```

Bu videoya özel olarak şunlara bak ve her birini ayrı yaz:
- **Işık:** Sultan kemerde ters ışıkla, kenarları parlayan bir siluet mi? Meydan gölgede mi?
- **Yön:** halk hep kapının **içinde**, meydanda mı? Yeniçeriler dışarıda, yolda mı?
- **At:** yürüyüşü doğal mı, binici sabit mi?
- **Anne yakın planı** (3. blok, ~39–42. sn): yüz ve çocuk K3'e uyuyor mu, eller doğal mı?
- **Sultan'ın sözü** (4. blok): bölünmeden ~46,5–55. sn arasında söyleniyor mu, halk ondan **sonra** mı kalkıyor?
- **Alay:** sıra doğru mu (mehter, çavuşlar ve sancaktarlar, Sultan ve solaklar, atlı paşalar)? Solaklar bloklar boyunca aynı mı? Kalabalıkta kopya yüzler ya da birbirine kaynaşan figürler var mı? Mehter sesi 1. bloğun sonunda susuyor mu?
- Sancaklarda yıldız ya da yazı var mı? Vezirler bloklar boyunca aynı mı? Kan, ceset var mı?

## 6. Teslim ve sorular

Drive: `H3_Video_Studyosu/20261119_fatih2/`. Şunları yükle:
- birleşik video;
- `rapor.md`;
- `uzun_sonuc.json`;
- `hikaye.json`;
- `uzun_senaryo.json`;
- `gorseller/`;
- `_kontrol.jpg`;
- sınır kareleri.

orhan'a sor:
- **Geçişler** (15., 30. ve 45. sn): akıcı / fark ediliyor ama rahatsız etmiyor / rahatsız ediyor;
- **film sahnesi gibi mi?** Işık, kamera, duygu, tarihî görünüm;
- **gözüne batan:** ne varsa.

## 7. Sonuç mesajı

Başlık `FATİH 2 SONUCU`. İçerik `UZUN VIDEO 2 SONUCU`'ndaki başlıklar, ayrıca 5. adımdaki özel gözlemler ve görsellerin ilhama ne kadar uyduğu.
