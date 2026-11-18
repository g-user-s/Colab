# Uzun video deneyi: metin çapası ile görsel referans (18 Kasım 2026)

**Soru:** H3 tek seferde en fazla 15 sn üretir; uzun video ayrı üretilen bloklardan oluşur. Bloklar arasında karakterleri ve mekânı tutmak için hangisi daha iyi:
- **metin:** her bloğa aynı ayrıntılı tarif (dünya çapası) verilir, T2VA;
- **ref:** her bloğa ek olarak aynı karakter ve mekân görselleri verilir, Ref2VA.

**Düzen:** 30 sn, 2 blok (15 + 15), Pika H3 Flex, A100. Sahne: çay bahçesi, çaycı Ahmet ve genç bir kadın, 4 Türkçe replik.
- Hikâye kartı ve görseller `gemini-4-hydrogen` ve `gemini-3.1-flash-image` ile üretildi.
- İki kol aynı plan ve aynı seed'lerle, aynı runtime'da üretildi. Yeniden üretim kapalıydı.
- Değerlendirme üç bağımsız yoldan yapıldı:
  1. orhan'ın kör karşılaştırması (Muse yazı-tura ile video_N adları verdi);
  2. Gemini süreklilik puanı (1–10; kimlik, kıyafet, mekân, ses, hikâye);
  3. Muse'un tam çözünürlük kare incelemesi.

Deney iki kez yapıldı:
- **A:** mekân görselinde kadının masasında çay hazırdı;
- **B:** mekân görseli düzeltildi (masa boş), kart ve plan yeniden yazıldı.

## Sonuç

| | A metin | A ref | B metin | B ref |
|---|---|---|---|---|
| orhan (kör, 4 soru) | 0/4 | **4/4** | 0/4 | **4/4** |
| Gemini kimlik | 5 | 10 | 10 | 10 |
| Gemini kıyafet | 9 | 10 | 7 | 10 |
| Gemini mekân | 3 | 9 | 7 | 10 |
| Gemini ses | 7 | 10 | 10 | 10 |
| Gemini hikâye | 4 | 10 | 9 | 10 |
| **Gemini ortalama** | **5,6** | **9,8** | **8,6** | **10,0** |

**Blok sınırında (15,08 sn) görülenler:**
- **A metin:** tam kopuş. Başka bir adam (koyu saçlı, sakallı, daha genç), başka bir mekân (tenteli dükkân, okunur yazı), yuvarlak masa kareye dönüyor, kadının yüzü değişiyor.
- **B metin:** kayma. Saç rengi, kadının saçı ve pantolonu değişiyor, masa dikdörtgene dönüyor, çanta ve demlik beliriyor.
- **A ref:** kimlik, kıyafet ve mekân aynı. Kadrajda sıçrama var, masadaki bardak sayısı 1'den 2'ye çıkıyor.
- **B ref:** süreklilik kırılması yok. Bardak sayısı tutarlı (açılışta 0, sonra 1).

**Karar:** Uzun videoda varsayılan yöntem **ref** (Ref2VA, hikâye kartından üretilen karakter ve mekân görselleriyle). Metin yöntemi bloklar arasında rastgele bozuluyor; aynı plan iki koşuda farklı şiddette kırıldı.

## Kalan sorunlar (ref)

- **Blok içi kusurlar:** martı titremesi, parmak uzaması, tepsiyle etkileşimde katılık, hafif dudak senkronu kayması. Normal üretimde (`yeniden_uretim` 1) Gemini izlemesi kusurlu bloğu yeni seed ile tekrar üretir.
- **Mekân kuralı:** mekân görseli hikâye başlamadan önceki sahneyi göstermeli. Sonradan getirilen nesne görselde olmamalı (kart kuralı `hikaye.py`'de). A'da hazır bardak açılışa sızmadı, ama kural kalıyor.
- **Köprü** (önceki bloğun son karesi): B ref'te süreklilik zaten tam çıktığı için öncelik düşük.

## Maliyet

| Koşu | CCU |
|---|---|
| A | 7,25 |
| Başarısız B denemesi (iş başlatma zaman aşımı; düzeltildi: `77327ed`) | 0,11 |
| B2 (makine yeniden başladı, `devam` ile sürdü) | 6,59 |
| **Toplam** | **13,95** |

Bir uzun video deneyi (2 kol × 2 blok + birleştirme) A100'de yaklaşık 55–62 dk sürdü.
