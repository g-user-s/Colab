"""Sabit sürümler ve ayarlar. Hepsi 01.11.2026'da test edilmiş sürümlere sabitlenmiştir."""

import os

WORK_DIR = os.environ.get("H3APP_WORK_DIR", "/content")
COMFY_DIR = os.path.join(WORK_DIR, "ComfyUI")
OUTPUT_DIR = os.path.join(WORK_DIR, "h3app_videolar")
CACHE_DIR = os.path.join(WORK_DIR, "h3app_cache")
# Model dosyalarının önce aranacağı klasörler (ör. Drive'daki doğrulanmış kopyalar); launch(model_dirs=...) doldurur
MODEL_SOURCE_DIRS = []
# Drive'da bulunmayan modeller indirildikten sonra buraya da kopyalanır (None: kapalı); launch(model_save_dir=...) doldurur
MODEL_SAVE_DIR = None

COMFY_REPO = "https://github.com/Comfy-Org/ComfyUI.git"
COMFY_COMMIT = "0dbfd49"
COMFY_PORT = 8188

HF_REPO = "Comfy-Org/MiniMax-H3"
HF_REVISION = "912b6e38b2092ec4d2e86d24183e0d59ea059d48"

# rol -> (depodaki yol, ComfyUI models alt klasörü, boyut, sha256)
MODELS = {
    "unet": ("diffusion_models/minimax_h3_fl2va_pruned_int8_convrot.safetensors", "diffusion_models",
             20970379616, "e889202c41dafb67b10d67b97f0d8541508036a6090af23425a5c2615d03c47a"),
    "te_nvfp4": ("text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors", "text_encoders",
                 15687142551, "35a88d51044231fe332301d7a62aa81e3f2cba62febeb446e2c1e3e0ef76f2c6"),
    "te_int8": ("text_encoders/qwen3vl_32b_minimax_h3_int8_convrot.safetensors", "text_encoders",
                27141342152, "bc2ced0fbea64757fa9acddccfc0b3f4819d1dcf1da6c124d690d368be283923"),
    "vae_video": ("vae/minimax_h3_video_vae_int8_convrot.safetensors", "vae",
                  2811065184, "52a2c8c73583c86e4f41cdcce3a6ad0ea562987bc0bf3d60a0cef5f5c8e60c0e"),
    "vae_audio": ("vae/minimax_h3_audio_vae_fp32.safetensors", "vae",
                  605254808, "8e505d95dd1561d47abd43d4238fd40d9bb1ae9e147ed0a4cba778d76ae4db48"),
    "pika_lora": ("loras/pika_h3_flex_fl2va_v1_bf16.safetensors", "loras",
                  1956172304, "cc5453aeecd6189468409003fe4cf1b57e52ff3a830a0a154b87decbe07358b7"),
    # Referanslı üretim (Ref2VA): yüklenen karakter/sahne görselleri
    "unet_ref": ("diffusion_models/minimax_h3_ref2va_pruned_int8_convrot.safetensors", "diffusion_models",
                 20970379616, "9255f52b6677845ad238f20dfaafa94727053694127ab7f255c048f0f9365779"),
    "pika_lora_ref": ("loras/pika_h3_flex_ref2va_v1_bf16.safetensors", "loras",
                      1956172304, "de3745ceb7d8d5c20898dd8fa3a05f1c0b00089ccd55297b2a8bab95c766b0e0"),
    # H3 Fast / Turbo LoRA (LightX2V / Comfy-Org resmi şablonları: T2VA 8 adım, Ref2VA 4 adım)
    "turbo_lora": ("loras/minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors", "loras",
                   1956193000, "2339acdf19bfe123f46b971ea35d367a84adb85de43627e1eceafa5a5b2b111e"),
    "turbo_lora_ref": ("loras/minimax_h3_ref2v_turbo_4step_v0.1_comfyui_bf16.safetensors", "loras",
                       1956193000, "5b9ab5ade15d0775676d01a907268a69a1468dc6033b3b0d3ded5502f3ebb84c"),
}

# H3'ün resmi prompt yazım skill'i (MiniMax'in deposundan, sabit commit, git blob sha ile doğrulanır)
SKILL_REPO = "MiniMax-AI/MiniMax-H3"
SKILL_COMMIT = "199b7d0e1fd95e7b3eafa8c15eca692534142427"
SKILL_FILES = {
    "skills/h3-prompt-writing/SKILL.md": "b6d9b2839384a588763a9c24315225dd8ce19d56",
    "skills/h3-prompt-writing/references/base-en.txt": "40cf586a634d677d6b7107b367cf0ec9621be728",
    "skills/h3-prompt-writing/references/ref-en.txt": "7ae1b2d07d743fd2392258a96449be9e9e322d35",
}

# Pika H3 Flex'in resmi 6 adımlık programı (knot'lar 1000/750/500/250/100/40/0, video shift 12)
PIKA_SIGMAS = "1.0, 0.972973, 0.923077, 0.8, 0.571429, 0.333333, 0.0"
H3_STEPS = 20
TURBO_STEPS = 8
TURBO_REF_STEPS = 4

METHODS = {
    "turbo": {"label": "MiniMax-H3 Turbo (4/8 adım, G4'te ~2-3 dk)", "file": "minimax_h3_turbo"},
    "pika": {"label": "Pika H3 Flex (6 adım, G4'te ~6 dk)", "file": "pika_h3_flex"},
    "h3": {"label": "MiniMax-H3 (20 adım, G4'te ~18 dk)", "file": "minimax_h3"},
}

RESOLUTIONS = {
    "16:9 yatay · 1344×768": (1344, 768),
    "9:16 dikey · 768×1344": (768, 1344),
    "1:1 kare · 1024×1024": (1024, 1024),
}

# Görsel stil. Prompt'a marka adı değil tarif yazılır; anime/3d/suluboya tarifleri scenario-alter skill'inin
# (MIT) denenmiş restyle cümlelerinden. "real" bugünkü davranıştır: prompt'lar stil seçimi eklenmeden önceki gibi kalır.
STYLES = {
    "real": {"label": "Gerçek dünya", "kind": "photoreal live-action"},
    "anime": {
        "label": "Anime", "kind": "hand-drawn 2D anime",
        "look": "a hand-drawn 2D anime feature film: clean ink lines, flat cel shading with one shadow tone, "
                "painted backgrounds",
        "people": "hand-drawn anime characters",
        "background": "hand-painted anime background art with flat colour areas and painted clouds",
        "avoid": "glossy 3D render, CGI lighting, photorealism, live-action skin texture, photographic background",
        "keywords": ("anime",),
    },
    "pixar": {
        "label": "Disney Pixar", "kind": "stylised 3D animated feature film",
        "look": "a 3D animated feature film: stylised characters with slightly larger heads and hands, exaggerated "
                "rounded proportions, smooth stylised skin and sculpted hair, soft global illumination, a stylised 3D set",
        "people": "stylised 3D animated characters",
        "background": "a stylised 3D set: soft rounded shapes, sculpted clouds, clean simple surfaces",
        "avoid": "photorealism, live-action footage, real skin pores, photographic water and sky, 2D flat shading",
        "keywords": ("3d animated", "3d-animated", "3d animation"),
    },
    "watercolour": {
        "label": "Suluboya", "kind": "hand-painted watercolour animation",
        "look": "a moving watercolour painting on textured paper: visible brush strokes that follow the motion, "
                "soft edges and a little pencil underdrawing",
        "people": "loosely painted watercolour figures with visible wet-on-wet pigment bleed, soft unpainted paper "
                  "highlights on faces and clothes, simplified hand-drawn ink outlines, zero skin texture",
        "background": "loose watercolour washes on textured paper and a few confident brush strokes",
        "avoid": "photorealism, live-action footage, 3D render, CGI lighting, sharp photographic detail, "
                 "realistic human faces, smooth digital airbrushing, solid opaque skin shading",
        "keywords": ("watercolour", "watercolor"),
    },
}
DEFAULT_STYLE = "real"

# Ses seviyesi standardı (EBU R128 loudnorm hedefi)
TARGET_LUFS = -16.0

# Prompt yazımı için model zinciri (kullanıcının sırası, 16.11.2026): önce varsayılan, yanıt gelmezse yedekler sırayla.
# Arayüzde başka bir model seçilirse o önce denenir, ardından bu zincir. Gemma sistem talimatını mesajın başında alır.
GEMINI_MODEL = "gemini-4-hydrogen"
GEMINI_FALLBACK_MODELS = ("gemini-3.8-flash", "gemini-3.5-flash-lite", "gemma-4-31b-it")
# Her model ilk metin parçasını bu kadar saniyede göndermezse ya da yoğunsa (503/429) sıradakine geçilir
FIRST_CHUNK_SECONDS = 10
# Üretilen videoyu izleyen Gemini modelleri (sırayla). 16.11.2026 kör testinde fazladan eli 2.5-flash ve
# 3-flash-preview buldu, 3.5-flash-lite kaçırdı: izlemede lite model kullanılmaz.
REVIEW_MODELS = ("gemini-2.5-flash", "gemini-3-flash-preview")
# İzleme yüksek önemde kusur bulursa yeni seed ile en fazla bu kadar yeniden deneme; en iyi aday tutulur
REVIEW_RETRIES = 2

MIN_SECONDS, MAX_SECONDS = 4, 15
MAX_TOTAL_SECONDS = 60      # Çok çekimli uzun video üst sınırı (4 blok × 15 sn)
MIN_SHOT_SECONDS, MAX_SHOT_SECONDS = 2, 15
MAX_BLOCKS = 4
MAX_REF_IMAGES = 9          # H3 Ref2VA en fazla 9 referans görsel alır

AUDIO_MODES = {
    "speech": "Türkçe konuşmalı sahne (doğal ses)",
    "music": "Müzikli, konuşmasız kurgu (dış müzik)",
}
DEFAULT_AUDIO_MODE = "speech"


def frames_for(seconds):
    """Resmi şablondaki formül: 24 fps, H3'ün 17k+5 kare ızgarasına yukarı yuvarlanır."""
    n = max(5, round(float(seconds) * 24))
    return n + (5 - n % 17) % 17
