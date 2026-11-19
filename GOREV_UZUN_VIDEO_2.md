# Görev: uzun video — aydınlık mutfak (köprü açık, kalite önceliği)

**Depo:** https://github.com/g-user-s/Colab (dal `claude/trusting-johnson-c5d0tf`). Önce: `cd ~/workspace/Colab && git pull`.

**Amaç:** Deney değil, gerçek üretim. Hedef: kaliteli ve devamlılık sorunu olmayan bir video. Bu görevde üç ayar varsayılandan farklı:

1. **Köprü açık** (artık varsayılan). Blok 2 ve 3'e önceki bloğun son karesi verilir; Gemini o bloğun prompt'unu bu kareye göre yeniden yazar. İlk köprü deneyinde 30. saniyedeki geçiş belirgin iyileşmişti.
2. **Kadraj sürekliliği** (yeni plan kuralı). Her blok, önceki bloğun bittiği kadraj, kamera konumu, kişi konumları ve ışıkla açılır; çekim boyu ancak bloğun ilk çekiminden sonra değişir. İlk deneyde 15. saniyede köprü işe yaramamıştı, çünkü plan yeni bloğu farklı bir çekim boyuyla açıyordu.
3. **Yeniden üretim eşiği "orta".** Bloklardaki el ve nesne kusurları da yeni seed ile bir kez tekrar denenir; betik en az kusurlu adayı seçer.

**Tahmini maliyet:**
- A100'de ~45–75 dk, **~6–9 CCU**; üst sınır, her blok bir kez yeniden üretilirse;
- Gemini ~15 istek.

**Onay noktaları:**
1. kart ve görseller;
2. üretim.

---

## 1. Kart

```bash
cd ~/workspace/Colab
~/workspace/tools/h3muse-venv/bin/python muse/uzun_senaryo.py kart --dizin ~/workspace/h3uretim/20261119_mutfak --sure 45 --stil real --fikir 'Sabah güneşinin bol girdiği, beyaz dolaplı, aydınlık bir mutfak; pencere önünde saksıda fesleğen, tezgâhta çaydanlık ve ahşap ekmek tahtası, pencere kenarında iki sandalyeli küçük beyaz bir masa. Ellili yaşlarda, kısa kahverengi saçlı, açık mavi gömlekli ve beyaz önlüklü anne ocağın başında çay demliyor. Gri tişörtlü, yirmili yaşlarda, kısa siyah saçlı oğlu mutfağa girip esniyor: "Günaydın anne, çay hazır mı?" Anne gülümsüyor: "Demleniyor, sen ekmeği kes." Oğul tezgâhta ekmeği kesiyor, anne bir tabağa beyaz peynir ve zeytin koyuyor. Oğul: "Bugün çok güzel bir gün olacak gibi." Anne çayları ince belli bardaklara doldurup pencere kenarındaki masaya getiriyor, ikisi karşılıklı oturuyor. Anne: "Her sabah böyle başlasa keşke." Oğul bardağını kaldırıp gülümsüyor: "Başlar anne, başlar."'
```

Fikri değiştirme. Kartta şunları kontrol et:
- 3 blok, 15 + 15 + 15 sn;
- 5 replik harfi harfine aynı; anne S1, oğul S2 (gerekirse elle düzelt);
- Türkçe harfler korunmuş;
- **mekân hikâye başlamadan önceki hâliyle:** masada çay bardağı, peynir ya da zeytin yok, ekmek kesilmemiş;
- **ışık:** sabah güneşi, aydınlık. "dim", "moody", "dusk", "low light" gibi bir tarif varsa düzelt; orhan karanlık sahneleri değerlendiremiyor.

Kartı orhan'a özetle.

## 2. Görseller

```bash
~/workspace/tools/h3muse-venv/bin/python muse/uzun_senaryo.py gorsel --dizin ~/workspace/h3uretim/20261119_mutfak
```

Kontrol et:
- K1 (anne) ve K2 (oğul): tam boy, tek kişi, karta uyuyor;
- MEKAN: **aydınlık**, insan yok, yazı yok, masa boş.

Gerekirse `--yeniden` (her görsel için en fazla 2 kez). Görselleri orhan'a göster.

## 3. Plan

```bash
~/workspace/tools/h3muse-venv/bin/python muse/uzun_senaryo.py plan --dizin ~/workspace/h3uretim/20261119_mutfak --kol ref
```

`uzun_senaryo.json` dosyasında şunları kontrol et:
- `"kopru": true`, `"yeniden_uretim": 1`, `"deney": false`;
- blok 2 ve blok 3'ün ilk çekimi (`plan.shots`, her bloğun `shot: 1` satırı), önceki bloğun son çekimiyle aynı kadrajı ve konumları tarif ediyor mu? Etmiyorsa raporda yaz; planı elle düzeltme.

## 4. Onay mesajı

```
Uzun video hazır: "<başlık>", aydınlık mutfak, 45 sn, 3 blok. Köprü açık, kadraj sürekliliği kuralı,
yeniden üretim eşiği orta (blok başına en fazla 1 tekrar).
GPU: A100 (yoksa G4). Tahmini ~45–75 dk, ~6–9 CCU. Güncel bakiye: <colab usage>. Kart ve görseller ekte. Başlayayım mı?
```

## 5. Üretim

```bash
~/workspace/tools/h3muse-venv/bin/python muse/h3_uret.py uret --senaryo ~/workspace/h3uretim/20261119_mutfak/uzun_senaryo.json \
  --oturum-dizini ~/workspace/h3uretim/20261119_mutfak/oturum --gpu a100,g4 --yeniden-esik orta
```

Günlükte şunlar olmalı:
- `Yüklendi: kopru_ref_2.png` ve `kopru_ref_3.png`;
- iki kez `köprü prompt'u yazılıyor`.

`köprü karesi eklendi; prompt yeniden yazılmadı` satırını görürsen dur ve bana bildir.

Not: Köprülü akışta bir blok yeniden üretilirse, köprü karesi seçilen adayın son karesinden alınır. Bu doğru davranış.

## 6. İnceleme

1. **Rapor:** her blokta kaç aday üretildi, neden, ilk ve seçilen adayın kusurları (`oturum.json` → `incelemeler`). Yeniden üretim kusuru azalttı mı?
2. **Süreklilik puanı** (Gemini).
3. **Sınır kareleri** (tam çözünürlük):
   ```bash
   cd ~/workspace/h3uretim/20261119_mutfak
   for t in 14.9 15.2 30.0 30.3; do ffmpeg -v error -y -ss $t -i oturum/cikti/ref_pika_h3_flex_birlesik.mp4 -frames:v 1 sinir_$t.png; done
   ```
   Her sınırda şunlara bak:
   - kişilerin konumu ve duruşu;
   - kamera açısı ve kadraj;
   - ışık;
   - nesneler: çaydanlık, ekmek, peynir tabağı, bardaklar.

   Geçiş tek bir çekimin devamı gibi mi, yoksa kesme gibi mi?
4. **Kare kare genel bakış** (rehber bölüm 3, Adım 6): kıyafet, eller, yazı, nesnelerin erken görünmesi.

## 7. Teslim

Drive'da `H3_Video_Studyosu/20261119_mutfak/` klasörüne şunları yükle ve boyutlarını doğrula:
- birleşik video;
- `rapor.md`;
- `uzun_sonuc.json`;
- `hikaye.json`;
- `gorseller/`;
- `_kontrol.jpg`;
- sınır kareleri.

orhan'a videoyu izlemesi için bağlantıyı ver ve şunları sor:
- 15. ve 30. saniyelerdeki geçişler akıcı mı? (Her biri için: akıcı / fark ediliyor ama rahatsız etmiyor / rahatsız ediyor.)
- Karakterler ve mekân baştan sona aynı mı?
- Gözüne batan bir şey oldu mu?

## 8. Sonuç mesajı

```
UZUN VIDEO 2 SONUCU (mutfak)
- Video bağlantısı, süre, GPU, toplam süre, CCU öncesi → sonrası (tahminle)
- Köprü satırları ve köprü prompt'larında ne değişti; kadraj sürekliliği planda nasıl yazıldı
- Süreklilik puanları ve Gemini'nin süreklilik sorunları
- Blok blok: aday sayısı, yeniden üretim nedeni, ilk ve seçilen adayın kusurları
- Senin sınır karesi incelemen ve genel kare incelemen (Gemini'den ayrı başlıkla)
- orhan'ın cevapları
- Gemini istek sayısı, hatalar ve uyarılar
```
