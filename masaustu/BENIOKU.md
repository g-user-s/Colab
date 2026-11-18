# H3 Stüdyo — Linux masaüstü uygulaması

H3 Video Stüdyosu ile Türkçe konuşmalı video üretmek için masaüstü uygulaması.
- 4–15 sn'lik tek video;
- 16–60 sn'lik uzun video. Karakter ve mekân görselleriyle üretildiği için bloklar boyunca aynı kişiler ve aynı mekân korunur (bkz. `DENEY_SONUCLARI.md`).

**Bu bilgisayarda GPU gerekmez.** GPU işi Google Colab'de yapılır. Senaryo, hikâye kartı, görseller, Gemini izlemesi, indirme ve rapor bu bilgisayarda çalışır. Muse'un kullandığı komut satırı betikleriyle aynı kodu kullanır.

## Gerekenler

- Linux. Ubuntu 24.04+ ve Fedora 39+'te Python 3.12 hazır gelir.
- Python 3.12 veya üstü, `ffmpeg`.
- Bir Google hesabı ve Colab işlem birimi (CCU). Pro/Pro+ üyeliği G4 ve A100 için gerekli.
- Gemini API anahtarı: <https://aistudio.google.com/apikey>.

## Kurulum

```bash
sudo apt install ffmpeg git          # Fedora: sudo dnf install ffmpeg git
git clone -b claude/trusting-johnson-c5d0tf https://github.com/g-user-s/Colab ~/H3Studyo
bash ~/H3Studyo/masaustu/kur.sh
```

Kurulum betiği şunları yapar:
- kendi Python ortamını kurar (`~/.local/share/h3studyo`);
- PySide6, Gemini kütüphanesi ve Colab CLI'yı kurar, Colab CLI'ya 411 yamasını uygular;
- uygulama menüsüne **H3 Stüdyo**'yu ekler.

Sistem paketlerine dokunmaz. Kurulumdan sonra uygulamayı menüden ya da `~/.local/bin/h3studyo` ile aç.

Pencere açılmazsa ve "could not load the Qt platform plugin xcb" hatası görürsen: `sudo apt install libxcb-cursor0`.

**Güncelleme:** `cd ~/H3Studyo && git pull`. Kurulumu tekrarlamak gerekmez, yalnızca paket sürümleri değişirse gerekir.

## İlk kullanım (bir kez)

**Durum ve kurulum** sekmesinde her satır ✅ olmalı:

1. **Giriş yap…** → Google sayfası açılır. Colab'e izin ver, Google'ın gösterdiği kodu pencereye yapıştır, **Gönder**'e bas. Giriş bilgisi sistem anahtarlığında saklanır. Anahtarlık yoksa düz dosyada saklanır; kurulum bunu kendisi ayarlar.
2. **Gemini anahtarı:** anahtarı kutuya yapıştır → **Kaydet** → **Dene**. Anahtar `~/.config/h3muse/gemini.key` dosyasında yalnızca sana açık izinle (600) durur ve Colab'e hiç gönderilmez.
3. **Kuru deneme:** Colab'de CPU runtime açar, sahte bir video üretip indirir ve kapatır. Maliyeti yaklaşık 0,01 CCU. Bu adım giriş, yükleme, indirme ve kapatma adımlarının senin bilgisayarında çalıştığını doğrular.

## Video üretmek

**Yeni video** sekmesi:

1. **Fikir.** Kim, nerede, ne yapıyor, ekranda nerede duruyor? Türkçe replikleri çift tırnak içinde, harfi harfine yaz. Tür, süre, stil ve yöntemi seç. Pika H3 Flex önerilir.
2. **Tek video:** **Senaryo yaz.** Gemini önce bir brief, sonra H3 prompt'unu yazar. Brief'i düzenleyip prompt'u yeniden yazdırabilirsin.
3. **Uzun video:**
   - **Hikâye kartı yaz.** Kart; karakterlerin görünüşünü, kıyafetini ve sesini, mekânı ve blokları tek bir yerde toplar. Tablolardan düzelt, **Kaydet ve denetle**.
   - **Görseller.** Her karakter için boydan bir görsel ve boş bir mekân görseli üretilir. Beğenmediğini **Yeniden üret**, ya da **Kendi görselim…** ile kendi PNG'ni ver. Mekân görselinde, sonradan getirilecek bir nesne (örneğin servis edilecek çay) şimdiden görünmemeli.
   - **Plan yaz ve üretime geç.**
4. **Onay penceresi** tahmini süreyi ve CCU'yu gösterir. Onaylarsan Colab'de GPU açılır.
5. **Üretim** sekmesi aşamayı, canlı günlüğü ve açık kalma süresini gösterir. Her video bu bilgisayardan Gemini'ye izletilir. Yüksek önemde kusur varsa aynı runtime'da yeni seed ile tekrar üretilir. Bitince video, rapor ve izleme kusurları gösterilir.

**Yeniden üretim eşiği:**
- *Yüksek* (varsayılan) yalnızca belirgin kusurlarda yeniden üretir.
- *Orta* el ve nesne kaynaşması gibi küçük kusurları da yeniden üretir. Daha temiz sonuç verir, ama yaklaşık iki kat CCU harcar.

## Maliyet (ölçülmüş)

| İş | A100 |
|---|---|
| 8 sn tek video | ~12 dk, ~1,4 CCU |
| 45 sn uzun video (3 blok) | ~47 dk, ~5,3 CCU |

GPU sırası varsayılan olarak A100, sonra G4'tür. A100 Pika için G4'ten ucuz (6,73 / 9,92 CCU/saat) ve genellikle daha kolay bulunuyor. G4 sık sık "503: kapasite yok" veriyor; uygulama bu durumda kendisi tekrar dener.

## Uygulama kapanırsa

Üretim uygulamadan bağımsız çalışır. Pencereyi kapatmak ya da bilgisayarın yeniden başlaması işi durdurmaz; GPU işi Colab'de sürer.

Uygulama açılışta bitmemiş üretimleri kontrol eder. Onları yöneten süreç çalışmıyorsa uyarır, çünkü Colab runtime'ı açık kalıp **CCU yakıyor olabilir**. **Üretimler** sekmesinde:
- **Devam** kaldığı yerden sürdürür; iş baştan başlamaz;
- **Kapat** runtime'ı kapatır.

## Dosyalar

Her video `~/H3Uretimler/<tarih>_<ad>/` altındadır:
- `fikir.txt`;
- `senaryo.json` ya da `hikaye.json`, `gorseller/` ve `uzun_senaryo.json`;
- `oturum/cikti/`: video, kontrol görselleri, prompt'lar;
- `oturum/rapor.md`;
- `oturum/uygulama.log`.

Üretim klasörü **Durum ve kurulum** sekmesinden değiştirilebilir.

## Sorun giderme

| Görülen | Yapılacak |
|---|---|
| Durum: "Colab CLI 411 yaması: yok" | **Yamayı uygula.** Colab CLI güncellenirse yama silinir; bu durumda da aynısını yap |
| Giriş her açılışta soruluyor | "Sistem anahtarlığı yok" kutusunu işaretle, sonra yeniden giriş yap |
| "İstenen GPU'ların hiçbiri alınamadı" | Kapasite yok, CCU harcanmadı. Biraz sonra tekrar dene ya da GPU sırasını değiştir |
| Gemini "yedek modelle yazıldı" uyarısı | Ana model yoğun. Kalite önemliyse birkaç dakika sonra senaryoyu yeniden yazdır |
| Durum: "Sunucudaki oturumlar: N açık oturum" ve süren bir üretimin yok | Üretimler sekmesinde açık kalanı bul ve **Kapat** |

## Geliştirme

Testler ekransız Qt ve sahte Colab ile uçtan uca çalışır: tek video, uzun video (kart düzenleme ve görseller), giriş penceresi, kesinti sonrası devam.

```bash
pip install PySide6==6.8.1 pytest pytest-qt -r h3/requirements-dev.txt
cd masaustu && QT_QPA_PLATFORM=offscreen python -m pytest -q tests
```
