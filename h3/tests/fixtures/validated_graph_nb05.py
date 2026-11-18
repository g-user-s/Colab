"""Yerel ComfyUI'ın /prompt doğrulamasından geçmiş T2VA grafiği (ilk çalışan notebook'tan, değiştirilmeden).
Kullanmadan önce PROMPT, WIDTH, HEIGHT, SECONDS, H3_STEPS tanımlanmalıdır."""


def graph(method, seed, prefix):
    n = max(5, round(SECONDS * 24))
    n += (5 - n % 17) % 17                                # resmi şablondaki gibi 17k+5 ızgarasına yukarı yuvarla
    g = {
        "unet": {"class_type": "UNETLoader", "inputs": {"unet_name": "minimax_h3_fl2va_pruned_int8_convrot.safetensors", "weight_dtype": "default"}},
        "clip": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors", "type": "minimax", "device": "default"}},
        "vae_v": {"class_type": "VAELoader", "inputs": {"vae_name": "minimax_h3_video_vae_int8_convrot.safetensors"}},
        "vae_a": {"class_type": "VAELoader", "inputs": {"vae_name": "minimax_h3_audio_vae_fp32.safetensors"}},
        "cond": {"class_type": "MiniMaxH3ImageToVideo", "inputs": {"clip": ["clip", 0], "vae": ["vae_v", 0], "prompt": PROMPT,
                                                                    "width": WIDTH, "height": HEIGHT, "length": n}},
        "noise": {"class_type": "RandomNoise", "inputs": {"noise_seed": seed}},
        "decode_v": {"class_type": "VAEDecode", "inputs": {"samples": ["sample", 0], "vae": ["vae_v", 0]}},
        "decode_a": {"class_type": "VAEDecodeAudio", "inputs": {"samples": ["sample", 0], "vae": ["vae_a", 0]}},
        "video": {"class_type": "CreateVideo", "inputs": {"images": ["decode_v", 0], "audio": ["decode_a", 0], "fps": 24}},
        "save": {"class_type": "SaveVideo", "inputs": {"video": ["video", 0], "filename_prefix": prefix,
                                                        "format": "mp4", "format.codec": "h264", "format.codec.encoding": "auto"}},
    }
    if method == "pika":
        g["lora"] = {"class_type": "LoraLoaderModelOnly", "inputs": {"model": ["unet", 0], "lora_name": "pika_h3_flex_fl2va_v1_bf16.safetensors", "strength_model": 1.0}}
        g["sampler"] = {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "lcm"}}
        g["sigmas"] = {"class_type": "ManualSigmas", "inputs": {"sigmas": "1.0, 0.972973, 0.923077, 0.8, 0.571429, 0.333333, 0.0"}}
        model = ["lora", 0]
    else:
        g["sampler"] = {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "res_multistep"}}
        g["sigmas"] = {"class_type": "BasicScheduler", "inputs": {"model": ["unet", 0], "scheduler": "simple", "steps": H3_STEPS, "denoise": 1.0}}
        model = ["unet", 0]
    g["guider"] = {"class_type": "BasicGuider", "inputs": {"model": model, "conditioning": ["cond", 0]}}
    g["sample"] = {"class_type": "SamplerCustomAdvanced", "inputs": {"noise": ["noise", 0], "guider": ["guider", 0], "sampler": ["sampler", 0],
                                                                      "sigmas": ["sigmas", 0], "latent_image": ["cond", 1]}}
    return g, n
