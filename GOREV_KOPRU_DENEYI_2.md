# Görev: köprü deneyi 2 — aydınlık sahne, 3 blok

**Depo:** https://github.com/g-user-s/Colab (dal `claude/trusting-johnson-c5d0tf`). Önce: `cd ~/workspace/Colab && git pull`.

**Neden tekrar:** İlk köprü deneyinin sahnesi (yağmurlu, loş sahaf) fazla karanlıktı. orhan videoları değerlendiremedi. Bu deneyde sahne aydınlık, yüzler net. Bloklar arasındaki hareket de devam ediyor, böylece geçişin akıcılığı görülebiliyor.

**Soru:** 3 blokluk 45 sn'lik bir videoda, blok geçişleri (15. ve 30. saniye) köprüyle daha akıcı olur mu?

**Düzen:** Aynı senaryo, aynı plan, aynı görseller ve aynı seed'ler. İki koşu yapılır, tek fark köprü:
- **Kol A:** köprüsüz;
- **Kol B:** köprülü.

Yeniden üretim iki kolda da kapalı; koşullar eşit kalsın.

**Tahmini maliyet:**
- A100'de iki koşu toplam ~80–100 dk, **~10–11 CCU**;
- Gemini ~20 istek: kart, 3 görsel, plan ve prompt'lar, 2 köprü prompt'u, 6 blok izlemesi, 2 süreklilik.

**Onay noktaları:**
1. kart ve görseller;
2. üretim (iki koşunun toplam maliyetiyle).

**Körlük kuralı:** Kör karşılaştırmada orhan cevap verene kadar **hangi videoda ne gördüğünü yazma**. Kare incelemeni yap, ama dosyada tut; eşleşmeyle birlikte açıkla. İlk deneyde inceleme raporu eşleşmeyi ele veriyordu.

---

## 1. Kart

```bash
cd ~/workspace/Colab
D=~/workspace/h3uretim/20261119_mutfak
~/workspace/tools/h3muse-venv/bin/python muse/uzun_senaryo.py kart --dizin $D --sure 45 --stil real --fikir 'Sabah güneşinin bol girdiği, beyaz dolaplı, aydınlık bir mutfak; pencere önünde saksıda fesleğen, tezgâhta çaydanlık ve ahşap ekmek tahtası, pencere kenarında iki sandalyeli küçük beyaz bir masa. Ellili yaşlarda, kısa kahverengi saçlı, açık mavi gömlekli ve beyaz önlüklü anne ocağın başında çay demliyor. Gri tişörtlü, yirmili yaşlarda, kısa siyah saçlı oğlu mutfağa girip esniyor: "Günaydın anne, çay hazır mı?" Anne gülümsüyor: "Demleniyor, sen ekmeği kes." Oğul tezgâhta ekmeği kesiyor, anne bir tabağa beyaz peynir ve zeytin koyuyor. Oğul: "Bugün çok güzel bir gün olacak gibi." Anne çayları ince belli bardaklara doldurup pencere kenarındaki masaya getiriyor, ikisi karşılıklı oturuyor. Anne: "Her sabah böyle başlasa keşke." Oğul bardağını kaldırıp gülümsüyor: "Başlar anne, başlar."'
```

Bu fikri değiştirme. Kartta şunları kontrol et:
- 3 blok, 15 + 15 + 15 sn;
- 5 replik harfi harfine aynı; anne S1, oğul S2 (görev sırası; gerekirse elle düzelt);
- Türkçe harfler korunmuş;
- **mekân hikâye başlamadan önceki hâliyle:** masada çay bardağı, peynir ya da zeytin yok, ekmek kesilmemiş;
- ışık: sabah güneşi, aydınlık. Kartta "dim", "moody", "dusk" gibi karanlık bir tarif varsa düzelt.

Kartı orhan'a özetle.

## 2. Görseller

```bash
~/workspace/tools/h3muse-venv/bin/python muse/uzun_senaryo.py gorsel --dizin ~/workspace/h3uretim/20261119_mutfak
```

Kontrol et:
- K1 (anne) ve K2 (oğul): tam boy, tek kişi, karta uyuyor;
- MEKAN: insan yok, yazı yok, masa boş, **aydınlık**.

Gerekirse `--yeniden` (her görsel için en fazla 2 kez). Görselleri orhan'a göster.

## 3. Plan ve iki senaryo

```bash
~/workspace/tools/h3muse-venv/bin/python muse/uzun_senaryo.py plan --dizin ~/workspace/h3uretim/20261119_mutfak --kol ref --yeniden-uretim 0
~/workspace/tools/h3muse-venv/bin/python - <<'SON'
import json, os
d = os.path.expanduser("~/workspace/h3uretim/20261119_mutfak")
s = json.load(open(f"{d}/uzun_senaryo.json", encoding="utf-8"))
for ad, kopru in (("A", False), ("B", True)):
    s["kopru"] = kopru
    json.dump(s, open(f"{d}/senaryo_{ad}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(ad, "kopru:", kopru, "· yeniden_uretim:", s["yeniden_uretim"], "· seed:", s["seed"],
          "· bloklar:", [b["sure"] for b in s["kollar"]["ref"]["bloklar"]])
SON
```

**Beklenen:** iki satır. Yalnızca `kopru` farklı, `yeniden_uretim: 0`, `bloklar: [15, 15, 15]`.

## 4. Onay mesajı

```
Köprü deneyi 2 hazır: aydınlık mutfak, 45 sn, 3 blok. İki koşu: A köprüsüz, B köprülü; aynı plan ve seed'ler.
GPU: A100 (yoksa G4). Toplam tahmini ~80–100 dk, ~10–11 CCU. Güncel bakiye: <colab usage>. Kart ve görseller ekte. Başlayayım mı?
```

## 5. Üretim (sırayla, önce A sonra B)

```bash
~/workspace/tools/h3muse-venv/bin/python muse/h3_uret.py uret --senaryo ~/workspace/h3uretim/20261119_mutfak/senaryo_A.json \
  --oturum-dizini ~/workspace/h3uretim/20261119_mutfak/oturum_A --gpu a100,g4
~/workspace/tools/h3muse-venv/bin/python muse/h3_uret.py uret --senaryo ~/workspace/h3uretim/20261119_mutfak/senaryo_B.json \
  --oturum-dizini ~/workspace/h3uretim/20261119_mutfak/oturum_B --gpu a100,g4
```

B'nin günlüğünde şunlar olmalı:
- `Yüklendi: kopru_ref_2.png` ve `kopru_ref_3.png`;
- iki kez `köprü prompt'u yazılıyor`.

`köprü karesi eklendi; prompt yeniden yazılmadı` satırı görürsen dur ve bana bildir.

Kontrol: A ve B'nin 1. blok videoları bayt bayt aynı olmalı (`sha256sum`). Köprü 1. bloğa dokunmuyor.

## 6. Kör karşılaştırma

1. Yazı-tura ile A ve B'nin birleşik videolarına `deney_video_7.mp4` ve `deney_video_8.mp4` adlarını ver. İkisini Drive'da `H3_Video_Studyosu/20261119_mutfak/` klasörüne yükle. Eşleşmeyi `eslesme.txt` dosyasına yaz.
2. orhan'a şunları sor. Kendi bulgularından hiçbirini yazma:
   - 15. saniyedeki geçiş hangisinde daha akıcı?
   - 30. saniyedeki geçiş hangisinde daha akıcı?
   - Karakterler ve mekân hangisinde daha tutarlı?
   - Genel olarak hangisi daha iyi? Gözüne batan bir şey oldu mu?
   - İpucu: 13–17. ve 28–32. saniyeleri tekrar oynat.

## 7. Kare incelemesi (cevaptan sonra açıklanır)

İki video için de her sınırın hemen öncesini ve sonrasını tam çözünürlükte çıkar ve karşılaştır:

```bash
cd ~/workspace/h3uretim/20261119_mutfak
for k in A B; do for t in 14.9 15.2 30.0 30.3; do
  ffmpeg -v error -y -ss $t -i oturum_$k/cikti/ref_pika_h3_flex_birlesik.mp4 -frames:v 1 sinir_${k}_${t}.png
done; done
```

Her sınır ve her video için şunlara bak:
- kişilerin konumu ve duruşu;
- kamera açısı ve kadraj;
- ışık;
- nesneler: çaydanlık, ekmek, peynir tabağı, bardaklar.

Hangisinin geçişi daha doğal? Bunu `inceleme.md` dosyasına yaz ve **orhan cevap verene kadar paylaşma**.

## 8. Sonuç mesajı

orhan'ın cevaplarından sonra:

```
KÖPRÜ DENEYİ 2 SONUCU
- Eşleşme (video_7 / video_8 → A / B) ve orhan'ın cevapları
- Senin sınır karesi incelemen (iki video, iki sınır)
- Gemini süreklilik puanları ve blok kusurları (A ve B)
- Köprü prompt'larında ne değişti (blok 2 ve 3)
- GPU, süre, CCU (iki koşu ayrı ayrı), Gemini istek sayısı, hatalar ve uyarılar
```
