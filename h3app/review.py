"""Üretilen videonun Gemini ile otomatik izlenmesi: video sesiyle birlikte bir kontrol listesine göre izlenir ve
zaman damgalı kusur listesi döner (fazladan el/kişi, nesne ışınlanması, bakış açısı sıçraması, kimlik, yazı, stil,
replikler ve dudak uyumu, ilk/son 2 saniye).

16.11.2026 kör testi (ipucu verilmeden, gerçek bir Pika videosu): gemini-2.5-flash 0–2 sn'deki fazladan eli doğru
zamanla buldu, gemini-3-flash-preview de buldu, gemini-3.5-flash-lite "kusursuz" dedi. Bu yüzden izleme kendi
model sırasını kullanır ve lite modeller burada kullanılmaz. Gemini'ye ulaşılamazsa None döner; üretim engellenmez.
"""

import os
import subprocess
import tempfile

from . import config, prompt_writer

CHECKLIST = """You are a strict video QA reviewer for AI-generated video clips. Watch the whole clip frame by frame and
LISTEN to the audio. Compare it with the generation prompt and the reference pictures. Report every defect you can see
or hear, with timestamps. Check at least:
1. Anatomy and physical logic: extra or missing hands/arms/fingers, disembodied body parts, objects floating or
   teleporting between hands, objects changing size, people or objects appearing/disappearing without a cause.
2. Camera logic: unexplained point-of-view shots, sudden jumps or cuts the prompt did not ask for.
3. Identity: does each character match the reference picture / description for the whole clip?
4. Scene and style consistency over time; text or lettering that should not be there.
5. Speech: are the quoted lines spoken, in the right language, by the right character, with lips in sync?
6. The first 2 seconds and the last 2 seconds specifically (models often glitch there).
Severity: "high" = a viewer would clearly notice and the clip should be regenerated; "medium" = noticeable but
usable; "low" = minor. Do not invent defects: report only what you actually see or hear.
Answer ONLY with JSON: {"verdict": "pass" | "fail", "defects": [{"start_s": number, "end_s": number,
"severity": "high" | "medium" | "low", "category": string, "description": string}], "summary": string}"""

SEVERITIES = ("high", "medium", "low")
SEVERITY_TR = {"high": "yüksek", "medium": "orta", "low": "düşük"}
TIMEOUT_MS = 240_000


def _proxy(path, dest_dir):
    """İzleme için küçük kopya (540p, düşük bit hızı): istek hızlı ve satır içi gönderilebilir boyutta kalır."""
    out = os.path.join(dest_dir, "inceleme.mp4")
    try:
        subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", path, "-vf", "scale=-2:540",
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "30", "-c:a", "aac", "-b:a", "96k", out],
                       check=True, timeout=180)
        return out
    except Exception:
        return path


def normalize(raw):
    """Model çıktısını tutarlı bir sözlüğe çevirir; karar, yüksek önemde kusur olup olmamasından türetilir."""
    defects = []
    for d in (raw or {}).get("defects") or []:
        if not isinstance(d, dict):
            continue
        sev = str(d.get("severity", "medium")).lower()
        try:
            start = float(d.get("start_s", 0) or 0)
            end = float(d.get("end_s", start) or start)
        except (TypeError, ValueError):
            start = end = 0.0
        defects.append({"start_s": round(start, 2), "end_s": round(max(start, end), 2),
                        "severity": sev if sev in SEVERITIES else "medium",
                        "category": str(d.get("category") or "").strip(),
                        "description": str(d.get("description") or "").strip()})
    defects.sort(key=lambda d: (SEVERITIES.index(d["severity"]), d["start_s"]))
    return {"verdict": "fail" if any(d["severity"] == "high" for d in defects) else "pass",
            "defects": defects, "summary": str((raw or {}).get("summary") or "").strip()}


def review_video(path, prompt, api_key, images=(), roles=None, models=None, log=None):
    """Videoyu izletir. {'verdict', 'defects', 'summary', 'model'} ya da (hiçbir model yanıt vermezse) None döner."""
    from google.genai import types
    models = [m for m in (models or config.REVIEW_MODELS) if m]
    with tempfile.TemporaryDirectory(prefix="h3app_inceleme_") as tmp:
        data = open(_proxy(path, tmp), "rb").read()
    parts = [types.Part.from_bytes(data=data, mime_type="video/mp4")]
    if images:
        parts += ["Reference pictures:"] + prompt_writer._image_parts(images, roles)
    parts.append("Generation prompt:\n" + (prompt or "").strip())
    cfg = types.GenerateContentConfig(system_instruction=CHECKLIST, temperature=0.1,
                                      response_mime_type="application/json")
    for m in models:
        try:
            client = prompt_writer._client(api_key, TIMEOUT_MS)   # değişkende tutulmalı (bkz. prompt_writer)
            resp = client.models.generate_content(model=m, contents=parts, config=cfg)
            result = normalize(prompt_writer._parse_json(resp.text or ""))
            result["model"] = m
            return result
        except Exception as e:
            if log:
                log(f"   🔍 {m} videoyu izleyemedi ({str(e)[:120]}); sıradaki izleyici deneniyor.")
    return None


def blocking(result):
    """Yeniden üretim gerektiren (yüksek önemde) kusur var mı?"""
    return bool(result) and any(d["severity"] == "high" for d in result.get("defects") or [])


def score(result):
    """Adayları karşılaştırmak için: daha az yüksek, sonra orta, sonra düşük kusur daha iyidir. İzlenemeyen en sona."""
    if not result:
        return (99, 99, 99)
    counts = [sum(1 for d in result["defects"] if d["severity"] == s) for s in SEVERITIES]
    return tuple(counts)


def short(result):
    """Çok kısa özet: 'kusur yok', '1 yüksek, 2 düşük kusur' ya da 'izlenemedi'."""
    if result is None:
        return "izlenemedi"
    parts = [f"{n} {SEVERITY_TR[s]}" for s, n in zip(SEVERITIES, score(result)) if n]
    return (", ".join(parts) + " kusur") if parts else "kusur yok"


def summary(result):
    """Günlük için tek satır Türkçe özet."""
    if result is None:
        return "🔍 Otomatik izleme yapılamadı (Gemini yanıt vermedi); video yine de kaydedildi."
    model = result.get("model", "")
    if not result["defects"]:
        return f"🔍 İzleme ({model}): kusur bulunmadı."
    items = [f"[{d['start_s']:.1f}–{d['end_s']:.1f} sn, {SEVERITY_TR[d['severity']]}] {d['description']}"
             for d in result["defects"][:4]]
    more = f" (+{len(result['defects']) - 4} kusur daha)" if len(result["defects"]) > 4 else ""
    return f"🔍 İzleme ({model}): {len(result['defects'])} kusur — " + " · ".join(items) + more
