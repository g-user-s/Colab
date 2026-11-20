"""ComfyUI API grafikleri: resmi `video_pika_h3_flex_t2v` ve `video_minimax_h3_t2v`
şablonlarının birebir karşılığı (yerel ComfyUI'ın /prompt doğrulamasından geçti)."""

import os

from . import config


def _name(role):
    return os.path.basename(config.MODELS[role][0])


def build(method, prompt, seed, width, height, frames, text_encoder="te_nvfp4", prefix="h3app/video", ref_images=(),
          first_frame=None, last_frame=None):
    """ref_images boşsa metinden video (T2VA); doluysa ComfyUI/input altındaki görsellerle referanslı video
    (Ref2VA, resmi `video_pika_h3_flex_ref2va` / `video_minimax_h3_r2v` şablonları).
    first_frame / last_frame (ComfyUI/input altındaki dosya adları): anahtar kareli video (FL2VA / I2VA / L2VA);
    aynı FL2VA modeli ve LoRA'ları, `MiniMaxH3ImageToVideo` düğümünün isteğe bağlı girişleri."""
    if method not in config.METHODS:
        raise ValueError(f"Bilinmeyen yöntem: {method}")
    ref = bool(ref_images)
    g = {
        "unet": {"class_type": "UNETLoader", "inputs": {"unet_name": _name("unet_ref" if ref else "unet"), "weight_dtype": "default"}},
        "clip": {"class_type": "CLIPLoader", "inputs": {"clip_name": _name(text_encoder), "type": "minimax", "device": "default"}},
        "vae_v": {"class_type": "VAELoader", "inputs": {"vae_name": _name("vae_video")}},
        "vae_a": {"class_type": "VAELoader", "inputs": {"vae_name": _name("vae_audio")}},
        "cond": {"class_type": "MiniMaxH3ImageToVideo", "inputs": {"clip": ["clip", 0], "vae": ["vae_v", 0], "prompt": prompt,
                                                                    "width": width, "height": height, "length": frames}},
        "noise": {"class_type": "RandomNoise", "inputs": {"noise_seed": int(seed)}},
        "decode_v": {"class_type": "VAEDecode", "inputs": {"samples": ["sample", 0], "vae": ["vae_v", 0]}},
        "decode_a": {"class_type": "VAEDecodeAudio", "inputs": {"samples": ["sample", 0], "vae": ["vae_a", 0]}},
        "video": {"class_type": "CreateVideo", "inputs": {"images": ["decode_v", 0], "audio": ["decode_a", 0], "fps": 24}},
        "save": {"class_type": "SaveVideo", "inputs": {"video": ["video", 0], "filename_prefix": prefix,
                                                        "format": "mp4", "format.codec": "h264", "format.codec.encoding": "auto"}},
    }
    if ref and (first_frame or last_frame):
        raise ValueError("Referans görseller ile anahtar kareler birlikte kullanılamaz.")
    for key, name in (("first_frame", first_frame), ("last_frame", last_frame)):
        if name:
            g[f"kf_{key}"] = {"class_type": "LoadImage", "inputs": {"image": name}}
            g["cond"]["inputs"][key] = [f"kf_{key}", 0]
    if ref:
        if len(ref_images) > config.MAX_REF_IMAGES:
            raise ValueError(f"En fazla {config.MAX_REF_IMAGES} referans görsel kullanılabilir.")
        cond = {"clip": ["clip", 0], "vae": ["vae_v", 0], "audio_vae": ["vae_a", 0], "prompt": prompt,
                "width": width, "height": height, "length": frames, "ref_image_size": "match"}
        for i, name in enumerate(ref_images):
            g[f"img{i}"] = {"class_type": "LoadImage", "inputs": {"image": name}}
            cond[f"ref_images.ref_image_{i}"] = [f"img{i}", 0]
        g["cond"] = {"class_type": "MiniMaxH3ReferenceToVideo", "inputs": cond}
    if method == "pika":
        g["lora"] = {"class_type": "LoraLoaderModelOnly", "inputs": {"model": ["unet", 0],
                     "lora_name": _name("pika_lora_ref" if ref else "pika_lora"), "strength_model": 1.0}}
        g["sampler"] = {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "lcm"}}
        g["sigmas"] = {"class_type": "ManualSigmas", "inputs": {"sigmas": config.PIKA_SIGMAS}}
        model = ["lora", 0]
    elif method == "turbo":
        g["lora"] = {"class_type": "LoraLoaderModelOnly", "inputs": {"model": ["unet", 0],
                     "lora_name": _name("turbo_lora_ref" if ref else "turbo_lora"), "strength_model": 1.0}}
        g["sampler"] = {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "res_multistep"}}
        steps = config.TURBO_REF_STEPS if ref else config.TURBO_STEPS
        g["sigmas"] = {"class_type": "BasicScheduler", "inputs": {"model": ["lora", 0], "scheduler": "simple",
                                                                  "steps": steps, "denoise": 1.0}}
        model = ["lora", 0]
    else:
        g["sampler"] = {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "res_multistep"}}
        g["sigmas"] = {"class_type": "BasicScheduler", "inputs": {"model": ["unet", 0], "scheduler": "simple",
                                                                  "steps": config.H3_STEPS, "denoise": 1.0}}
        model = ["unet", 0]
    g["guider"] = {"class_type": "BasicGuider", "inputs": {"model": model, "conditioning": ["cond", 0]}}
    g["sample"] = {"class_type": "SamplerCustomAdvanced", "inputs": {"noise": ["noise", 0], "guider": ["guider", 0],
                                                                      "sampler": ["sampler", 0], "sigmas": ["sigmas", 0],
                                                                      "latent_image": ["cond", 1]}}
    return g
