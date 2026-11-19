# Görev: köprü deneyi — blok geçişleri daha akıcı olur mu?

**Depo:** https://github.com/g-user-s/Colab (dal `claude/trusting-johnson-c5d0tf`). Önce: `cd ~/workspace/Colab && git pull`.

**Soru:** Uzun videoda bloklar arasındaki geçiş (15. ve 30. saniye) "köprü" ile daha akıcı olur mu?

**Köprü:** her bloğa önceki bloğun son karesi de sahne görseli olarak verilir ve Gemini o bloğun prompt'unu bu kareyi görerek yeniden yazar: kişilerin konumu, ışık, nesneler. Kod hazır, kuru denemede (T15) çalıştı. Gerçek GPU'da ilk kez deneniyor.

**Düzen:** Dünkü sahaf videosu ("1923 Haritası", `~/workspace/h3uretim/20261118_sahaf`) **köprüsüz kol**dur. Aynı planı, aynı karakter ve mekân görsellerini ve aynı seed'leri (22, 23, 24) kullanarak **köprülü kol**u üreteceksin. Aradaki tek fark köprü olacak.

Dünkü üretimde hiçbir blok yeniden üretilmemişti. Bu yüzden bu koşuda yeniden üretimi kapatıyoruz (`yeniden_uretim: 0`); iki kol eşit kalsın.

**Tahmini maliyet:**
- A100'de ~40–50 dk, **~5 CCU**;
- Gemini ~6 istek: 2 köprü prompt'u, 3 blok izlemesi, 1 süreklilik.

**Onay:** üretimden önce orhan'a sor (4. adım).

---

## 1. Senaryoyu kopyala, köprüyü aç

```bash
cd ~/workspace/Colab
mkdir -p ~/workspace/h3uretim/20261119_kopru
~/workspace/tools/h3muse-venv/bin/python - <<'SON'
import json, os
k = os.path.expanduser("~/workspace/h3uretim/20261118_sahaf/uzun_senaryo.json")
h = os.path.expanduser("~/workspace/h3uretim/20261119_kopru/uzun_senaryo.json")
s = json.load(open(k, encoding="utf-8"))
s["kopru"] = True
s["yeniden_uretim"] = 0
json.dump(s, open(h, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("kopru:", s["kopru"], "· yeniden_uretim:", s["yeniden_uretim"], "· kollar:", list(s["kollar"]),
      "· seed:", s["seed"], "· görseller:", [os.path.basename(r["dosya"]) for r in s["referanslar"]])
SON
```

**Beklenen:**
- `kopru: True · yeniden_uretim: 0 · kollar: ['ref'] · seed: 22`;
- üç görsel: K1, K2, MEKAN.

Görsel yolları dünkü klasörü gösterir; bu doğru. Aynı görseller kullanılacak, dünkü klasörde hiçbir şeyi değiştirme.

## 2. Kontrol: kod sürümü uyuyor mu?

`h3_uret.py`, senaryo farklı bir `h3app` sürümüyle yazılmışsa üretimi reddeder. Dünden bu yana `h3app` değişmedi, bu yüzden geçmesi gerekir. Reddederse **dur ve bana bildir**: planı yeniden yazmak iki kolu karşılaştırılamaz yapar.

## 3. Onay mesajı

```
Köprü deneyi hazır: dünkü sahaf planı, aynı görseller ve seed'ler, yalnızca köprü açık.
GPU: A100 (yoksa G4). Tahmini ~40–50 dk, ~5 CCU. Güncel bakiye: <colab usage>. Başlayayım mı?
```

## 4. Üretim

```bash
~/workspace/tools/h3muse-venv/bin/python muse/h3_uret.py uret \
  --senaryo ~/workspace/h3uretim/20261119_kopru/uzun_senaryo.json \
  --oturum-dizini ~/workspace/h3uretim/20261119_kopru/oturum --gpu a100,g4
```

Günlükte şunları gör ve raporda yaz:
- blok 2 ve blok 3 için `Yüklendi: kopru_ref_2.png` / `kopru_ref_3.png`;
- `🔗 kopru_ref_N.png: köprü prompt'u yazılıyor (bu makineden)…`;
- köprü prompt'unda uyarı olup olmadığı.

Uyarı: `köprü karesi eklendi; prompt yeniden yazılmadı` satırını görürsen köprü çalışmamış demektir (anahtar okunamadı). O zaman dur ve bana bildir.

## 5. Köprü prompt'larını incele

`oturum/oturum.json` → `kopru_promptlari` alanında blok 2 ve 3'ün yeni prompt'ları var. Bunları dünkü planın aynı bloklarıyla (`uzun_senaryo.json` → `kollar.ref.bloklar[N].prompt`) karşılaştır. Neler değişti? Kişilerin konumu, kamera açısı, ışık, tezgâhtaki nesneler (harita, kitaplar)? Kısa bir özet yaz.

## 6. Kör karşılaştırma

1. Dünkü video: `~/workspace/h3uretim/20261118_sahaf/oturum/cikti/ref_pika_h3_flex_birlesik.mp4`. Yeni video: `~/workspace/h3uretim/20261119_kopru/oturum/cikti/ref_pika_h3_flex_birlesik.mp4`.
2. Yazı-tura ile `deney_video_5.mp4` ve `deney_video_6.mp4` adlarını ver. İkisini Drive'da `H3_Video_Studyosu/20261119_kopru/` klasörüne yükle. Eşleşmeyi `eslesme.txt` dosyasına yaz, orhan cevap verene kadar söyleme.
3. orhan'a şunları sor:
   - **15. ve 30. saniyelerdeki geçişler hangisinde daha akıcı?** (En önemli soru bu.)
   - Hangisinde karakterler ve mekân daha tutarlı?
   - Genel olarak hangisi daha iyi? Gözüne batan bir şey oldu mu?
   - İpucu: 13–17. ve 28–32. saniyeleri tekrar oynat, mümkünse büyük ekranda.

## 7. Kare incelemesi: blok sınırları

Her iki video için, her blok sınırında, sınırdan hemen önceki ve hemen sonraki kareyi tam çözünürlükte çıkar ve karşılaştır:

```bash
for v in sahaf:20261118_sahaf kopru:20261119_kopru; do ad=${v%%:*}; d=~/workspace/h3uretim/${v#*:}/oturum/cikti
  for t in 14.9 15.2 30.0 30.3; do
    ffmpeg -v error -y -ss $t -i $d/ref_pika_h3_flex_birlesik.mp4 -frames:v 1 ~/workspace/h3uretim/20261119_kopru/sinir_${ad}_${t}.png
  done; done
```

Her sınır için (14,9→15,2 ve 30,0→30,3) ve her video için şunları yaz:
- kişilerin konumu ve duruşu devam ediyor mu, yoksa sıçrıyor mu?
- kamera açısı ve kadraj;
- ışık;
- nesneler: harita, kitaplar, çanta.

Sonra hangi videonun geçişinin daha doğal göründüğünü söyle.

## 8. Sonuç mesajı

```
KÖPRÜ DENEYİ SONUCU
- Video bağlantıları (kör adlarıyla), GPU, süre, CCU öncesi → sonrası (rapordaki tahminle)
- Köprü çalıştı mı (yükleme ve prompt satırları), köprü prompt'larında ne değişti
- Gemini süreklilik puanları: dünkü (10,0) ve yeni; yeni videonun blok izleme kusurları
- orhan'ın cevapları ve eşleşme (cevaptan sonra)
- Senin sınır karesi incelemen (iki video, iki sınır)
- Hatalar, uyarılar, Gemini istek sayısı
```
