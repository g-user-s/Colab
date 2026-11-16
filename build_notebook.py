"""h3app paketini tek bir Colab notebook'una çevirir: her modül kendi %%writefile hücresinde."""

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "notebooks", "h3_video_studyosu.ipynb")
MODULES = ["__init__", "config", "prompt_writer", "graphs", "setup_env", "comfy_client", "qa", "review", "assemble", "ui"]
GRADIO, GENAI = "6.31.0", "2.34.0"

INTRO = """# H3 Video Stüdyosu (grafik arayüzlü uygulama)

Kısa bir fikir yazın → **Gemini** onu önce detaylı bir yönetmen brief'ine, sonra MiniMax-H3'ün resmi `h3-prompt-writing` yapısına çevirsin → **Pika H3 Flex** ve/veya **MiniMax-H3** ile Colab'de video üretin.
İsterseniz **karakter görseli** yükleyin (en fazla 9): uygulama referanslı moda (Ref2VA) geçer, görseldeki kişinin yüzü video boyunca korunur.

**Gerekenler**
1. **Çalışma zamanı → Çalışma zamanı türünü değiştir → G4 GPU** (RTX PRO 6000). Başka GPU'da da çalışır ama NVFP4 yerine daha büyük int8 metin kodlayıcı iner.
2. **Gemini API anahtarı:** Sol paneldeki 🔑 *Secrets* bölümüne `GEMINI` adıyla ekleyip bu notebook'a erişim izni verin. (Ya da anahtarı uygulamadaki şifre kutusuna yazın.)
3. **Çalışma zamanı → Tümünü çalıştır.** Arayüz en alttaki hücrenin altında açılır.

**İlk üretim:** ComfyUI kurulumu + modeller (~42 GB, Hugging Face'ten, SHA-256 doğrulamalı) ~5 dk sürer; sonra Pika ~6 dk, MiniMax-H3 ~18 dk (15 sn video).
Videolar `/content/h3app_videolar/` klasörüne yazılır, arayüzden indirilebilir ve her video biter bitmez Drive'a (`H3_Video_Studyosu`) kopyalanır.\n\n**Bağlantı koparsa:** üretim arka planda sürer. Sayfaya dönünce **📂 Son Üretimleri Yükle**'ye basın: süren iş varsa günlüğü izlenir, bitince sonuçlar yüklenir. Bilgisayar uzun süre uykuda kalırsa Colab runtime'ı silebilir; o zaman bitmiş videolar Drive'dadır.
"""

SETTINGS = """# Videolar üretilir üretilmez Drive'a da kopyalansın mı? Açık bırakın: Colab bağlantısı koparsa (bilgisayar
# uykuya geçti, sekme kapandı) runtime silinebilir; Drive'a yazılmamış videolar kaybolur.
SAVE_TO_DRIVE = True
DRIVE_FOLDER = "/content/drive/MyDrive/H3_Video_Studyosu"
# Model dosyaları önce bu Drive klasörlerinde aranır (boyut + SHA-256 kontrolüyle kopyalanır); bulunamazsa
# Hugging Face'ten iner. Drive'ınızda yoksa sorun değil; istemezseniz [] yapın.
DRIVE_MODEL_DIRS = ["/content/drive/MyDrive/MiniMax-H3/models", "/content/drive/MyDrive/Pika-H3-Flex"]
# Modeller Drive'da yoksa, indirildikten sonra Drive'a da kaydedilsin mi? (DRIVE_MODEL_DIRS'in ilk klasörüne)
# Açarsanız bir sonraki oturumda ~55-65 GB yeniden inmez, Drive'dan alınır. Drive'ınızda bu kadar boş yer
# olmalı (ücretsiz 15 GB'a sığmaz); yer yoksa kopya atlanır. Kopya arka planda yapılır, üretimi bekletmez.
SAVE_MODELS_TO_DRIVE = False  #@param {type:"boolean"}
"""

LAUNCH = f"""import subprocess, sys
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "gradio=={GRADIO}", "google-genai=={GENAI}"], check=True)

drive_dir, model_dirs, model_save_dir = None, [], None
if SAVE_TO_DRIVE or DRIVE_MODEL_DIRS or SAVE_MODELS_TO_DRIVE:
    from google.colab import drive
    drive.mount("/content/drive")
    drive_dir = DRIVE_FOLDER if SAVE_TO_DRIVE else None
    model_dirs = DRIVE_MODEL_DIRS
    if SAVE_MODELS_TO_DRIVE:
        model_save_dir = (DRIVE_MODEL_DIRS or ["/content/drive/MyDrive/MiniMax-H3/models"])[0]

sys.path.insert(0, "/content/h3_video_app")
for m in [m for m in sys.modules if m == "h3app" or m.startswith("h3app.")]:
    del sys.modules[m]
import h3app
h3app.launch(drive_dir=drive_dir, model_dirs=model_dirs, model_save_dir=model_save_dir, server_port=7860)
try:
    from google.colab import output
    print("PROXY_URL:", output.eval_js("google.colab.kernel.proxyPort(7860)"))
except Exception:
    pass
"""

OUTRO = """## Bitince
Menü: **Çalışma zamanı → Çalışma zamanı bağlantısını kes ve sil** (G4 saatte ~10 CU harcar). İndirmediğiniz videolar runtime ile birlikte silinir.

**Sürümler:** ComfyUI `0dbfd49` · Comfy-Org/MiniMax-H3 `912b6e38` · H3 skill `199b7d0e` · gradio """ + GRADIO + """ · google-genai """ + GENAI + """
"""


def cell(kind, src):
    c = {"cell_type": kind, "metadata": {}, "source": src.strip("\n").splitlines(True)}
    if kind == "code":
        c.update(execution_count=None, outputs=[])
    return c


cells = [cell("markdown", INTRO), cell("markdown", "## 1 · Ayarlar"), cell("code", SETTINGS),
         cell("markdown", "## 2 · Uygulama dosyaları\nHer hücre bir modülü `/content/h3_video_app/h3app/` altına yazar. Kaynak kod burada açıkça okunabilir.")]
for m in MODULES:
    src = open(os.path.join(HERE, "h3app", m + ".py"), encoding="utf-8").read()
    cells.append(cell("code", f"%%writefile /content/h3_video_app/h3app/{m}.py\n" + src))
cells += [cell("markdown", "## 3 · Uygulamayı başlat"), cell("code", LAUNCH), cell("markdown", OUTRO)]
# %%writefile klasörü kendisi açmaz: ilk modül hücresinden önce klasörü oluştur
cells.insert(4, cell("code", "import os\nos.makedirs(\"/content/h3_video_app/h3app\", exist_ok=True)"))
nb = {"cells": cells, "metadata": {"colab": {"provenance": [], "gpuType": "G4"}, "accelerator": "GPU",
      "kernelspec": {"name": "python3", "display_name": "Python 3"}, "language_info": {"name": "python"}},
      "nbformat": 4, "nbformat_minor": 0}
json.dump(nb, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(os.path.abspath(OUT), len(cells), "hücre")
