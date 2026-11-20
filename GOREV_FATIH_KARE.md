# Görev: Fatih — anahtar kare yöntemi (FL2VA), aynı sahne yeni yöntemle

**Depo:** https://github.com/g-user-s/Colab (dal `claude/trusting-johnson-c5d0tf`). Önce: `cd ~/workspace/Colab && git pull`.

## Neden

Fatih sahnesini (fatih4) bu kez başka bir yöntemle üretiyoruz.
- **fatih4'te:** 15 sn'lik 4 blok vardı; model kompozisyonu yalnızca metinden ve referans görsellerden kurdu.
- **Yeni yöntemde:** sahne **10 kısa tek çekime** bölünüyor. Her çekimin **ilk ve son karesi** önce Gemini ile fotoğraf olarak üretiliyor, H3 yalnızca bu iki kare arasını dolduruyor.
- **Beklenen:** kompozisyon, kimlik ve kamera açısı görselden geldiği için daha sinematik ve daha tutarlı bir sonuç.
- **Zonaro anı:** 4. çekimin son karesi, Zonaro'nun tablosunun düzeni verilerek üretiliyor. Yani tablonun anı doğrudan bir kare olarak hedefleniyor.

Kaynaklar:
- MiniMax'in resmî H3 rehberi: FL2VA biçimi, tek çekim önerisi;
- ComfyUI'deki H3 düğümünün ilk/son kare girişleri;
- tweet'teki ipucu: son kare sıfırdan üretilmez, ilk kare taban verilip yalnızca değişen şey tarif edilir. Böylece kamera açısı kilitli kalır.

| Çekim | Süre | Ne oluyor |
|---|---|---|
| 1 | 5 sn | Damdan yüksek geniş plan: binlerce kişi sessizce bekliyor, kamera alçalıyor |
| 2 | 5 sn | Kalabalığın içinde anne ve oğlu; mehter yaklaşıyor, herkes kapıya doğru bakıyor (kapı kadraj dışında) |
| 3 | 5 sn | Mehter kemerden kameraya doğru çıkıp yolun iki yanına açılıyor |
| 4 | 8 sn | **Tablonun anı:** Sultan beyaz atıyla kemerin gölgesinden ışığa çıkıyor |
| 5 | 5 sn | Sultan geçerken kalabalık diz çöküyor, alay duruyor |
| 6 | 6 sn | Akşemseddin: "Hünkârım, Peygamber efendimizin müjdesi bugün gerçek oldu." |
| 7 | 5 sn | Sultan: "Bu zafer bizim değil, Allah'ındır." |
| 8 | 5 sn | Diz çökmüş anne, gözlerini Sultan'a kaldırıyor |
| 9 | 11 sn | Sultan: "Kalkınız ve müsterih olunuz…" |
| 10 | 5 sn | Yüksekten: binlerce kişi ayağa kalkıyor |

**Ayarlar:**
- ~62 sn (10 çekim), Pika, seed 22, eşik **yüksek**, yeniden üretim 1;
- kareler 1344×768'e kırpılır.

**Tahmini maliyet:**
- A100'de ~64–120 dk, **~7–14 CCU**;
- Gemini: 20 kare görseli, 10 çekim izlemesi, 1 süreklilik.

**Onay noktaları:**
1. kareler;
2. üretim.

---

## 1. Hazırlık

Bu yöntem fatih4'ün karakter ve mekân görsellerini ve Zonaro tablosunu girdi olarak kullanır. Önce var olduklarını kontrol et:

```bash
ls ~/workspace/h3uretim/20261119_fatih4/gorseller/{K1,K2,K3,MEKAN}.png ~/workspace/h3uretim/20261119_fatih/ilham/tablo.jpg
```

Biri eksikse dur ve bana yaz.

Ardından senaryoyu yerleştir:

```bash
D=~/workspace/h3uretim/20261120_fatih_kare
mkdir -p $D
cp ~/workspace/Colab/muse_gorevleri/20261120_fatih_kare/uzun_senaryo.json $D/
~/workspace/tools/h3muse-venv/bin/python -c "import json; s=json.load(open('$D/uzun_senaryo.json')); print(s['h3app_surum'], s['durum'], len(s['kareler']), list(s['kollar']))"
```

**Beklenen:** `c9c1d9f9b2b4 hazir 20 ['kare']`.

`uzun_senaryo.json`'u elle düzenleme; `plan` adımını çalıştırma.

## 2. Anahtar kareler (20 görsel)

> **Düzeltme (20.11):** C2 ve C8'de kapı yanlışlıkla annenin arkasına konmuştu. Bu çekimlerde kapı artık kadraj dışında,
> solda; anne ve oğlunun arkasında yalnızca kalabalık ve ev duvarı var. Kareleri bu düzeltmeden önce ürettiysen:
> `git pull`, `uzun_senaryo.json`'u 1. adımdaki gibi yeniden kopyala, sonra yalnızca şu dört kareyi yenile:
> `... kareler --dizin ~/workspace/h3uretim/20261120_fatih_kare --yeniden C2a --yeniden C2b --yeniden C8a --yeniden C8b`

```bash
cd ~/workspace/Colab
~/workspace/tools/h3muse-venv/bin/python muse/uzun_senaryo.py kareler --dizin ~/workspace/h3uretim/20261120_fatih_kare
```

**Nasıl çalışır:**
- Kareler sırayla üretilir. Bazı kareler bir önceki kareyi "taban" olarak kullanır: aynı kamera, yalnızca bir şey değişir.
- Yarıda kalırsa aynı komutu tekrar çalıştır; var olanları atlar.
- Kareler `kareler/<id>.png` dosyalarına yazılır. Her çekimin ilk karesi `C<n>a`, son karesi `C<n>b`.

**Kontrol et (çekim çekim, a ve b yan yana):**
- **Kimlik:** Sultan, Akşemseddin ve anne fatih4 görselleriyle aynı mı?
- **Mekân mantığı:** kapı yalnızca kameranın kapıya baktığı karelerde görünmeli. C2 ve C8'de (anne) kapı, kemer ya da sur **görünmemeli**.
- **a → b farkı:** küçük ve tarif edilen kadar mı? Kamera aynı yerde mi? Özellikle C1, C2, C6, C7, C9, C10.
- **C4b (en önemlisi):** Zonaro'nun tablosu gibi mi?
  - Sultan beyaz atla kemerden kameraya doğru, hafif solda;
  - önde solda Akşemseddin;
  - arkada mızrak ve sancak ormanı, parlak gök;
  - kemerde fresko;
  - ön planda solda kırmızı-altın sarıklı muhafız;
  - **ceset yok**, tablo gibi boyalı değil, fotoğraf gibi.
- **C4a:** C4b ile aynı kadraj, ama Sultan kemerin gölgesinde, daha geride.
- **Hepsinde:** yazı yok, sancakta yıldız yok, kan yok.

**Beğenmediğin kareyi yenile:**

```bash
~/workspace/tools/h3muse-venv/bin/python muse/uzun_senaryo.py kareler --dizin ~/workspace/h3uretim/20261120_fatih_kare --yeniden C4b
```

Her kare için en fazla 2 kez yenile. **Bir taban kareyi yenilersen ona bağlı kareyi de yenile.** Bağlılıklar:
- C1a → C1b → C10a → C10b;
- C2a → C2b;
- C3a → C3b;
- C4b → C4a;
- C5a → C5b;
- C6a → C6b;
- C7a → C7b;
- C8a → C8b;
- C9a → C9b.

Örnek: `--yeniden C4b --yeniden C4a`.

Bütün kareleri orhan'a göster: çekim sırasıyla, a ve b yan yana.

## 3. Onay mesajı

```
Fatih — anahtar kare yöntemi hazır: 10 tek çekim, ~62 sn. Her çekimin ilk ve son karesi ekte (C4b: Zonaro'nun anı).
Pika, eşik yüksek. GPU: A100 (yoksa G4). Tahmini ~64–120 dk, ~7–14 CCU. Güncel bakiye: <colab usage>. Başlayayım mı?
```

## 4. Üretim

```bash
~/workspace/tools/h3muse-venv/bin/python muse/h3_uret.py uret --senaryo ~/workspace/h3uretim/20261120_fatih_kare/uzun_senaryo.json \
  --oturum-dizini ~/workspace/h3uretim/20261120_fatih_kare/oturum --gpu a100,g4
```

Günlükte `━━ Kol: kare (anahtar kareli, FL2VA) ━━` görünmeli. Kesilirse rehberdeki gibi `devam` kullan.

## 5. İnceleme

Rapor ve süreklilik puanı. Çekim sınırlarından birer kare al:

```bash
cd ~/workspace/h3uretim/20261120_fatih_kare
for t in 5.1 5.3 10.2 10.4 15.4 15.6 23.4 23.6 28.6 28.8 35.2 35.4 40.3 40.5 45.5 45.7 57.0 57.2; do
  ffmpeg -v error -y -ss $t -i oturum/cikti/kare_pika_h3_flex_birlesik.mp4 -frames:v 1 sinir_$t.png; done
```

Şunları ayrı ayrı yaz:
- **Kareye uyum:** her çekim ilk karesiyle başlayıp son karesiyle bitiyor mu? Arada sıçrama, erime, bozulma var mı?
- **Tablo anı (4. çekim, 15,5–23,5. sn):** Zonaro'nun tablosu canlanmış gibi mi? At yürüyüşü doğal mı?
- **Kalabalık:** diz çökme (5. çekim) ve ayağa kalkma (10. çekim) gerçekçi mi?
- **Konuşma:** replikler tam, dudaklar uyumlu mu? Sultan'ın sözü 9. çekimin içinde bitiyor mu?
- **Ses:** mehter çekimden çekime kopuyor mu, rahatsız ediyor mu?
- **fatih4 ile karşılaştırma:** hangisi daha sinematik, hangisi daha tutarlı? Kendi görüşün.

## 6. Teslim ve sorular

Drive: `H3_Video_Studyosu/20261120_fatih_kare/`. Şunları yükle:
- birleşik video;
- `rapor.md`;
- `uzun_sonuc.json`;
- `uzun_senaryo.json`;
- `kareler/`;
- `_kontrol.jpg`;
- sınır kareleri.

orhan'a sor:
- **fatih4 mü, bu mu daha iyi?** Neden?
- **Film sahnesi gibi mi?** Tablo anı nasıl?
- **gözüne batan:** ne varsa.

## 7. Sonuç mesajı

Başlık `FATİH KARE SONUCU`. Şunları içersin:
- video bağlantısı;
- GPU, süre, CCU;
- kare üretiminde kaç yenileme yapıldı ve hangi model kullanıldı;
- süreklilik puanları;
- çekim çekim adaylar ve kusurlar;
- 5. adımdaki gözlemlerin;
- orhan'ın cevapları;
- hatalar ve uyarılar.
