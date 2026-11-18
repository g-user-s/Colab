# T13 — Video izleme: Muse ile Gemini, kör karşılaştırma

**Depo:** https://github.com/g-user-s/Colab (dal `claude/trusting-johnson-c5d0tf`). Önce: `cd ~/workspace/Colab && git pull`.

**Amaç:** Üretilen videoları bugün Gemini izliyor ve kusur arıyor: fazladan el, kimlik kayması, yanlış replik, dudak senkronu. Bu işi senin de yapıp yapamayacağını, yapabiliyorsan ne kadar iyi yaptığını öğrenmek istiyoruz. Yapamadığın kısımları açıkça yazman en az iş yapabildiklerin kadar değerli.

**Maliyet:** CCU 0, Gemini 1 istek. T12'nin videosu kullanılır, yeni üretim yok.

```bash
V=$(ls ~/workspace/h3uretim/test_t5/oturum/cikti/*_seed*.mp4 | grep -v kontrol | head -1)
D=~/workspace/h3uretim/test_t13; mkdir -p $D; echo "$V"
```
(Kabuk değişkenleri komutlar arasında kaybolabilir; her komutta tam yolu yazman daha güvenli.)

---

## 1. Ham yetenek

T12'nin videosunu (`.mp4`) doğrudan açmayı dene ve şu soruları cevapla:
- Videoyu açabiliyor musun?
- Hareketi, yani kareler arasındaki değişimi görebiliyor musun, yoksa yalnızca tek bir kare mi görüyorsun?
- Sesi duyabiliyor musun? Konuşmayı anlayabiliyor musun?

Ne algıladığını dürüstçe yaz. Görmediğin bir şeyi tahminle doldurma.

## 2. Kareler

Videodan saniyede 2 kare çıkar ve hepsine bak:
```bash
mkdir -p ~/workspace/h3uretim/test_t13/kareler
ffmpeg -v error -i "<video yolu>" -vf fps=2,scale=640:-2 ~/workspace/h3uretim/test_t13/kareler/k_%03d.jpg
ls ~/workspace/h3uretim/test_t13/kareler | wc -l
```
Ayrıca aynı klasördeki `_kontrol.jpg` (temas sayfası) ve `_kirpinti.jpg` (%100 kırpıntılar) dosyalarına bak. `k_005.jpg`, videonun yaklaşık 2. saniyesidir: kare numarası ÷ 2 ≈ saniye.

## 3. Ses

Sesi dinleyemiyorsan bunu yaz ve geç. Yeni bir araç kurma.

## 4. Kör değerlendirme: önce sen

**Gemini'nin sonucuna bakmadan önce** kendi değerlendirmeni yaz. Şunları açma:
- `_bilgi.json` dosyasındaki `inceleme` alanı;
- `gunluk.txt` dosyasındaki 🔍 satırları;
- rapordaki izleme satırı.

1. `h3/h3app/review.py` dosyasındaki `CHECKLIST` metnini oku. Bu, Gemini'ye verilen kontrol listesidir.
2. Videonun prompt'u `~/workspace/h3uretim/test_t5/senaryo.json` dosyasındaki `prompt` alanında.
3. Listeyi uygula ve sonucu aynı JSON biçiminde `~/workspace/h3uretim/test_t13/muse_inceleme.json` dosyasına yaz:
   ```json
   {"verdict": "pass|fail",
    "defects": [{"start_s": 0, "end_s": 0, "severity": "high|medium|low", "category": "...", "description": "..."}],
    "summary": "...",
    "kontrol_edemediklerim": ["ör. dudak senkronu: ses duyamıyorum"]}
   ```
   `kontrol_edemediklerim` alanı yalnızca senin için var; kontrol edemediğin her maddeyi oraya yaz.

## 5. Gemini'nin değerlendirmesi

Şimdi aynı videoyu Gemini'ye, bu sefer **senin makinenden** izlet:
```bash
~/workspace/tools/h3muse-venv/bin/python muse/izle.py --video "<video yolu>" \
  --senaryo ~/workspace/h3uretim/test_t5/senaryo.json --cikti ~/workspace/h3uretim/test_t13/gemini_inceleme.json
```

Sonra T12'nin kendi izlemesine bak: `_bilgi.json` dosyasındaki `inceleme` alanı ve `gunluk.txt` dosyasındaki 🔍 satırları. Bunlar Colab runtime'ından yapılan izlemeydi. Orada hata varsa tam satırı yaz (anahtar benzeri bir şey görürsen `***` yap).

## 6. Karşılaştırma

Bir tablo yap:

| Kusur (zaman, kısa tarif) | Muse buldu mu | Gemini buldu mu | Karelere tekrar bakınca: gerçek mi? |
|---|---|---|---|

Sonra şu soruları cevapla:
- Gemini'nin bulup senin kaçırdığın kusurlar neler? Neden kaçırdın? (Ör. ses, hareket, iki kare arasında kalması.)
- Senin bulup Gemini'nin kaçırdıkları neler?
- Bu videoda hangi değerlendirme daha doğruydu? Neden?
- Senin izlemen hangi kontroller için Gemini'nin yerini tutabilir, hangileri için tutamaz?

---

Sonucu `RAPOR T13` başlığıyla tek mesajda gönder. `muse_inceleme.json` ve `gemini_inceleme.json` dosyalarının içeriğini de ekle.
