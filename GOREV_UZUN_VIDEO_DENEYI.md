# Görev: uzun video deneyi (Muse için)

**Amaç:** Uzun videolarda karakter ve sahne tutarlılığını artırmak için yeni yöntemin işe yarayıp yaramadığını ölçmek. Aynı 30 saniyelik senaryo iki yöntemle üretilir:

- **Kol `metin` (eski yöntem):** bloklar arasında kimliği yalnızca metin tarifi taşır.
- **Kol `ref` (yeni yöntem):** kimliği karakter ve mekân görselleri taşır (Ref2VA).

İki kol aynı runtime'da, aynı plan ve aynı seed'lerle üretilir. Fark yalnızca yöntemdir.

**Tahmini maliyet:** A100'de ~55 dk, **~6–7 CCU**. Gemini kotasından 15–18 istek harcar; deneyi kotası taze bir günde yap.

Her adımda `MUSE_REHBERI.md`'deki kurallar geçerlidir; bu belge yalnızca deneye özel adımları verir. Bir adım beklenenden farklı sonuç verirse dur, tam çıktıyı orhan'a ilet.

---

## 0. Hazırlık

```bash
cd ~/workspace/Colab && git pull
PY=~/workspace/tools/h3muse-venv/bin/python
```

Ön koşul: rehberin 2. bölümü tamamlanmış, 2.6'daki kuru deneme geçmiş olmalı.

## 1. Uzun akışın kuru denemesi (CPU, ~0,01 CCU)

```bash
K=~/workspace/h3uretim/uzun_kuru_deneme
$PY muse/uzun_senaryo.py kart   --dizin $K --fikir 'Kuru deneme: "Merhaba."' --sure 24 --sahte
$PY muse/uzun_senaryo.py gorsel --dizin $K
$PY muse/uzun_senaryo.py plan   --dizin $K --kol ikisi
python3 muse/h3_uret.py uret --senaryo $K/uzun_senaryo.json --oturum-dizini $K/oturum --gpu cpu --anahtar '' --aralik 15
```

**Beklenen:**
- `✅ teslim edildi`;
- raporda iki satır: `Kol metin` ve `Kol ref`;
- `$K/oturum/cikti/` içinde iki `_birlesik.mp4` dosyası;
- `aktif atama: 0`.

Kuru deneme geçmezse deneye geçme. Çıktıyı orhan'a ilet.

## 2. Hikâye kartı

```bash
D=~/workspace/h3uretim/$(date +%Y%m%d)_uzun_deney
$PY muse/uzun_senaryo.py kart --dizin $D --sure 30 --stil real --fikir 'Akşamüstü, deniz kenarında bir çay bahçesi; arkada sakin deniz ve martılar. Kır bıyıklı, beyaz önlüklü, ellili yaşlarda çaycı Ahmet, kırmızı hırkalı, uzun siyah saçlı genç bir kadının masasına ince belli bardakta çay getiriyor. Ahmet: "Çaylar taze, buyurun abla." Kadın gülümseyerek: "Sağ olun Ahmet abi, bugün deniz çok güzel." Ahmet yan masayı topluyor, sonra dönüp gülümsüyor: "Bu manzara her akşam böyle, alışırsınız." Kadın çayından bir yudum alıp: "Alışmak istemem, hep ilk günkü gibi kalsın."'
```

Bu fikri **değiştirmeden** kullan; deneyin karşılaştırılabilir olması için sabit.

`$D/hikaye.json` dosyasını kontrol et:
- 2 karakter var mı (Ahmet S1, kadın S2)?
- 2 blok var mı, 15 + 15 sn?
- 4 replik harfi harfine doğru mu?
- Kıyafet ve görünüş tarifleri ayırt edici mi?

Kartı orhan'a özetle ve **onay al**.

## 3. Görseller

```bash
$PY muse/uzun_senaryo.py gorsel --dizin $D
```

`gorseller/K1.png`, `K2.png` ve `MEKAN.png` dosyalarına bak:
- kişiler karta uyuyor mu?
- tam boy ve tek kişi mi?
- mekân boş mu?

Gerekirse `--yeniden K1` ile yeniden ürettir. En fazla 2 kez; olmazsa orhan'a sor. Görselleri orhan'a göster ve **onay al**.

Gemini görsel üretemezse (hata mesajı) tam mesajı orhan'a ilet. Orhan görsel verirse `--ref K1=/yol.png` kullan.

## 4. Plan (iki kol)

```bash
$PY muse/uzun_senaryo.py plan --dizin $D --kol ikisi
```

Çıkış kodu `0` olmalı. `uzun_senaryo.json` içinde `"deney": true`, `"yeniden_uretim": 0` ve iki kol (`metin`, `ref`) olduğunu kontrol et. Deneyde yeniden üretim kapalıdır, böylece iki kol eşit koşullarda karşılaştırılır.

## 5. Onay ve üretim

Orhan'a gönderilecek onay mesajı:

```
Uzun video deneyi hazır: 30 sn, 2 blok, iki yöntem (metin / görsel referanslı).
GPU: A100 (yoksa G4). Tahmini süre ~55 dk, ~6–7 CCU (G4'te ~9). Güncel bakiye: <colab usage>
Kart ve görseller onaylandı. Başlayayım mı?
```

Onay gelince:
```bash
python3 muse/h3_uret.py uret --senaryo $D/uzun_senaryo.json --oturum-dizini $D/oturum --gpu a100,g4
```

Kopma olursa: `python3 muse/h3_uret.py devam --oturum-dizini $D/oturum`.

## 6. Kör karşılaştırma

Orhan'ın değerlendirmesi, Gemini'nin puanlarından daha önemlidir. Hangi videonun hangi yöntem olduğunu ona söylemeden izlet:

1. Yazı-tura at ya da rastgele seç. `*_metin_*_birlesik.mp4` ve `*_ref_*_birlesik.mp4` dosyalarını Drive'a `deney_video_1.mp4` ve `deney_video_2.mp4` adıyla yükle. Hangi numaranın hangi kol olduğunu `$D/eslesme.txt` dosyasına yaz; orhan cevap verene kadar söyleme.
2. Orhan'a sor:
   - Hangisinde karakterler baştan sona aynı kişi gibi?
   - Hangisinde kıyafet ve mekân daha tutarlı?
   - Hangisinde ses daha tutarlı?
   - Genel olarak hangisi daha iyi?
3. Cevaptan sonra eşleşmeyi açıkla.

## 7. Teslim ve rapor

Drive'a `H3_Video_Studyosu/<tarih>_uzun_deney/` klasörüne şunları yükle ve boyutlarını doğrula:
- iki video (kör adlarıyla);
- `*_uzun_sonuc.json`;
- `rapor.md`;
- `hikaye.json`;
- `gorseller/`;
- iki birleşik videonun `_kontrol.jpg` dosyaları;
- `eslesme.txt` (orhan cevap verdikten sonra).

Sonuç mesajında şunlar olsun (bu mesaj Claude'a da iletilecek, eksiksiz yaz):

```
UZUN VIDEO DENEYİ SONUCU
- Tarih, GPU (ad ve bellek), toplam süre, CCU öncesi → sonrası
- Süreklilik puanları (rapor.md'den), her kol için: kimlik / kıyafet / mekân / ses / hikâye / ortalama
- Gemini'nin süreklilik sorunları listesi (her kol için, zamanlarıyla)
- Blok izleme özetleri (her kol, her blok)
- Orhan'ın kör karşılaştırma cevapları ve eşleşme
- Görsel üretimi: hangi model, kaç deneme, orhan'ın görüşü
- Hatalar, uyarılar, yedek model kullanımı (tam metin)
- Drive klasörünün bağlantısı
```

Deney başarısız olursa (hata kodu `1`), aynı gün en fazla **bir kez** tekrar dene ve yalnızca hata tablosunda "tekrar dene" yazan bir hataysa. Diğer durumlarda `rapor.md`'yi ve `cikti/gunluk.txt`'nin son 50 satırını orhan'a ilet.

## Sonraki adım (bu görevin parçası değil)

Köprü (`--kopru`) denemesi, bu deneyin sonucuna göre orhan karar verirse yapılacak.
