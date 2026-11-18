# Görev: ilk gerçek uzun video (45 sn, görsel referanslı)

**Depo:** https://github.com/g-user-s/Colab (dal `claude/trusting-johnson-c5d0tf`). Önce: `cd ~/workspace/Colab && git pull`.

**Amaç:** Bu bir deney değil, gerçek bir üretim. Deneyde kazanan yöntemi (`ref`: karakter ve mekân görselleriyle Ref2VA, bkz. `DENEY_SONUCLARI.md`) **yeniden üretim açıkken** çalıştırıyoruz. Görmek istediğimiz iki şey:

1. Üç blokluk bir videoda karakterler ve mekân baştan sona tutuyor mu?
2. Blok içi kusurlar (parmak, nesne, martı titremesi gibi) Gemini izlemesi ve yeni seed ile eleniyor mu?

**Tahmini maliyet:** A100'de 45–80 dk, **~5–9 CCU**. Alt sınır hiçbir blok yeniden üretilmezse, üst sınır her blok bir kez yeniden üretilirse geçerli. Gemini isteği ~15–20.

**Onay noktaları** (her zamanki kuralların geçerli):
1. Kart → orhan;
2. Görseller → orhan;
3. Üretim → orhan, tahmini CCU ile birlikte. Bu görevde orhan, kart ve görselleri onaylarken üretim onayını da verebilir.

Her adımda `MUSE_REHBERI.md` geçerli. Kopma olursa bölüm 7'yi uygula.

---

## 1. Hikâye kartı

```bash
cd ~/workspace/Colab
~/workspace/tools/h3muse-venv/bin/python muse/uzun_senaryo.py kart --dizin ~/workspace/h3uretim/20261118_sahaf --sure 45 --stil real --fikir 'Yağmurlu bir öğleden sonra, eski bir sahaf dükkânı; tavana kadar kitap dolu ahşap raflar, tezgâhta pirinç bir kasa, amber lambalar, camda yağmur damlaları. Gözlüklü, gri sakallı, tüvit yelekli sahaf Rıza bir rafın tozunu alıyor. Sarı yağmurluklu genç bir kız içeri girip "Eski haritalarınız var mı?" diye soruyor. Rıza gülümseyip "En güzelleri arka odada, bir dakika." diyor ve rafların arasından arkaya gidiyor. Kız tezgâhtaki eski kitapları karıştırıyor. Rıza elinde katlanmış, sararmış bir haritayla dönüyor ve haritayı tezgâha açıyor: "Bu, 1923 tarihli bir İstanbul haritası." Kız haritaya eğilip parmağıyla bir yeri gösteriyor: "Dedemin evi tam burasıymış." Rıza duygulanıp hafifçe başını sallıyor: "O zaman bu harita sizi bekliyormuş."'
```

Bu fikri değiştirme. Kartta şunları kontrol et:
- 3 blok, 15 + 15 + 15 sn;
- 5 replik harfi harfine aynı, konuşmacılar doğru (Rıza S1, kız S2);
- Türkçe harfler korunmuş ("Rıza", "dükkânı");
- `mekan.tarif` hikâye başlamadan önceki dükkânı anlatıyor: **harita mekânda olmamalı**, çünkü Rıza onu arka odadan getiriyor;
- kıyafetler ayırt edici ve bloklar boyunca aynı.

Bir şey yanlışsa `hikaye.json`'u elle düzelt (`_meta`'ya dokunma). Kartı orhan'a özetle.

## 2. Görseller

```bash
~/workspace/tools/h3muse-venv/bin/python muse/uzun_senaryo.py gorsel --dizin ~/workspace/h3uretim/20261118_sahaf
```

K1 (Rıza), K2 (kız) ve MEKAN'a bak:
- tam boy mu, tek kişi mi?
- karta uyuyor mu?
- mekânda insan, okunur yazı ve **harita** yok mu?

Gerekirse `--yeniden` (her görsel için en fazla 2 kez). Görselleri orhan'a göster.

## 3. Plan

```bash
~/workspace/tools/h3muse-venv/bin/python muse/uzun_senaryo.py plan --dizin ~/workspace/h3uretim/20261118_sahaf --kol ref
```

Beklenen: çıkış kodu 0, `kol: ref`, `"yeniden_uretim": 1`, `"deney": false`.

## 4. Onay mesajı

```
Uzun video hazır: "<başlık>", 45 sn, 3 blok, görsel referanslı (ref), yeniden üretim açık (blok başına en fazla 1).
GPU: A100 (yoksa G4). Tahmini süre 45–80 dk, ~5–9 CCU (G4'te ~7–13). Güncel bakiye: <colab usage>
Kart ve görseller ekte. Başlayayım mı?
```

## 5. Üretim

```bash
~/workspace/tools/h3muse-venv/bin/python muse/h3_uret.py uret --senaryo ~/workspace/h3uretim/20261118_sahaf/uzun_senaryo.json \
  --oturum-dizini ~/workspace/h3uretim/20261118_sahaf/oturum --gpu a100,g4
```

## 6. İnceleme

1. **Rapor:** `rapor.md` dosyasında her bloğun izleme sonucunu ve aday sayısını oku. Hangi bloklar yeniden üretildi ve neden? İlk ve ikinci adayın kusurlarını `oturum.json` → `incelemeler` alanından karşılaştır. Yeniden üretim kusuru gerçekten azalttı mı?
2. **Kare incelemesi:** birleşik videoya rehber bölüm 3, Adım 6'daki gibi tam çözünürlükte bak. Özellikle şunlara:
   - blok sınırları: 15. ve 30. saniyenin hemen öncesi ve sonrası;
   - Rıza'nın arkaya gidip haritayla dönmesi: aynı kişi mi, harita gelmeden önce tezgâhta harita var mı?
   - kızın parmağıyla gösterdiği an: eller doğal mı?
3. **Süreklilik puanı:** rapordaki kimlik, kıyafet, mekân, ses ve hikâye puanları.

## 7. Teslim

Drive'da `H3_Video_Studyosu/20261118_sahaf/` klasörüne şunları yükle ve boyutlarını doğrula:
- birleşik video;
- `rapor.md`;
- `uzun_sonuc.json`;
- `hikaye.json`;
- `gorseller/`;
- birleşik videonun `_kontrol.jpg` dosyası.

orhan'a videoyu izlemesi için bağlantıyı ver. Ona özellikle 15. ve 30. saniyelere bakmasını söyle.

## 8. Sonuç mesajı

```
UZUN VIDEO ÜRETİM SONUCU
- Video bağlantısı, süre, GPU, toplam süre, CCU öncesi → sonrası (rapordaki tahminle birlikte)
- Süreklilik puanları ve Gemini'nin süreklilik sorunları
- Blok blok: aday sayısı, yeniden üretim nedeni, ilk ve seçilen adayın kusurları
- Senin kare incelemen (blok sınırları, harita, eller), Gemini'den ayrı başlıkla
- Gemini istek sayısı, yedek model kullanımı, hatalar ve uyarılar (tam metin)
- Rehberde ya da betiklerde zorlandığın yer varsa
```
