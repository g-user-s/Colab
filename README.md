# H3 Video Stüdyosu

Kısa bir video fikrini, **Google Colab** üzerinde açık ağırlıklı video+ses modelleriyle (**MiniMax-H3**, **Pika H3 Flex**) sesli videoya çeviren, grafik arayüzlü bir uygulama. Türkçe konuşmalı sahneler için tasarlandı: replikler ayrı bir seslendirme (TTS) yerine doğrudan video modelinin kendi sesiyle üretilir.

> **English summary:** A Gradio app that runs in Google Colab. You type a short video idea; Gemini expands it into a director's brief and then into a prompt in MiniMax-H3's official prompt format; ComfyUI renders a video with native audio using Pika H3 Flex, MiniMax-H3 or MiniMax-H3 Turbo. Optional reference images keep a character's identity (Ref2VA). Built and tested for Turkish dialogue. Code is MIT-licensed; the models have their own licenses.

## Nasıl çalışır

```
kısa fikir ──► Gemini: yönetmen brief'i ──► Gemini: H3 prompt'u (resmi yapı) ──► ComfyUI: Pika / H3 / Turbo ──► video + ses
                                                                                                 │
                                          otomatik kontrol (kesmeler, donma, ses seviyesi, stil) ◄┘ ──► Drive'a kayıt
```

- **⚡ Hızlı üretim:** Arayüzün en üstünde tek düğmeli panel: fikir, süre, stil ve yöntem seçilir, **Fikirden videoya: hepsini yap** ile brief, prompt ve video sırayla yapılır; durum tek satırda yazar (`⏳ 1/3 …`, `⏳ 3/3 …`, `✅ Hazır: …` ya da `❌ Hata: …`).
- **Fikirden prompt'a:** Gemini önce fikri kamera, ışık, ses ve oyunculuk ayrıntılarıyla bir brief'e, sonra MiniMax-H3'ün resmi `h3-prompt-writing` yapısına çevirir. Tırnak içindeki ekran yazıları ve Türkçe replikler harfi harfine korunur ve denetlenir.
- **Referanslı mod (Ref2VA):** En fazla 9 görsel yüklenebilir ve her birine rol verilir: **Karakter** (yükleme sırasıyla Karakter 1, 2… ve konuşurlarsa S1, S2…), **Arka plan / mekân** (sahne o yerde geçer, görselden kişi çıkarılmaz) ya da **Nesne**. İsteğe bağlı ad verilebilir (ör. "Çaycı Ahmet") ve fikirde o adla anılabilir. Karakterlerin kimliği video boyunca korunur.
- **Stiller:** Gerçek dünya, Anime, Disney-Pixar tarzı 3D ve Suluboya. Çizgi/3D stillerde referans görsel önce Gemini ile o stilde yeniden çizdirilebilir.
- **Üç yöntem:** Pika H3 Flex (6 adım), MiniMax-H3 (20 adım), MiniMax-H3 Turbo (4/8 adım).
- **Uzun video (15–60 sn):** Fikir 15 saniyelik çok çekimli bloklara bölünür, bloklar kare-tam birleştirilir. İki ses modu var: konuşmalı sahne ya da yüklediğiniz telifsiz müzikle konuşmasız kurgu. Beğenmediğiniz tek bir blok yeni seed ile yeniden üretilebilir.
- **Otomatik izleme ve yeniden üretim:** Her video bitince Gemini videoyu **sesiyle birlikte izler** ve zaman damgalı kusur listesi verir (fazladan el/kişi, elden ele ışınlanan nesne, istenmeyen bakış açısı, kimlik kayması, anlamsız yazı, replik ve dudak uyumu, ilk/son 2 saniye). Yüksek önemde kusur varsa yeni seed ile en fazla 2 kez (ayarlanabilir) yeniden üretilir ve en az kusurlu aday seçilir. İzleme için `gemini-2.5-flash` → `gemini-3-flash-preview` kullanılır; bir kör testte ikisi de gerçek bir hatayı (kadraja giren gövdesiz el) buldu, `3.5-flash-lite` bulamadığı için izlemede kullanılmaz. Gemini'ye ulaşılamazsa video yine kaydedilir.
- **Otomatik kontrol:** Kesme zamanları prompt'la karşılaştırılır; donmuş kareler, sondaki bozulma, stil tutarlılığı ve konuşma varlığı ölçülür. Ses -16 LUFS'a dengelenir; temas sayfası ve %100 kırpıntılar çıkarılır.
- **Kesintiye dayanıklı:** Üretim arka planda koşar; tarayıcı sekmesi kapansa da video kopyalanır, kontrol edilir ve Drive'a yazılır. Geri dönünce **📂 Son Üretimleri Yükle** süren işi izler ya da sonuçları yükler.

## Hızlı başlangıç (Colab)

1. [`notebooks/h3_video_studyosu.ipynb`](notebooks/h3_video_studyosu.ipynb) dosyasını Colab'de açın: **Dosya → Not defteri aç → GitHub** sekmesine bu reponun adresini yazın ya da dosyayı indirip **Yükle** sekmesinden açın.
2. **Çalışma zamanı → Çalışma zamanı türünü değiştir → G4 GPU** seçin. G4 yoksa A100 de çalışır (aşağıdaki ölçümlere bakın).
3. Sol paneldeki 🔑 **Secrets** bölümüne Gemini API anahtarınızı `GEMINI` adıyla ekleyin ve bu notebook'a erişim izni verin. Anahtar [Google AI Studio](https://aistudio.google.com/)'dan alınır. İsterseniz anahtarı arayüzdeki şifre kutusuna da yazabilirsiniz.
4. **Çalışma zamanı → Tümünü çalıştır.** Drive bağlantı izni istenir (videoların kaybolmaması için önerilir; istemiyorsanız ayarlar hücresinde `SAVE_TO_DRIVE = False` yapın).
5. Arayüz en alttaki hücrenin altında açılır. Hücre çıktısındaki `PROXY_URL` bağlantısı aynı arayüzü tam sayfa açar.

İlk üretimde ComfyUI kurulur ve modeller Hugging Face'ten sabit bir revizyondan indirilir (~55–65 GB); her dosya SHA-256 ile doğrulanır. Modeller Drive'ınızda varsa (`DRIVE_MODEL_DIRS`) önce oradan kopyalanır.

**Modelleri Drive'a kaydetmek (isteğe bağlı):** Ayarlar hücresindeki `SAVE_MODELS_TO_DRIVE` kutusunu işaretlerseniz, Drive'da bulunmayan her model indirilip doğrulandıktan sonra arka planda `DRIVE_MODEL_DIRS`'in ilk klasörüne de kopyalanır; sonraki oturumlarda modeller Drive'dan alınır. Bunun için Drive'da ~55–65 GB boş yer gerekir (ücretsiz 15 GB'a sığmaz); yer yoksa kopya atlanır ve üretim etkilenmez. Varsayılan olarak kapalıdır.

**Tarayıcı kullanan yapay zekâ ajanlarıyla:** Hızlı üretim paneli, tarayıcıyı kullanabilen kişisel ajanların (ör. Meta Muse; henüz Muse ile denenmedi) da uygulamayı çalıştırabilmesi için sade tutuldu. Öğelerin sabit kimlikleri var: `hizli-fikir`, `hizli-sure`, `hizli-stil`, `hizli-yontem`, `hizli-uret` (düğme), `hizli-durum` (durum satırı), `hizli-video`, `hizli-dosyalar`. Ajan durum satırı `✅` ya da `❌` ile başlayana kadar beklemelidir. Colab oturumu Google hesabınıza bağlıdır; ajana bu erişimi vermeden önce iyi düşünün.

**İşiniz bitince:** Çalışma zamanı → Çalışma zamanı bağlantısını kes ve sil. GPU açık kaldıkça Colab işlem birimi harcar.

## Ölçülen süreler

| Ortam | İş | Süre |
|---|---|---|
| A100 80 GB | İlk kurulum: ComfyUI + 53,5 GB model indirme ve doğrulama | ~6 dk |
| A100 80 GB | Pika H3 Flex, 10 sn, 1344×768, Ref2VA (6 adım × ~51 sn) | ~6 dk |
| G4 (RTX PRO 6000) | Pika H3 Flex, 15 sn, 1344×768 | ~5–6 dk |
| G4 (RTX PRO 6000) | MiniMax-H3, 15 sn, 1344×768, 20 adım | ~17–18 dk |

MiniMax-H3 Turbo henüz gerçek GPU'da ölçülmedi.

## Gemini modelleri

Prompt yazımı sırayla şu modelleri dener: `gemini-4-hydrogen` → `gemini-3.8-flash` → `gemini-3.5-flash-lite` → `gemma-4-31b-it`. Her model ilk metin parçasını en fazla **10 saniye** içinde göndermelidir. Göndermezse ya da yoğunluk/kota hatası (503/429) verirse uygulama beklemeden sıradakine geçer ve bunu arayüzde yazar. Sıra ve süre [`h3app/config.py`](h3app/config.py) içinde değiştirilebilir.

Ücretsiz Gemini katmanında model başına günlük istek sınırı düşüktür (ör. 20). Hangi modellerin sizin anahtarınızla yanıt verdiğini ve ne kadar sürdüğünü görmek için:

```bash
GEMINI=... python tools/gemini_hiz_testi.py --filtre flash
```

Her ölçüm günlük kotadan bir istek harcar.

## Geliştirme

GPU gerekmez; testler sahte video ve sahte Gemini istemcisiyle çalışır. Sistemde `ffmpeg` ve `ffprobe` kurulu olmalıdır.

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
python -m pytest -q
```

Kodu değiştirdikten sonra notebook'u yeniden üretin; her modül kendi `%%writefile` hücresine yazılır:

```bash
python build_notebook.py
```

Arayüzü GPU'suz denemek için: `H3APP_FAKE=1 H3APP_FAKE_VIDEO=ornek.mp4 H3APP_WORK_DIR=/tmp/h3 python -c "import h3app; h3app.launch(inline=False, prevent_thread_lock=False)"`

| Dosya | Görev |
|---|---|
| `h3app/prompt_writer.py` | Gemini ile brief, H3 prompt'u, çekim planı; çıktı denetimi; model zinciri |
| `h3app/graphs.py` | ComfyUI API grafikleri (T2VA ve Ref2VA; Pika, H3, Turbo) |
| `h3app/setup_env.py` | ComfyUI kurulumu, model indirme ve SHA-256 doğrulama |
| `h3app/comfy_client.py` | Arka plandaki ComfyUI sunucusu ve iş kuyruğu |
| `h3app/qa.py` | Otomatik kalite kontrolü ve ses dengeleme |
| `h3app/assemble.py` | Uzun video bloklarının birleştirilmesi ve ses miksajı |
| `h3app/ui.py` | Gradio arayüzü, arka plan işleri, Drive'a kayıt |
| `build_notebook.py` | Paketi tek bir Colab notebook'una çevirir |

## Bilinen sınırlar

- Colab'in tam sayfa proxy'si (`*.colab.dev`) canlı günlüğü tamponlayabilir; uygulama bunu sık güncellemeyle hafifletir, ama günlük birkaç saniye gecikebilir.
- Bilgisayar uzun süre uykuda kalırsa Colab runtime'ı silebilir. Bitmiş videolar Drive'a yazıldığı için korunur; yarım kalan üretim kaybolur.
- Uzun video (çok bloklu) modu yalnızca sahte modda test edildi; gerçek GPU'da henüz denenmedi.
- Gerçek GPU'da yalnızca tek referans görselle üretim yapıldı; birden fazla görsel ve rol (karakter + arka plan + nesne) henüz denenmedi.
- H3 tek üretimde 5–15 saniye için eğitilmiştir; daha uzun videolar bloklar hâlinde üretilir.

## Lisanslar

- **Bu reponun kodu:** [MIT](LICENSE).
- **Modeller bu repoda yoktur**; çalışma anında Hugging Face'ten indirilir ve **kendi lisanslarına tabidir**: [MiniMax-H3](https://huggingface.co/Comfy-Org/MiniMax-H3) ağırlıkları ve Pika H3 Flex LoRA'ları. Özellikle ticari kullanımdan önce ilgili model kartlarını ve lisansları okuyun.
- MiniMax'in resmi `h3-prompt-writing` rehberi de repoda dağıtılmaz; çalışma anında [MiniMax-AI/MiniMax-H3](https://github.com/MiniMax-AI/MiniMax-H3) deposundan sabit bir commit'ten indirilip doğrulanır.
- Gemini API kullanımı Google'ın koşullarına tabidir.
- Ürettiğiniz videoların (özellikle gerçek kişilere ait referans görsellerle) sorumluluğu kullanıcıya aittir.
