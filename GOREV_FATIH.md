# Görev: Fatih'in İstanbul'a girişi — film sahnesi (60 sn, 4 blok, elle yazılmış senaryo)

**Depo:** https://github.com/g-user-s/Colab (dal `claude/trusting-johnson-c5d0tf`). Önce: `cd ~/workspace/Colab && git pull`.

**Önceki Fatih görevlerinin hepsi iptal.** `20261119_fatih` ve `20261119_fatih2` klasörlerindeki planları üretme.

## Sahne

Profesyonel bir tarih filmi sahnesi. Topkapı'dan şehrin içine uzanan uzun, taş döşeli bir cadde:
- iki kenarda omuz omuza yeniçeri kordonu ve tek beyaz hilalli, yıldızsız sancaklar;
- kordonun arkasında, balkonlarda ve pencerelerde **binlerce Rum** padişahı bekliyor.

Güneş caddenin sonundaki kapının arkasında: cadde boyunca puslu, altın bir ters ışık var.

**Tören alayı:**
- önde ağır bir marş çalan mehter takımı, atlı çavuşlar, sancaktarlar ve yaldızlı alem;
- beyaz atının üstünde Sultan II. Mehmed, iki yanında solaklar, sağ üzengisinde Akşemseddin;
- arkada atlı vezirler ve paşalar.

| Blok | Ne oluyor | Kamera |
|---|---|---|
| 1 (0–15) | Binlerce kişi bekliyor; alay ters ışıkta kapıdan giriyor. Kalabalığın içinde gergin yüzler, oğlunu kucağında tutan genç anne | Çatıdan yüksek geniş plan (yavaş vinç), sonra kalabalığın içinden sığ odak |
| 2 (15–30) | Alay kameraya doğru ilerliyor; geçerken kalabalık dalga dalga diz çöküyor; alay çeşmeli küçük meydanda duruyor, mehter susuyor | Simetrik, cepheden alçak açı, yavaş geri kaydırma |
| 3 (30–45) | Sessizlik; Akşemseddin ve Sultan konuşuyor; diz çökmüş annenin yakın planı; Sultan'ın yüzü yumuşuyor | İkili plan, yakın planlar |
| 4 (45–60) | Sultan'ın hitabı: "Kalkınız ve müsterih olunuz…"; binlerce kişi ayağa kalkıyor | Yakın plan; kapanışta yine çatıdan yüksek açı (yavaş vinç yukarı) |

Kart, çekim planı ve dört H3 prompt'u elle yazıldı. Dosyalar depoda hazır: `muse_gorevleri/20261119_fatih3/`. Üretici betik de aynı klasörde (`olustur.py`).

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
D=~/workspace/h3uretim/20261119_fatih3
mkdir -p $D
cp ~/workspace/Colab/muse_gorevleri/20261119_fatih3/hikaye.json ~/workspace/Colab/muse_gorevleri/20261119_fatih3/uzun_senaryo.json $D/
~/workspace/tools/h3muse-venv/bin/python -c "import json; s=json.load(open('$D/uzun_senaryo.json')); print(s['h3app_surum'], s['durum'], s['kopru'], [r['dosya'] for r in s['referanslar']])"
```

**Beklenen:** `f204aa2cbaab hazir False` ve dört yol, hepsi `/home/hatch/workspace/h3uretim/20261119_fatih3/gorseller/` altında.

**`plan` adımını ÇALIŞTIRMA.** Kartı ve `uzun_senaryo.json`'u elle düzenleme.

## 2. Görseller (4 tane)

```bash
cd ~/workspace/Colab
~/workspace/tools/h3muse-venv/bin/python muse/uzun_senaryo.py gorsel --dizin ~/workspace/h3uretim/20261119_fatih3 \
  --ilham K1=~/workspace/h3uretim/20261119_fatih/ilham/tablo.jpg \
  --ilham K2=~/workspace/h3uretim/20261119_fatih/ilham/tablo.jpg
```

MEKAN'a ilham verme. Kapı fotoğrafı yalnızca kapıyı gösteriyor; burada mekân caddenin kendisi, kapı onun en ucunda.

Kontrol et:
- **K1 (Sultan):** 21 yaşında; ince bıyık, kısa sakal; gümüş zırh, kırmızı kaftan, **beyaz sorguçlu** miğfer; tam boy, tek kişi, gerçekçi.
- **K2 (Akşemseddin):** ak sakal, beyaz sarık, lacivert cübbe; tam boy, tek kişi, gerçekçi.
- **K3 (anne ve oğlu):** 30 yaşlarında Rum kadın, ham keten başörtüsü, çivit yün elbise, kahverengi şal; **kucağında** 6 yaşlarında, kıvırcık saçlı, bej tunikli oğlu. Bu görselde iki kişi olması doğru.
- **MEKAN, en önemlisi:**
  - görüntü **yüksek açıdan, uzun caddenin doğu ucundan batıya**, kapıya bakıyor;
  - kapı caddenin en sonunda, puslu altın ters ışıkta;
  - iki kenarda yeniçeri kordonu ve **yıldızsız**, tek hilalli sancaklar;
  - kordonun arkasında, balkonlarda ve pencerelerde **ayakta bekleyen kalabalık**;
  - caddenin ortası **boş**: alay yok, Sultan yok, at yok;
  - ortalarda çeşmeli küçük bir meydan;
  - yazı yok.

Gerekirse `--yeniden` ile tekrar üret (her görsel için en fazla 2 kez). Dördünü orhan'a göster.

## 3. Onay mesajı

```
Fatih film sahnesi hazır: 60 sn, 4 blok, binlerce kişinin beklediği cadde, ters ışıkta giren tören alayı,
dalga dalga diz çöken kalabalık, hitap ve ayağa kalkış. Köprü kapalı, eşik yüksek.
GPU: A100 (yoksa G4). Tahmini ~52–96 dk, ~6–11 CCU. Güncel bakiye: <colab usage>. Görseller ekte. Başlayayım mı?
```

## 4. Üretim

```bash
~/workspace/tools/h3muse-venv/bin/python muse/h3_uret.py uret --senaryo ~/workspace/h3uretim/20261119_fatih3/uzun_senaryo.json \
  --oturum-dizini ~/workspace/h3uretim/20261119_fatih3/oturum --gpu a100,g4
```

## 5. İnceleme

Rapor ve süreklilik puanı. Sınır kareleri: 14,9 / 15,2 / 29,9 / 30,2 / 44,9 / 45,2.

```bash
cd ~/workspace/h3uretim/20261119_fatih3
for t in 14.9 15.2 29.9 30.2 44.9 45.2; do ffmpeg -v error -y -ss $t -i oturum/cikti/ref_pika_h3_flex_birlesik.mp4 -frames:v 1 sinir_$t.png; done
```

Modelin sınırını öğrenmek için şunları ayrı ayrı ve ayrıntılı yaz:
- **Kalabalık:** "binlerce" gibi duruyor mu? Kopya yüzler, birbirine kaynaşan figürler, bulanık "duvar kâğıdı" kalabalık var mı? Diz çökme dalgası (2. blok) ve ayağa kalkış (4. blok) gerçekçi mi?
- **Alay:** sıra doğru mu (mehter → çavuşlar ve sancaktarlar → Sultan ve solaklar → atlı paşalar)? Solaklar tek tip ve tutarlı mı?
- **Atlar:** yürüyüş doğal mı, bacaklar doğru mu, binici sabit mi?
- **Işık:** cadde boyunca ters ışık ve pus var mı? Sultan'ın kenarları parlıyor mu?
- **Kamera:** yüksek açı, simetrik cephe ve yakın planlar istenen gibi mi? Vinç ve kaydırma hareketleri oldu mu?
- **Anne:** yakın planı (3. blok, ~40,5–43. sn) K3'e uyuyor mu, eller doğal mı?
- **Sultan'ın sözü:** bölünmeden ~46,5–55. sn arasında mı, halk sonra mı kalkıyor?
- Sancaklarda yıldız ya da yazı var mı? Kan, ceset var mı?

## 6. Teslim ve sorular

Drive: `H3_Video_Studyosu/20261119_fatih3/`. Şunları yükle:
- birleşik video;
- `rapor.md`;
- `uzun_sonuc.json`;
- `hikaye.json`;
- `uzun_senaryo.json`;
- `gorseller/`;
- `_kontrol.jpg`;
- sınır kareleri.

orhan'a sor:
- **Film sahnesi gibi mi?** Işık, kamera, kalabalık, duygu, tarihî görünüm;
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
