# Muse için rehber: Colab'de H3 video üretimi

Bu rehber, H3 Video Stüdyosu ile Colab GPU'sunda Türkçe konuşmalı video üretmenin adımlarını anlatır. Akış başsızdır, tarayıcı gerekmez. Senaryo Gemini ile yazılır, video Colab'de üretilir, sonuç Drive'a teslim edilir.

Rehberi baştan sona sırayla uygula. Bir adım burada yazdığından farklı sonuç verirse kendi çözümünü uydurma: dur, gördüğünü olduğu gibi orhan'a bildir.

Onay kuralların her zamanki gibi geçerli. Bu rehber onlara bir şey eklemez; yalnızca bu akışta onayın hangi noktalarda gerektiğini gösterir (bkz. Onay noktaları).

### Senin ortamında bilinmesi gerekenler (18 Kasım test turundan)

- **Uzun komutlar:** exec aracın ~10 sn'den uzun süren komutu kendiliğinden arka plana alır ve bitince sonucu sana teslim eder. `h3_uret.py` kendi yoklamasını yapar; senin ayrıca yoklama döngüsü yazmana gerek yok, komutun bitmesini bekle.
- **Kabuk değişkenleri:** bir komutta tanımladığın `D=...` gibi değişkenler sonraki komutta, arka plana alınan işte ya da `nohup … &` içinde kaybolabilir. Değişkeni kullandığın komutun içinde tanımla ya da tam yol yaz.
- **`pkill -f`:** kalıbın ilk harfini köşeli paranteze al (`pkill -f "[h]3_uret.py"`); yoksa komutu çalıştıran kendi kabuğunu da öldürür.
- **Drive:** `H3_Video_Studyosu` klasörü yoksa oluştur. Yükleme komutu: `drive +upload <dosya> --parent <klasör>`.
- **Colab içinden Drive bağlama (`colab drivemount`):** her seferinde tarayıcıda onay ister ve onay gelmezse sonsuza kadar bekler. Bu akışta kullanılmaz; teslim her zaman indirme + Drive bağlayıcısıyla yapılır.
- **Gemini anahtarı:** kasan anahtarı bir bağlayıcıda saklar ve dosyaya gerçek anahtar yerine **vekil değer** (`hsurr:…`) yazar. İstek senin makinenden çıkarken gerçek anahtarla değiştirilir. Bu yüzden Gemini'ye giden her şey senin makinende yapılır; Colab runtime'ı Gemini'ye gitmez.
- **`NO_PROXY`:** içindeki köşeli IPv6 kayıtları (`[::1]`) Gemini kütüphanesini bozuyordu (`Invalid port: ':1]'`). Betikler bunu artık kendileri düzeltiyor; elle ayarlamana gerek yok.
- **Gemini'nin ilk yanıtı:** her istek onay kartından geçtiği için ana model 10 sn içinde yanıt vermeye başlamıyor ve iş yedek modele düşüyordu. Betikler bu sınırı senin ortamında 60 sn yapıyor. Yedek model yine de kullanılırsa rapor bunu gösterir.
- **CCU:** `colab usage` bakiyeyi 2 ondalıkla verir; kısa işlerde fark 0,00 görünür. Rapor bu yüzden ayrıca "açık kalma süresi × saatlik oran" tahminini yazar.

---

## İçindekiler

1. Neyin ne olduğu
2. Tek seferlik kurulum
3. Her üretimde yapılacaklar
4. İyi senaryo nasıl yazılır
5. Maliyet ve süre
6. Hata olursa ne yapılır
7. Kopma ve yeniden başlama
8. Yapılmayacaklar
9. Bilinen sınırlar
10. Uzun video (16–60 sn)

---

## 1. Neyin ne olduğu

| Parça | Ne işe yarar | Nerede çalışır |
|---|---|---|
| `muse/senaryo.py` | Fikir → Gemini brief'i → H3 prompt'u → denetim → `senaryo.json` | Senin makinende (GPU yok, CCU harcamaz) |
| `muse/h3_uret.py` | GPU açar, üretir, indirir, doğrular, kapatır, rapor yazar | Senin makinende; Colab'i yönetir |
| `muse/runtime_runner.py` | Üretimi Colab'de arka planda yürütür | Colab runtime'ında (`h3_uret.py` yükler, sen elle çalıştırmazsın) |
| `muse/yama_411.py` | Colab CLI'daki 411 hatasını düzeltir | Senin makinende, kurulumda bir kez |
| `muse/uzun_senaryo.py` | Uzun video: hikâye kartı → karakter/mekân görselleri → blok prompt'ları | Senin makinende (CCU harcamaz) |
| `h3/` | H3 Video Stüdyosu'nun kendisi (uzun video modülleri `h3app/hikaye.py`, `h3app/uzun.py` dahil) | `h3_uret.py` runtime'a `h3app.tar` olarak yükler |
| `muse/ortak.py` | Sabit ayarlar (h3 commit'i, süre sınırları) | — |

Bu betikler H3 Video Stüdyosu'nun kendi fonksiyonlarını çağırır: `prompt_writer.expand`, `prompt_writer.rewrite`, `ui._generate_job`. Yani notebook'taki "Fikirden videoya" düğmesiyle aynı kalitede iş çıkar: Gemini brief'i ve prompt'u yazar, video üretilir, otomatik kontrol yapılır, Gemini videoyu izler ve kusur bulursa yeni seed ile yeniden üretir.

H3 Video Stüdyosu bu deponun `h3/` klasöründedir; ayrıca klonlanmaz. `git pull` ile H3 kodu da güncellenir. Her senaryo yazıldığı `h3app` sürümünü kaydeder; kod değiştiyse `h3_uret.py` eski senaryoyu reddeder ve senaryoyu yeniden yazdırman gerekir.

### Klasörler (senin makinende)

```
~/workspace/tools/colab                 # Colab CLI sarmalayıcısı (zaten var)
~/workspace/tools/colab-cli-venv/       # CLI'nın venv'i (zaten var)
~/workspace/tools/h3muse-venv/          # senaryo.py için venv (kurulumda oluşturulur)
~/workspace/Colab/                      # bu depo (rehber + betikler)
~/.config/h3muse/gemini.key             # Gemini anahtarı (chmod 600)
~/workspace/h3uretim/<tarih>_<ad>/      # her üretimin klasörü: senaryo, oturum, çıktı, rapor
```

---

## 2. Tek seferlik kurulum

Her komutu sırayla çalıştır ve çıktısının beklenen sonuçla aynı olduğunu kontrol et.

### 2.1 Colab CLI ve giriş

```bash
~/workspace/tools/colab whoami
```
**Beklenen:** hesap adı ve kapsamlar görünür, giriş kodu sorulmaz.
Kod soruyorsa sarmalayıcının `PYTHON_KEYRING_BACKEND=keyrings.alt.file.PlaintextKeyring` ayarını yaptığını kontrol et. Hâlâ soruyorsa girişi orhan ile birlikte yap.

Token dosyası şifresizdir. İzinlerini kısıtla:
```bash
find ~/.local/share/python_keyring -type f -exec chmod 600 {} \; 2>/dev/null; true
```

### 2.2 411 yaması

```bash
~/workspace/tools/colab-cli-venv/bin/python ~/workspace/Colab/muse/yama_411.py
```
**Beklenen:** `✅ Yama zaten uygulanmış` ya da `✅ Yama uygulandı`.
`❌ Beklenen kod bulunamadı` çıkarsa CLI sürümü değişmiş demektir. Yamayı elle uygulama, orhan'a bildir.

CLI güncellenir ya da yeniden kurulursa yama silinir; bu komutu tekrar çalıştır. Kendiliğinden `colab update` çalıştırma (bkz. Yapılmayacaklar).

### 2.3 Bu depo

```bash
cd ~/workspace && ([ -d Colab ] || git clone -b claude/trusting-johnson-c5d0tf https://github.com/g-user-s/Colab) && cd Colab
git checkout claude/trusting-johnson-c5d0tf && git pull
ls h3/h3app/hikaye.py
```
**Beklenen:** son komut dosya yolunu yazar. H3 kodu bu deponun içinde gelir; ayrı bir H3 klonu gerekmez. Eski `~/workspace/h3-video-studyosu` klonu artık kullanılmaz.

### 2.4 Senaryo için venv

`senaryo.py`'nin tek dış bağımlılığı `google-genai` paketidir.
```bash
python3 -m venv ~/workspace/tools/h3muse-venv
~/workspace/tools/h3muse-venv/bin/pip install google-genai==2.34.0
```
`h3_uret.py` yalnızca standart kütüphaneyi kullanır; herhangi bir `python3` ile çalışır.

### 2.5 Gemini anahtarı

Anahtarı orhan **güvenli giriş kartıyla** verir; sohbete yazılmasını isteme. Anahtar elinde değilse Gemini gerektiren adımlar (senaryo, hikâye kartı, görseller, izleme) çalışmaz. Betikler bunu açık bir mesajla söyler; anahtarı başka yerden (ör. Colab Secrets) arama. Anahtar gelince bir dosyaya yaz: dosya yazma aracını kullan, anahtarı komut satırına yazma ve ekrana basma.
```bash
mkdir -p ~/.config/h3muse && chmod 700 ~/.config/h3muse
# anahtarı ~/.config/h3muse/gemini.key dosyasına yaz (tek satır), sonra:
chmod 600 ~/.config/h3muse/gemini.key
```
Senin ortamında anahtar bir bağlayıcıda durur ve dosyaya vekil değer yazılır (18 Kasım'da böyle kuruldu); bu doğru yoldur. Dosya yoksa betikler anahtarı `GEMINI_API_KEY` (ya da `GEMINI`, `GOOGLE_API_KEY`) ortam değişkeninden okur; güvenli kasan anahtarı böyle veriyorsa dosya yazmana gerek yok. Betikler izinleri 600'den geniş bir anahtar dosyasını reddeder. Anahtar runtime'a dosya olarak gider; runner onu okur okumaz siler. Komut satırına, günlüğe ya da rapora hiçbir zaman girmez.

### 2.6 Kuru deneme (bir kez, yaklaşık 0,01 CCU)

Akışın tamamını Colab CPU runtime'ında, sahte video ve sahte Gemini metinleriyle dene. Böylece gerçek GPU harcamasından önce CLI, yama, yükleme, indirme ve kapatma adımları doğrulanmış olur.

```bash
cd ~/workspace/Colab
D=~/workspace/h3uretim/kuru_deneme
~/workspace/tools/h3muse-venv/bin/python muse/senaryo.py \
  --fikir 'Kuru deneme' --sure 5 --sahte --cikti $D/senaryo.json
~/workspace/tools/h3muse-venv/bin/python muse/h3_uret.py uret --senaryo $D/senaryo.json --oturum-dizini $D/oturum \
  --gpu cpu --anahtar '' --aralik 15
```
`senaryo.py` sahte modda `2` dönebilir (örnek metin fikirle eşleşmez). Bu durumda `h3_uret.py`'ye `--sorunlu-kabul` ekle; kuru deneme için sorun değil.

**Beklenen:**
- `✅ teslim edildi`;
- `$D/oturum/cikti/` içinde bir `.mp4`, `_prompt.txt`, `_bilgi.json` ve `gunluk.txt`;
- raporda `aktif atama: 0`.

H3 kodu runtime'a `h3app.tar` olarak yüklenir; GitHub'a erişim gerekmez.

Kuru deneme geçmeden gerçek üretime geçme.

---

## 3. Her üretimde yapılacaklar

Her üretim için yeni bir klasör aç: `D=~/workspace/h3uretim/$(date +%Y%m%d)_<kisa-ad>`.

### Adım 1: Fikri yaz

Orhan'ın isteğini bölüm 4'teki şablona göre kısa bir Türkçe fikre çevir. Replikler çift tırnak içinde ve harfi harfine yazılır.

### Adım 2: Senaryoyu Gemini ile yazdır (CCU harcamaz)

```bash
cd ~/workspace/Colab
~/workspace/tools/h3muse-venv/bin/python muse/senaryo.py \
  --fikir '<fikir>' --sure 10 --stil real --yontem pika --cozunurluk yatay \
  --cikti $D/senaryo.json
```

Seçenekler:
- `--sure`: 4–15 saniye.
- `--stil`: `real` (gerçek dünya), `anime`, `pixar` (3D), `watercolour` (suluboya).
- `--yontem`: `pika` (varsayılan, hızlı ve dengeli), `turbo` (en hızlı, henüz gerçek GPU'da ölçülmedi), `h3` (en yavaş, yaklaşık 3 kat süre).
- `--cozunurluk`: `yatay` (1344×768), `dikey` (768×1344), `kare` (1024×1024).
- `--seed`: sayı (varsayılan 22).
- Referans görsel: `--ref yol.png:karakter:Çaycı Ahmet` (rol: `karakter` | `arka_plan` | `nesne`). En fazla 9 görsel; seçenek tekrarlanabilir.

Çıkış kodları:

| Kod | Anlamı | Ne yaparsın |
|---|---|---|
| `0` | Senaryo hazır | Adım 3'e geç |
| `2` | Prompt yazıldı ama denetim sorun buldu | Sorunları oku, fikri düzelt, tekrar çalıştır (en fazla 2 kez). Hâlâ sorun varsa orhan'a sor |
| `1` | Gemini hatası | Hata tablosu |

`⚠️ Yedek modelle yazılan adımlar` uyarısı çıkarsa metin `gemini-4-hydrogen` yerine daha zayıf bir yedek modelle yazılmıştır. Kalite önemli olduğu için 10–15 dakika bekleyip tekrar dene. İki denemede de yedek model kullanılıyorsa durumu orhan'a bildir ve ona karar bırak.

**Brief'i elle düzeltmek:** Gemini'nin brief'inde yanlış bir şey varsa (`senaryo.json` → `brief`), düzeltilmiş halini bir dosyaya yaz ve yalnızca prompt'u yeniden yazdır:
```bash
... muse/senaryo.py ... --brief-dosyasi $D/brief_duzeltilmis.txt --cikti $D/senaryo.json
```

### Adım 3: Senaryoyu değerlendir

`$D/senaryo.json` dosyasındaki `brief` ve `prompt` alanlarını oku. Şu soruların **hepsine** evet diyebilmelisin:

- [ ] Fikirdeki her replik prompt'ta `<d>[Turkish] ...</d>` içinde, harfi harfine aynı mı? (İ ı Ş ş Ğ ğ Ç ç Ö ö Ü ü dahil)
- [ ] Konuşan her kişinin bir konuşmacı kimliği (S1, S2…) ve ayırt edici bir sesi var mı?
- [ ] Repliklerin toplamı süreye sığıyor mu? (Kaba ölçü: saniyede en fazla 2,5 kelime, ayrıca baştan ve sondan 1'er saniye boşluk.)
- [ ] Mekân, ışık, kamera ve ses tarif edilmiş mi? İstenmediği hâlde müzik eklenmemiş mi (`non_diegetic_music: N/A`)?
- [ ] İstenmeyen ekran yazısı yok mu? (İstenmediyse prompt'ta "No readable text…" cümlesi olmalı.)
- [ ] Fikirde olmayan bir olay, kişi ya da sahne eklenmemiş mi?
- [ ] `sorunlar` listesi boş ve `yedek_model` listesi boş mu?

Bir maddede "hayır" diyorsan fikri düzeltip Adım 2'yi tekrarla. Brief'te tek bir yanlış varsa `--brief-dosyasi` yolunu kullan.

### Adım 4: Onay al

Orhan'a şunları göster ve onayını iste:

```
Senaryo hazır: <fikrin tek cümlelik özeti>
Replikler: "<replik 1>" / "<replik 2>"
Ayarlar: <süre> sn · <stil> · <yöntem> · <çözünürlük>
GPU sırası: G4 → H100 → A100
Tahmini süre ve maliyet: <bölüm 5'teki tablodan> dk, ~<x>–<y> CCU (güncel bakiye: <colab usage çıktısı>)
Prompt: $D/senaryo.json
Üretime başlayayım mı?
```

Güncel bakiyeyi öğrenmek için: `~/workspace/tools/colab usage`.

### Adım 5: Üret

```bash
cd ~/workspace/Colab
~/workspace/tools/h3muse-venv/bin/python muse/h3_uret.py uret --senaryo $D/senaryo.json --oturum-dizini $D/oturum
```

İş bölümü: **Colab yalnızca GPU işi yapar** (render, birleştirme, otomatik kontrol). **Gemini'ye giden her şey senin makinende yapılır:** videonun izlenmesi, yeniden üretim kararı, süreklilik puanı, köprü prompt'u. Gemini anahtarı runtime'a hiç gitmez; kasanın vekil anahtarı zaten yalnızca senin makinenden çıkan isteklerde çalışır. Bu yüzden betik `h3muse-venv` python'ıyla çalıştırılır.

Betik sırasıyla şunları yapar:
1. G4'ü 3 kez dener. 503 hatasında 30 sn bekler. Hesapta yoksa hemen H100'e, sonra A100'e geçer.
2. GPU'yu `nvidia-smi` ile doğrular; 40 GB altındaysa durur.
3. Runner'ı, H3 kodunu, senaryoyu ve referansları yükler. Anahtar yüklenmez.
4. İlk GPU işini başlatır. İlk işte kurulum ve model indirmesi yaklaşık 6 dk sürer; sonraki işlerde bu tekrar edilmez.
5. 30 saniyede bir durumu yoklar. İş bitince videoyu indirir ve sha256 ile doğrular.
6. Videoyu **senin makinenden** Gemini'ye izletir. Yüksek önemde kusur varsa **aynı runtime'da** yeni seed ile tekrar üretir (en fazla 2 kez) ve en az kusurlu adayı seçer.
7. Runtime'ı kapatır, sunucuda açık oturum kalmadığını kontrol eder, `$D/oturum/rapor.md`'yi yazar.

**Yeniden üretim eşiği:** varsayılan `--yeniden-esik yuksek`: yalnızca yüksek önemde kusur yeni seed'i tetikler. `--yeniden-esik orta` orta kusurları da (el-nesne kaynaşması, parmak bozulması gibi) tetikler. Bu daha temiz sonuç verir, ama neredeyse her blok bir kez daha üretilir: GPU süresi ve CCU yaklaşık iki katına çıkar. Hangisinin kullanılacağına orhan karar verir; onay mesajında tahmini CCU'yu buna göre yaz. 18 Kasım'daki 45 sn'lik videoda (eşik yüksek) hiçbir blok yeniden üretilmedi ve orta önemli el kusurları videoda kaldı.

Her iş biter bitmez indirildiği için bir hata olursa elde o ana kadarki çıktılar vardır. Runtime **her durumda kapatılır**. İzlemede her Gemini isteği orhan'ın onay kartına düşebilir; kartlar zamanında onaylanmazsa izleme yapılamaz ve rapor bunu "izlenemedi" olarak gösterir.

Çıkış kodları:

| Kod | Anlamı |
|---|---|
| `0` | Video teslim edildi |
| `1` | Hata oldu, runtime kapatıldı; ayrıntı `rapor.md` ve `cikti/gunluk.txt`'te |
| `3` | Hiçbir GPU alınamadı; hiçbir şey açılmadı, CCU harcanmadı |

Komut uzun sürer (15–60 dk). Çalışırken başka bir `uret` başlatma. Komut yarıda kesilirse bölüm 7'deki adımları izle.

### Adım 6: Sonucu incele

`$D/oturum/cikti/` klasöründe:
- `*_seedNN.mp4`: seçilen video;
- `*_kontrol.jpg`: videodan kareler (temas sayfası). Mutlaka bak;
- `*_kirpinti.jpg`: %100 kırpıntılar (yüz ve el detayları);
- `*_bilgi.json`: ayarlar ve otomatik kontrol;
- `*_prompt.txt`, `gunluk.txt`;
- `$D/oturum/oturum.json` → `incelemeler`: Gemini'nin her aday için izleme sonucu (senin makinenden yapıldı).

Gemini izlemesi yüksek önemde kusur bulduysa betik en fazla 2 kez yeni seed ile denemiş ve en az kusurlu adayı seçmiştir; rapordaki `aday` satırları bunu gösterir. Bunu raporunda açıkça yaz. Prompt'u sadeleştirip yeniden üretmek orhan'ın kararıdır.

**Senin kare incelemen (ikinci göz).** 18 Kasım T13'te görüldü: Gemini sesi ve hareketi denetler ama durağan sapmaları kaçırabilir. Sen ise karelerde prompt'ta olmayan yeleği, çaycı getirmeden masada duran bardağı ve düzensiz kamera yaklaşmasını buldun. Bu yüzden teslimden önce seçilen videoya kendin de bak:
```bash
mkdir -p $D/kareler && ffmpeg -v error -i <seçilen video> -vf fps=2 $D/kareler/k_%03d.jpg
```
Tam çözünürlük kullan, ölçekleme. Küçük el kusurları 640 px'te kayboluyor. Şunları prompt'la karşılaştır:
- kıyafet ve renkler;
- nesneler (getirilmeden önce yerinde mi, kayboluyor mu?);
- kişi sayısı ve konumları;
- yazı;
- eller (kare kare);
- kamera hareketi.

Bulduklarını raporda Gemini'nin bulduklarından ayrı bir başlıkla yaz. Ses, replik ve dudak senkronu için Gemini'nin sonucuna güven; sen bunları duyamıyorsun.

### Adım 7: Drive'a teslim

Drive bağlayıcısıyla `H3_Video_Studyosu/<tarih>_<kisa-ad>/` klasörüne şunları yükle:
- video;
- `_prompt.txt`;
- `_bilgi.json`;
- `_kontrol.jpg`;
- `rapor.md`.

Yüklemeden sonra her dosyanın Drive'daki boyutunu yereldeki boyutla karşılaştır. Yerel kopyayı silme.

### Adım 8: Rapor

`rapor.md`'nin içeriğini ve Drive bağlantısını orhan'a gönder. Ekle:
- Gemini izlemesinin özeti;
- yedek model uyarıları (varsa);
- harcanan CCU;
- `aktif atama: 0` satırı.

---

## 4. İyi senaryo nasıl yazılır

Videonun kalitesi büyük ölçüde fikrin netliğine bağlıdır. Gemini fikri genişletir, ama fikirde olmayan bir şeyi doğru tahmin edemez.

### Fikir şablonu

```
<Mekân ve zaman>. <Kim var, nasıl görünüyor, ekranda nerede duruyor>.
<Ne oluyor, sırayla>. <Kişi> <nasıl bir sesle> şöyle diyor: "<Türkçe replik>".
<Diğer kişi> <tepki> ve cevap veriyor: "<Türkçe replik>".
Kamera: <çekim boyu, hareket>. Işık: <...>. Ses: <ortam sesleri>.
```

**Örnek** (10 sn):
```
Akşamüstü, deniz kenarında bir çay bahçesi; arkada martılar ve sakin deniz. Beyaz önlüklü, kır bıyıklı
orta yaşlı bir çaycı solda, elinde ince belli çay bardakları dolu bir tepsiyle duruyor; sağda masada
genç bir kadın oturuyor. Çaycı tepsiyi masaya bırakırken sıcak, tok bir sesle "Çaylar taze, buyurun."
diyor. Kadın gülümseyip "Eline sağlık, tam vaktinde." diyor. Kamera: orta plan, yavaş yaklaşma.
Işık: altın saat, sıcak tonlar. Ses: dalga sesi, uzaktan martılar, bardak şıngırtısı.
```

### Kurallar

- **Süre ve replik dengesi:** 10 sn için toplam 15–20 kelime yeter. Uzun replik dudak senkronunu bozar.
- **Kişi sayısı:** en fazla 2 konuşan kişi. Kalabalık sahne gerekiyorsa arka plan sesi olarak tarif et.
- **Eller ve nesneler:** el–nesne etkileşimini sade tut (bir tepsi, bir bardak). "Bardağı alıp öbür eline geçiriyor" gibi el değiştirmeler kusur üretir. Gemini izlemesi en çok bunları yakalar.
- **Konum:** her kişinin ekranda nerede durduğunu yaz (solda, sağda, önde).
- **Yazı:** ekranda yazı isteniyorsa tam metni tırnak içinde ver. İstenmiyorsa hiç anma.
- **Gerçek yer:** adı geçen gerçek bir yer (Kapalıçarşı, Galata) gerçekteki gibi tarif edilir; Gemini bunu bilir.
- **Ayak sesi ve hayvanlar:** sistem kendi kurallarını uygular (topuk sesi yok, hayvanlar yerde yürür); fikirde bunları tekrarlamana gerek yok.
- **Stil:** `real` dışındaki stillerde (anime, pixar, suluboya) stil tarifini sistem ekler; fikre "anime tarzında" yazmana gerek yok.

### Gemini'nin rolü ve senin rolün

Gemini (`gemini-4-hydrogen`) fikri yönetmen brief'ine, brief'i de H3'ün resmi prompt yapısına çevirir. `check()` denetimi biçimi ve replik doğruluğunu kontrol eder. Senin işin **niyeti korumak**: brief'i okuyup orhan'ın istediği sahne bu mu diye bakmak. Gemini bazen sahneye kendi fikrini ekler; bunu yakalamak sana düşer.

Gemini kotası: ücretsiz katmanda model başına günde yaklaşık 20 istek vardır. Bir üretim yaklaşık 2–3 senaryo isteği ve 1–3 izleme isteği harcar. Ana model yanıt vermezse yedek zincirin her halkası ayrı istek sayılır; bütçeye bunun için %50 pay ekle. Gereksiz yere tekrar çalıştırma.

---

## 5. Maliyet ve süre

Ölçülmüş saatlik oranlar (17 Kasım 2026): **G4 9,92 · A100 6,73 · CPU 0,08 CCU/saat.** H100 henüz denenmedi; ilk kullanımda oranı `colab usage` (`Usage rate`) ile ölç ve raporda yaz.

Ölçülmüş süreler:

| GPU | İş | Süre |
|---|---|---|
| A100 | Kurulum + 53,5 GB model indirme ve doğrulama | ~6 dk |
| A100 | Pika, 5 sn video, render | ~3 dk (170 sn) |
| A100 | Pika, 10 sn Ref2VA | ~6 dk |
| G4 | Pika, 15 sn | ~5–6 dk |
| G4 | MiniMax-H3, 15 sn, 20 adım | ~17–18 dk |

Tahmin: `toplam dk = 6 (kurulum) + aday sayısı × (render + ~1 dk izleme)`. Aday sayısı 1'dir; Gemini "yüksek" kusur bulursa 3'e kadar çıkar. `CCU = dk / 60 × saatlik oran`.

| Örnek | En iyi durum | En kötü durum |
|---|---|---|
| Pika 10 sn, A100 | 13 dk ≈ 1,5 CCU | 27 dk ≈ 3,0 CCU |
| Pika 10 sn, G4 | 13 dk ≈ 2,1 CCU | 27 dk ≈ 4,5 CCU |
| MiniMax-H3 15 sn, G4 | 25 dk ≈ 4,1 CCU | 63 dk ≈ 10,4 CCU |

Not: Pika için A100, G4'ten ucuzdur ve G4 sık sık kapasite hatası (503) veriyor. Orhan maliyeti öne alırsa `--gpu a100,g4` sırasını öner.

Betik, bir üretim yöntemine göre belirlenen süreyi aşarsa çıktıları indirir ve runtime'ı kapatır: pika 45 dk, turbo 30 dk, h3 90 dk. Bu sınırı `--azami-dakika` ile değiştirmek orhan'ın kararıdır.

---

## 6. Hata olursa ne yapılır

| Görülen | Anlamı | Yapılacak |
|---|---|---|
| `G4 alınamadı: ... 503` | G4'te kapasite yok | Betik kendisi tekrar dener ve sıradaki GPU'ya geçer. Bir şey yapma |
| `bu hesapta kullanılamıyor` | Bu GPU hesabın üyeliğinde yok | Betik sıradakine geçer. Raporda yaz |
| Çıkış kodu `3` | Hiçbir GPU alınamadı | CCU harcanmadı. 30–60 dk sonra tekrar dene ya da orhan'a sor |
| `411 Length Required` | CLI yaması eksik | `yama_411.py`'yi çalıştır (2.2), sonra tekrar dene |
| `Allocation refused (precondition failed)` | Çok fazla açık oturum ya da kota | `colab sessions` ile açık oturumlara bak. Senin açtığın, bitmiş bir oturum varsa `h3_uret.py kapat` ile kapat. Başkasınınsa dokunma, orhan'a sor |
| `GPU belleği yetersiz` | 40 GB altı kart geldi | Betik runtime'ı kapattı. Tekrar dene |
| `senaryo.py` kodu `1`, `429` / `RESOURCE_EXHAUSTED` | Gemini kotası doldu | Betik yedek modelleri zaten denedi. Yarın ya da birkaç saat sonra dene; orhan'a bildir |
| `senaryo.py` kodu `1`, `API key not valid` / `403` | Anahtar geçersiz | Orhan'dan yeni anahtar iste |
| `senaryo.py` kodu `2` | Prompt denetimi sorun buldu | Sorun satırlarına göre fikri düzelt (çoğu zaman: replik eksik, ya da tırnak işaretleri farklı) |
| `Runtime'a geçici olarak ulaşılamadı (1/3)` | Colab bağlantısı anlık takıldı | Betik kendisi 15 sn arayla 3 kez dener. Bir şey yapma |
| `Runtime'dan yanıt alınamadı` (3 denemeden sonra), runtime kapandı, `isler: {}` ya da iş yarım | Colab bağlantısı uzun süre takıldı | Aynı senaryoyla **yeni bir oturum klasörüyle bir kez** tekrar başlat. İkinci kez de olursa dur ve orhan'a bildir |
| `Runner süreci durmuş` | Runtime'daki üretim çöktü | `cikti/gunluk.txt` ve `rapor.md`'yi orhan'a gönder. Aynı senaryoyu körlemesine tekrar başlatma |
| `Üretim N dakikayı aştı` | Takıldı ya da çok yavaş | Günlüğü orhan'a gönder |
| `RUNTIME_KAYIP` | Colab runtime'ı kendisi kapattı | `colab usage` ile aktif atamaya bak; günlükleri ve durumu orhan'a bildir |
| `KAPATILAMADI` | Runtime kapatılamadı | **Öncelikli:** `colab stop -s <ad>` ve `colab sessions` ile elle kapat. Olmazsa hemen orhan'a bildir: CCU yanıyor |
| Gemini izlemesi "high" kusur, 3 adayda da | Model bu sahnede zorlanıyor | Raporda belirt. Fikri sadeleştirme önerisini (daha az el hareketi, daha kısa replik) orhan'a sun |

Tabloda olmayan bir hata çıkarsa yeniden deneme. Tam hata metnini, `rapor.md`'yi ve `gunluk.txt`'nin son 30 satırını orhan'a gönder.

---

## 7. Kopma ve yeniden başlama

Makinen yeniden başlarsa ya da `h3_uret.py` yarıda kesilirse, runtime'daki üretim **devam eder**: runner arka planda çalışır. Kaldığın yerden sürdür:

1. Bitmemiş oturumları bul:
   ```bash
   grep -L '"asama": "kapatildi"' ~/workspace/h3uretim/*/oturum*/oturum.json
   ```
2. Her biri için durumu gör, sonra devam ettir:
   ```bash
   ~/workspace/tools/h3muse-venv/bin/python muse/h3_uret.py durum --oturum-dizini <klasör>/oturum
   ~/workspace/tools/h3muse-venv/bin/python muse/h3_uret.py devam --oturum-dizini <klasör>/oturum
   ```
3. `durum` komutu runtime'ın kaybolduğunu söylerse (`RUNTIME_KAYIP`), `colab sessions` ve `colab usage` ile açık atamaya bak ve durumu orhan'a bildir.

İşi bitirmek istemiyorsan ama runtime'ı kapatman gerekiyorsa:
```bash
~/workspace/tools/h3muse-venv/bin/python muse/h3_uret.py kapat --oturum-dizini <klasör>/oturum
```
Bu komut eldeki çıktıları indirmeye çalışır, sonra runtime'ı kapatır.

**Makinen her yeniden başladığında ve her çalışma oturumunun başında**, başka bir işe geçmeden önce 1. adımdaki kontrolü yap. 18 Kasım'da B2 deneyinde böyle bir kesintide `durum` + `devam` işi kaybetmeden sürdürdü. Unutulan bir runtime saatte 7–10 CCU yakar.

---

## 8. Yapılmayacaklar

- Gemini anahtarını `--env`, `colab exec` koduna ya da komut satırına yazma. CLI çalıştırılan kodu yerel geçmiş dosyasına (`~/.config/colab-cli/history/`) kaydeder; anahtar oraya düşer. Anahtar yalnızca `--anahtar` dosyası olarak gider.
- `colab update --install` ya da `pip install -U google-colab-cli` çalıştırma; yama silinir ve yeni sürüm denenmemiştir. Güncelleme uyarısını orhan'a bildir.
- H3 deposunun commit'ini değiştirme, depo dosyalarını düzenleme.
- `colab stop` / `h3_uret.py kapat` komutunu, teslim paketi indirilmeden başka birinin ya da başka bir üretimin oturumunda çalıştırma.
- Aynı anda iki `uret` başlatma.
- Runtime'da `/content` altındaki dosyaları elle silme. Betik indirmeden önce silme yapmaz; runtime kapanınca her şey zaten silinir.
- Drive'daki model klasörlerine güvenme. 18 Kasım'da çöpe taşındılar; modeller her oturumda Hugging Face'ten iner.

---

## 9. Bilinen sınırlar

- **Yazı yasağı tam tutmuyor:** prompt'ta yasak olsa da model tente, tabela ya da cam gibi yüzeylerde okunmayan sözde yazı çizebiliyor (18 Kasım T12'de tentede görüldü). İzleme bunu çoğunlukla "orta" önemde bildirir.
- **Uzun video** bölüm 10'da. Müzikli, konuşmasız kurgu modu henüz yok; yalnızca konuşmalı sahne.
- **Referanslı üretimde stil çizimi** (anime/3D için görselin önce Gemini ile yeniden çizdirilmesi) bu akışta yok; görseller olduğu gibi kullanılır. `real` stil dışında referans görsel kullanacaksan orhan'a sor.
- **Çoklu referans** (karakter + arka plan + nesne) H3 tarafında henüz gerçek GPU'da denenmedi. İlk denemede raporda özellikle belirt.
- **H100** CLI'da var ama bu hesapta hiç denenmedi. İlk alındığında GPU adını, belleğini ve saatlik oranı raporla.
- **MiniMax-H3 Turbo** gerçek GPU'da hiç ölçülmedi.
- **Colab Secrets** başsız okunamaz. Anahtar bu yüzden dosyayla gider; bu beklenen bir durum.
- Çıktılar en fazla ~40 MB'lık parçalar hâlinde iner (Colab dosya aktarım sınırı istek başına ~50 MB); her parça sha256 ile doğrulanır. 47 MB'tan büyük tek bir dosya inemez ve raporda "runtime'da kaldı" olarak listelenir. Seçilen video, prompt'lar, bilgi, kontrol görselleri ve günlük her zaman ilk parçadadır.

## 10. Uzun video (16–60 sn)

### Neden ayrı bir akış

H3 tek seferde en fazla 15 saniye üretir. Uzun video 15 saniyelik bloklardan oluşur ve her blok ayrı üretilir. Eski yöntemde bloklar arasındaki tek bağ birkaç cümlelik bir metindi; model bu metni her blokta biraz farklı yorumladığı için yüz, kıyafet ve mekân bloktan bloğa kayıyordu.

Yeni akışta **kimliği görseller taşır**:

1. **Hikâye kartı:** karakterlerin görünüşü, kıyafeti ve sesi; mekân; ışık; bloklar ve her bloğun replikleri. Kart bir kez yazılır ve bütün bloklarda aynen kullanılır.
2. **Karakter ve mekân görselleri:** Gemini karttan her karakter için boydan bir referans görsel ve boş bir mekân görseli üretir. Orhan'ın kendi görseli varsa o kullanılır.
3. **Her blok Ref2VA ile üretilir:** aynı görseller her bloğa verilir.
4. **Blok başına Gemini izlemesi:** kusurlu blok yeni seed ile yeniden üretilir.
5. **Süreklilik izlemesi:** birleşik video, blok sınırlarında kimlik, kıyafet, mekân, ses ve hikâye açısından 1–10 arası puanlanır.

İsteğe bağlı **köprü** (`--kopru`, deneysel): her bloğa önceki bloğun son karesi de sahne görseli olarak verilir ve o bloğun prompt'u runtime'da yeniden yazılır.

### Adımlar

`D=~/workspace/h3uretim/$(date +%Y%m%d)_<kisa-ad>` ve `PY=~/workspace/tools/h3muse-venv/bin/python`.

**1. Hikâye kartı**
```bash
$PY muse/uzun_senaryo.py kart --dizin $D \
  --fikir '<fikir; replikler çift tırnak içinde>' --sure 30 --stil real
```
`$D/hikaye.json` dosyasını oku. Karakterlerin `gorunum`, `kiyafet` ve `ses` alanları net ve ayırt edici mi? Bloklardaki `replikler` fikirdekiyle harfi harfine aynı mı? Bir şey yanlışsa JSON'u elle düzelt; `_meta` alanına dokunma. Kartı orhan'a özetle ve onay al.

**2. Görseller**
```bash
$PY muse/uzun_senaryo.py gorsel --dizin $D
```
`$D/gorseller/` içindeki `K1.png`, `K2.png`… ve `MEKAN.png` dosyalarına bak. Sorular:
- Görseldeki kişi karttaki tarife uyuyor mu (yaş, saç, kıyafet)?
- Tam boy mu, tek kişi mi?
- Mekân görseli boş mu (insan yok)?

Beğenmediğin görseli yeniden ürettir: `--yeniden K1`. Orhan'ın kendi görseli varsa: `--ref K1=/yol/foto.png` (yalnızca PNG). Görselleri orhan'a göster ve onay al: bundan sonra bütün videonun yüzleri bu görsellerden gelecek.

**3. Plan ve prompt'lar**
```bash
$PY muse/uzun_senaryo.py plan --dizin $D --kol ref
```
Çıktı `$D/uzun_senaryo.json`. Kod `2` ise sorunları oku. Kart kaynaklıysa kartı düzeltip 3. adımı tekrarla.

**4. Onay ve üretim:** onay mesajı bölüm 3, Adım 4'teki gibidir; maliyet için aşağıdaki tabloyu kullan.
```bash
~/workspace/tools/h3muse-venv/bin/python muse/h3_uret.py uret --senaryo $D/uzun_senaryo.json --oturum-dizini $D/oturum
```
Süre sınırı kendiliğinden hesaplanır: `20 + blok × (yeniden üretim + 1) × blok süresi` (pika 14, turbo 8, h3 30 dk).

**5. İnceleme ve teslim:** `$D/oturum/cikti/` içinde `*_ref_*_birlesik.mp4` (asıl video), her bloğun videosu ve kontrol görseli, `*_uzun_sonuc.json` bulunur. Raporda süreklilik puanları ve blok başına izleme sonuçları yer alır. Drive'a birleşik videoyu, `_uzun_sonuc.json`'u, `rapor.md`'yi, `hikaye.json`'u ve `gorseller/` klasörünü yükle.

### Uzun video maliyeti (tahmin)

Ölçüm: A100'de 30 sn / 2 blok = ~6 dk kurulum + blok başına ~11 dk (17 Kasım 2026).

| İş | Süre | A100 | G4 |
|---|---|---|---|
| 30 sn, 2 blok, yeniden üretim yok | ~30 dk | ~3,4 CCU | ~5,0 CCU |
| 30 sn, 2 blok, blok başına 1 yeniden üretim (en kötü) | ~55 dk | ~6,2 CCU | ~9,1 CCU |
| 60 sn, 4 blok, yeniden üretim yok | ~55 dk | ~6,2 CCU | ~9,1 CCU |
| **Deney** (30 sn × 2 kol = 4 blok) | ~55 dk | ~6,2 CCU | ~9,1 CCU |

Gemini kotası: bir uzun video yaklaşık 10–18 istek harcar (kart, görseller, plan, blok prompt'ları, blok izlemeleri, süreklilik). Ücretsiz katmanda günlük sınıra dikkat et; deneyi kotası taze bir günde yap.

### Bilinen sınırlar (uzun video)

- Sesi referansla sabitlemek mümkün değil. H3 sesi kendisi üretir; karttaki ses tarifi her blokta aynı verilir ama ton yine de kayabilir. Süreklilik izlemesindeki `ses` puanı bunu ölçer.
- En fazla 3 karakter; Ref2VA en fazla 9 görsel alır (karakterler + mekân + köprü karesi).
- Köprü deneyseldir; önce deney sonuçlarını bekle.
- `gorsel` adımında Gemini görsel modeli bu hesapta henüz denenmedi. Hata verirse tam mesajı orhan'a ilet; çözüm olarak orhan'dan görsel iste (`--ref`).

---

## Onay noktaları

Bu akışta orhan'ın onayı gereken yerler:

1. **GPU açmadan önce** (Adım 4): senaryo, ayarlar ve tahmini CCU.
2. **Denetimde sorun çıkmış bir senaryoyu üretmeden önce** (`--sorunlu-kabul`).
3. **Varsayılanların dışına çıkarken**: süre sınırı (`--azami-dakika`), GPU sırası, yöntem olarak `h3` (en pahalısı).
4. **Teslimden sonra**: sonucun kabulü ya da yeniden üretim kararı.
5. **Uzun videoda**: hikâye kartı ve karakter/mekân görselleri, üretimden önce ayrı ayrı onaylanır.

Kuru deneme (CPU, ~0,01 CCU) ve senaryo yazımı (yerel, CCU harcamaz) da her zamanki onay kurallarına tabidir.

---

*Bu rehber ve betikler sahte modda test edildi (`tests/test_muse.py`, 17 test). Gerçek Colab ve Gemini ile ilk koşu, 2.6'daki kuru denemedir.*
