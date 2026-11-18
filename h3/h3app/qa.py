"""Üretilen videonun GPU'suz kontrolü (QA v2): kesmeler (prompt'taki zamanlarla karşılaştırılır), donmuş aralıklar,
sonda kayma/bulanıklaşma tespiti (`tail_drift`), stil tutarlılığı uyarısı (`style_check`), ses kanalı ve konuşma bandı
analizi (`audio_check`), temas sayfası ve %100 kırpıntılar. Ölçü fikirleri scenario-alter skill'inin `alter_check.py`'sinden
(MIT) uyarlandı; orada kaynak video ile karşılaştırılıyordu, burada kaynak yok, beklenen kesmeler prompt'tan okunur."""

import os
import re
import subprocess

import cv2
import numpy as np

from . import config

SMALL = (160, 90)
CUT_HIST = 0.35       # ardışık iki karenin HS histogram uzaklığı (Bhattacharyya) bunu aşarsa kesme
CUT_JUMP = 6.0        # ya da gri fark, videonun ortanca farkının bu katını aşarsa (ışığı aynı kalan kesmeler)
CUT_MIN_DIFF = 12.0   # ... ve en az bu kadar (0-255) olursa
MIN_GAP = 6           # iki kesme arasında en az bu kadar kare
FROZEN_DIFF = 0.4     # ortalama gri fark bunun altındaysa kare "kıpırdamıyor"
FROZEN_MIN = 0.5      # en az bu kadar saniye kıpırdamazsa donmuş aralık
TOLERANCE = 0.35      # prompt'taki kesme zamanıyla eşleşme payı (sn)

TAIL_FRAMES = 12              # sonda kayma/bulanıklaşma kontrol penceresi (24 fps'te ~0,5 sn)
TAIL_MIN_TRIM = 6             # sonda bozulma varsa kırpılacak en az kare sayısı
TAIL_MAX_TRIM = 10            # sonda bozulma varsa kırpılacak en fazla kare sayısı
TAIL_SHARP_DROP = 0.60        # son karelerin keskinliği gövdenin bu oranının altına düşerse bulanıklaşma
TAIL_DRIFT_MULT = 2.6         # son karelerin ortalama hareketi gövde ortancasının bu katını aşarsa kayma
TAIL_DRIFT_MIN_DIFF = 6.5     # ... ve ortalama gri fark en az bu kadarsa

STYLE_MICRO_MAX = 0.55        # çizgi/boyalı stillerde yüksek frekanslı mikro-doku üst eşiği
STYLE_FLAT_MIN = 0.12         # çizgi/boyalı stillerde düz/boyalı bölge alt eşiği
SPEECH_BAND_LOW = 300.0       # konuşma bandı alt frekansı (Hz)
SPEECH_BAND_HIGH = 3400.0     # konuşma bandı üst frekansı (Hz)
SPEECH_RATIO_MIN = 0.35       # Türkçe konuşma beklenen videoda konuşma bandı enerjisi alt eşiği

# Kesme yalnızca "[Shot N] At 00:SS.000" biçimidir; "At about 00:05" gibi çekim içi olaylar kesme değildir
AT_RE = re.compile(r"\[Shot\s*\d+\]\s*At (\d{1,2}):(\d{2}(?:\.\d+)?)")
SPEECH_PROMPT_RE = re.compile(r"<d>|\[Turkish\]|\b(?:speaking|speaks|says|dialogue|bargaining)\b", re.I)


def prompt_cuts(prompt):
    """Prompt'taki "[Shot N] At 00:SS.000" kesme zamanları (0'dan büyük olanlar, sıralı)."""
    times = {round(int(m) * 60 + float(s), 3) for m, s in AT_RE.findall(prompt or "")}
    return sorted(t for t in times if t > 0)


def _scan(path):
    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    size = (int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))
    hists, grays = [], []
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        small = cv2.resize(frame, SMALL, interpolation=cv2.INTER_AREA)
        h = cv2.calcHist([cv2.cvtColor(small, cv2.COLOR_BGR2HSV)], [0, 1], None, [32, 32], [0, 180, 0, 256])
        hists.append(cv2.normalize(h, h))
        grays.append(cv2.cvtColor(small, cv2.COLOR_BGR2GRAY).astype(np.float32))
    cap.release()
    if not grays:
        raise ValueError(f"Video okunamadı: {path}")
    return fps, size, hists, grays


def find_cuts(hists, grays):
    """Kesme olan karelerin indeksleri (ilk kare hariç)."""
    hist_d = [cv2.compareHist(a, b, cv2.HISTCMP_BHATTACHARYYA) for a, b in zip(hists, hists[1:])]
    gray_d = [float(np.mean(np.abs(a - b))) for a, b in zip(grays, grays[1:])]
    base = max(float(np.median(gray_d)) if gray_d else 0.0, 1.0)
    cuts = []
    for i, (h, g) in enumerate(zip(hist_d, gray_d), start=1):
        if (h > CUT_HIST or (g > CUT_JUMP * base and g > CUT_MIN_DIFF)) and i - (cuts[-1] if cuts else 0) >= MIN_GAP:
            cuts.append(i)
    return cuts


def frozen_spans(grays, fps):
    """[(başlangıç sn, bitiş sn)]: görüntünün hiç kıpırdamadığı aralıklar."""
    spans, start = [], None
    for i in range(1, len(grays) + 1):
        still = i < len(grays) and float(np.mean(np.abs(grays[i] - grays[i - 1]))) < FROZEN_DIFF
        if still and start is None:
            start = i - 1
        elif not still and start is not None:
            if (i - start) / fps >= FROZEN_MIN:
                spans.append((round(start / fps, 2), round((i - 1) / fps, 2)))
            start = None
    return spans


def match(found, expected, tol=TOLERANCE):
    """(eşleşen [(beklenen, bulunan)], bulunamayan beklenenler, beklenmeyen bulunanlar)."""
    left, pairs, missing = list(found), [], []
    for e in expected:
        near = min(left, key=lambda f: abs(f - e), default=None)
        if near is not None and abs(near - e) <= tol:
            pairs.append((e, near))
            left.remove(near)
        else:
            missing.append(e)
    return pairs, missing, left


def _frames_at(path, indices):
    cap = cv2.VideoCapture(path)
    out = []
    for i in indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(i))
        ok, frame = cap.read()
        if ok:
            out.append((i, frame))
    cap.release()
    return out


def contact_sheet(path, fps, n_frames, dest, moments=8, width=480):
    """Videonun eşit aralıklı anlarından, zaman etiketli 2 satırlık temas sayfası."""
    idx = [int(n_frames * (k + 0.5) / moments) for k in range(moments)]
    tiles = []
    for i, frame in _frames_at(path, idx):
        tile = cv2.resize(frame, (width, int(width * frame.shape[0] / frame.shape[1])), interpolation=cv2.INTER_AREA)
        cv2.putText(tile, f"{i / fps:.1f} sn", (8, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 4)
        cv2.putText(tile, f"{i / fps:.1f} sn", (8, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        tiles.append(tile)
    while len(tiles) % 4:
        tiles.append(np.zeros_like(tiles[0]))
    cv2.imwrite(dest, np.vstack([np.hstack(tiles[k:k + 4]) for k in range(0, len(tiles), 4)]),
                [cv2.IMWRITE_JPEG_QUALITY, 88])
    return dest


def detail_crops(path, n_frames, dest, moments=4, box=320):
    """Her an için en çok hareket eden ayrıntılı bölgenin %100 kırpıntısı (genellikle eller ve yüz): parmak,
    yazı, logo ve yüz kontrolü için. Hareket, 3 kare sonrasıyla farktan; ayrıntı, kenar yoğunluğundan."""
    idx = [min(int(n_frames * (k + 0.5) / moments), max(n_frames - 4, 0)) for k in range(moments)]
    shots = dict(_frames_at(path, idx + [i + 3 for i in idx]))
    crops = []
    for i in idx:
        frame, later = shots.get(i), shots.get(i + 3, shots.get(i))
        if frame is None:
            continue
        h, w = frame.shape[:2]
        b = min(box, h, w)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float32)
        moving = cv2.GaussianBlur(np.abs(gray - cv2.cvtColor(later, cv2.COLOR_BGR2GRAY).astype(np.float32)), (0, 0), 8)
        energy = (moving + 1.0) * np.abs(cv2.Laplacian(gray, cv2.CV_32F))
        summed = cv2.boxFilter(energy, -1, (b, b), normalize=False)[b // 2:h - b // 2 + 1, b // 2:w - b // 2 + 1]
        y, x = np.unravel_index(int(np.argmax(summed)), summed.shape)
        crops.append(frame[y:y + b, x:x + b])
    cv2.imwrite(dest, np.hstack(crops), [cv2.IMWRITE_JPEG_QUALITY, 92])
    return dest


LUFS_RE = re.compile(r"I:\s*(-?\d+(?:\.\d+)?)\s*LUFS")


def measure_lufs(path):
    """Videodaki ses kanalının EBU R128 entegre ses yüksekliği (LUFS); ses kanalı yoksa None döner."""
    try:
        p = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af", "ebur128", "-f", "null", "-"],
                           capture_output=True, text=True, timeout=60)
    except Exception:
        return None
    matches = LUFS_RE.findall(p.stderr or "")
    return round(float(matches[-1]), 1) if matches else None


def _apply_gain(path, gain_db, tp):
    """Sese doğrusal kazanç uygular (görüntü kopyalanır); yükseltiyorsa tepeleri `tp` dBTP'de sınırlar."""
    af = f"volume={gain_db:.2f}dB"
    if gain_db > 0:
        af += f",alimiter=limit={10 ** (tp / 20):.4f}:level=disabled"
    tmp = f"{path}.loudnorm.mp4"
    try:
        subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", path, "-c:v", "copy",
                        "-af", af, "-ar", "48000", "-c:a", "aac", "-b:a", "192k", tmp], check=True, timeout=120)
        os.replace(tmp, path)
        return True
    except Exception:
        if os.path.exists(tmp):
            os.remove(tmp)
        return False


def normalize_audio(path, target_lufs=config.TARGET_LUFS, tp=-1.5, lra=11.0, tolerance=0.5):
    """Görüntü akışına dokunmadan (-c:v copy) sesi hedef entegre ses yüksekliğine (-16 LUFS) getirir.
    Ölçülen değere göre doğrusal kazanç uygulanır ve sonuç yeniden ölçülür; gerekirse bir kez daha ince ayar yapılır.
    (Tek geçişli dinamik `loudnorm` kısa, araları sessiz H3 konuşmalarında hedefi aşıyordu: -16,7 → -13,7.)
    Ses kanalı varsa ve sessiz değilse (önceki_lufs, yeni_lufs) döner; yoksa None. `lra` geriye uyumluluk için."""
    before = measure_lufs(path)
    if before is None or before <= -65.0:
        return None
    now = before
    for _ in range(2):
        gain = float(target_lufs) - now
        if abs(gain) <= tolerance or not _apply_gain(path, gain, tp):
            break
        measured = measure_lufs(path)
        if measured is None:
            break
        now = measured
    return (before, now)


def _ensure_grays(source):
    """`source` bir dosya yoluysa `_scan` ile gri kareleri ve fps'i döner; gri kare listesiyse doğrudan kullanır."""
    if isinstance(source, str):
        fps, _, _, grays = _scan(source)
        return grays, fps
    return list(source or []), 24.0


def tail_drift(source, fps=24.0, expected_cuts=None):
    """Videonun son 12 karesindeki (~0,5 sn) Laplacian keskinlik düşüşünü ve beklenmeyen global kaymayı ölçer.

    Bozulma varsa `assemble.py` içinde son 6–10 karenin otomatik kırpılabilmesi için `kirp_kare` (6..10) döner.
    Dönüş: `{bozuk, keskinlik_orani, kayma_orani, kirp_kare, neden}`.
    """
    grays, scanned_fps = _ensure_grays(source)
    fps = float(fps or scanned_fps or 24.0)
    n = len(grays)
    tail_len = min(TAIL_FRAMES, max(TAIL_MIN_TRIM, n // 4)) if n >= 20 else 0
    if tail_len < TAIL_MIN_TRIM or n < tail_len + 8:
        return {"bozuk": False, "keskinlik_orani": 1.0, "kayma_orani": 1.0, "kirp_kare": 0, "neden": None}

    # 1. Laplacian keskinlik düşüşü
    sharp = [float(np.mean(np.abs(cv2.Laplacian(g, cv2.CV_32F)))) for g in grays]
    body_start = max(0, n - tail_len - 36)
    body_sharp = sharp[body_start:n - tail_len]
    base_sharp = float(np.median(body_sharp)) if body_sharp else 0.0
    tail_sharp = sharp[n - tail_len:]
    if base_sharp > 1.0:
        sharp_ratio = round(float(np.mean(tail_sharp[-TAIL_MIN_TRIM:])) / base_sharp, 3)
        blur_bad = sharp_ratio < TAIL_SHARP_DROP
    else:
        sharp_ratio = 1.0
        blur_bad = False

    # 2. Beklenmeyen global kayma / sıçrama (prompt'ta son 0,5 sn içinde kasıtlı kesme yoksa)
    tail_start_sec = (n - tail_len) / fps
    has_expected_tail_cut = any(c >= tail_start_sec - TOLERANCE for c in (expected_cuts or []))
    diffs = [float(np.mean(np.abs(a - b))) for a, b in zip(grays, grays[1:])]
    body_diffs = [d for d in diffs[max(0, len(diffs) - tail_len - 36):len(diffs) - tail_len] if d < 25.0]
    base_diff = max(float(np.median(body_diffs)) if body_diffs else 0.0, 0.5)
    tail_diffs = diffs[len(diffs) - tail_len:]
    tail_mean = float(np.mean(tail_diffs[-TAIL_MIN_TRIM:])) if tail_diffs else 0.0
    tail_max = float(np.max(tail_diffs)) if tail_diffs else 0.0

    if not has_expected_tail_cut and tail_mean > 0:
        drift_ratio = round(tail_mean / base_diff, 3)
        drift_bad = tail_mean >= TAIL_DRIFT_MIN_DIFF and tail_mean >= TAIL_DRIFT_MULT * base_diff
    else:
        drift_ratio = round(tail_mean / base_diff, 3) if base_diff > 0 else 1.0
        drift_bad = False

    if not (blur_bad or drift_bad):
        return {
            "bozuk": False,
            "keskinlik_orani": sharp_ratio,
            "kayma_orani": drift_ratio,
            "kirp_kare": 0,
            "neden": None,
        }

    # Bozulmanın başladığı ilk kareyi bul ve kırpılacak kare sayısını [6, 10] aralığına sabitle
    bad_idx = tail_len - TAIL_MIN_TRIM
    for idx in range(tail_len):
        is_blur = blur_bad and tail_sharp[idx] < base_sharp * (TAIL_SHARP_DROP + 0.08)
        is_drift = drift_bad and idx < len(tail_diffs) and tail_diffs[idx] >= max(TAIL_DRIFT_MIN_DIFF * 0.85, base_diff * 2.2)
        if is_blur or is_drift:
            bad_idx = idx
            break
    trim = max(TAIL_MIN_TRIM, min(TAIL_MAX_TRIM, tail_len - bad_idx))
    if blur_bad and drift_bad:
        reason = "bulanıklaşma ve kayma"
    elif blur_bad:
        reason = "bulanıklaşma"
    else:
        reason = "kayma"
    return {
        "bozuk": True,
        "keskinlik_orani": sharp_ratio,
        "kayma_orani": drift_ratio,
        "kirp_kare": int(trim),
        "neden": reason,
    }


def _infer_style(style, prompt=""):
    """Stil açıkça verilmediyse prompt içindeki stil anahtar kelimelerinden tahmin eder."""
    if style and style in config.STYLES:
        return style
    low = (prompt or "").lower()
    for k, meta in config.STYLES.items():
        if k != config.DEFAULT_STYLE and any(kw in low for kw in meta.get("keywords", ())):
            return k
    return config.DEFAULT_STYLE


def _style_metrics(source):
    """Örneklenen karelerde düz/boyalı bölge oranını (`duz_oran`) ve yüksek frekanslı mikro-doku oranını (`mikro_doku`) ölçer."""
    grays, _ = _ensure_grays(source)
    if not grays:
        return 0.0, 0.0
    step = max(1, len(grays) // 8)
    sampled = grays[::step][:8]
    flats, micros = [], []
    for g in sampled:
        gx = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3)
        grad = np.hypot(gx, gy)
        blur = cv2.GaussianBlur(g, (5, 5), 1.2)
        micro = np.abs(g - blur)
        flats.append(float(np.mean(grad < 12.0)))
        micros.append(float(np.mean(micro > 3.5)))
    return round(float(np.mean(flats)), 3), round(float(np.mean(micros)), 3)


def style_check(source, style=None, prompt="", ref_source=None):
    """Anime, Pixar veya Suluboya seçildiğinde arka planın/dokunun fotoğrafa kayıp kaymadığını kontrol eder.

    `ref_source` (örn. Pika taslak videosu veya onun `style_check` sözlüğü) verilirse taslaktan H3 finaline
    geçerken oluşan stil kaymasını da denetler.
    Dönüş: `{stil, duz_oran, mikro_doku, kayma, taslaktan_kayma, uyari}`.
    """
    resolved = _infer_style(style, prompt)
    flat_ratio, micro_ratio = _style_metrics(source)
    if resolved == config.DEFAULT_STYLE:
        return {
            "stil": resolved,
            "duz_oran": flat_ratio,
            "mikro_doku": micro_ratio,
            "kayma": False,
            "taslaktan_kayma": False,
            "uyari": None,
        }

    abs_drift = (micro_ratio > STYLE_MICRO_MAX and flat_ratio < STYLE_FLAT_MIN) or (
        micro_ratio > 0.45 and flat_ratio > 0 and (micro_ratio / max(flat_ratio, 0.01)) > 5.0
    )
    rel_drift = False
    if ref_source is not None:
        if isinstance(ref_source, dict) and "duz_oran" in ref_source and "mikro_doku" in ref_source:
            ref_flat, ref_micro = float(ref_source["duz_oran"]), float(ref_source["mikro_doku"])
        else:
            ref_flat, ref_micro = _style_metrics(ref_source)
        if (micro_ratio - ref_micro >= 0.06 and flat_ratio <= ref_flat * 0.85) or (flat_ratio - ref_flat <= -0.08):
            rel_drift = True

    kayma = bool(abs_drift or rel_drift)
    label = config.STYLES.get(resolved, {}).get("label", resolved)
    uyari = None
    if abs_drift and rel_drift:
        uyari = f"{label} stilinde fotoğrafa ve taslağa göre mikro-doku kayması (düz: {flat_ratio:.2f}, doku: {micro_ratio:.2f})"
    elif abs_drift:
        uyari = f"{label} stilinde fotoğrafa kayma / aşırı mikro-doku (düz: {flat_ratio:.2f}, doku: {micro_ratio:.2f})"
    elif rel_drift:
        uyari = f"taslaktan finale geçerken {label} stilinde kayma (düz: {flat_ratio:.2f}, doku: {micro_ratio:.2f})"
    return {
        "stil": resolved,
        "duz_oran": flat_ratio,
        "mikro_doku": micro_ratio,
        "kayma": kayma,
        "taslaktan_kayma": rel_drift,
        "uyari": uyari,
    }


def audio_check(path, prompt="", lufs=None):
    """Ses kanalının dolu olup olmadığını, LUFS değerini ve konuşma bandı (300–3400 Hz) enerjisini ölçer.

    Dönüş: `{var, dolu, lufs, rms, konusma_orani, konusma_bekleniyor, uyari}`.
    """
    low_prompt = (prompt or "").lower()
    konusma_bekleniyor = bool(SPEECH_PROMPT_RE.search(prompt or "")) and "no speech" not in low_prompt
    if lufs is None:
        lufs = measure_lufs(path)
    try:
        p = subprocess.run(
            ["ffmpeg", "-v", "error", "-i", path, "-vn", "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
            capture_output=True, timeout=30,
        )
        pcm = np.frombuffer(p.stdout or b"", dtype=np.float32)
    except Exception:
        pcm = np.array([], dtype=np.float32)

    if pcm.size == 0:
        return {
            "var": False,
            "dolu": False,
            "lufs": lufs,
            "rms": 0.0,
            "konusma_orani": 0.0,
            "konusma_bekleniyor": konusma_bekleniyor,
            "uyari": "ses kanalı yok veya boş" if konusma_bekleniyor else None,
        }

    rms = round(float(np.sqrt(np.mean(pcm ** 2))), 4)
    dolu = bool(rms > 1e-4 and (lufs is None or lufs > -55.0))
    if dolu and pcm.size >= 64:
        spec = np.abs(np.fft.rfft(pcm)) ** 2
        freqs = np.fft.rfftfreq(pcm.size, 1.0 / 16000.0)
        tot = float(np.sum(spec[(freqs >= 50.0) & (freqs <= 8000.0)]))
        sp = float(np.sum(spec[(freqs >= SPEECH_BAND_LOW) & (freqs <= SPEECH_BAND_HIGH)]))
        konusma_orani = round(sp / tot, 2) if tot > 1e-12 else 0.0
    else:
        konusma_orani = 0.0

    uyari = None
    if not dolu:
        uyari = "ses kanalı sessiz/boş"
    elif konusma_bekleniyor and konusma_orani < SPEECH_RATIO_MIN:
        uyari = f"konuşma bandı enerjisi düşük ({konusma_orani:.2f})"

    return {
        "var": True,
        "dolu": dolu,
        "lufs": lufs,
        "rms": rms,
        "konusma_orani": konusma_orani,
        "konusma_bekleniyor": konusma_bekleniyor,
        "uyari": uyari,
    }


def check(path, prompt="", sheet=None, crops=None, style=None, ref_video=None):
    """Videoyu ölçer (QA v2). `{saniye, kare, fps, boyut, kesmeler, beklenen, eslesen, bulunamayan, beklenmeyen, donmus,
    lufs, ses, son_kayma, stil_kontrol, temas, kirpinti}` döner; özet için `summary()`."""
    fps, size, hists, grays = _scan(path)
    n = len(grays)
    cuts = [round(i / fps, 2) for i in find_cuts(hists, grays)]
    expected = prompt_cuts(prompt)
    pairs, missing, extra = match(cuts, expected)
    lufs = measure_lufs(path)
    ses = audio_check(path, prompt=prompt, lufs=lufs)
    son_kayma = tail_drift(grays, fps=fps, expected_cuts=expected)
    stil_kontrol = style_check(grays, style=style, prompt=prompt, ref_source=ref_video)
    report = {"saniye": round(n / fps, 2), "kare": n, "fps": round(fps, 2), "boyut": list(size),
              "kesmeler": cuts, "beklenen": expected, "eslesen": pairs, "bulunamayan": missing,
              "beklenmeyen": extra, "donmus": frozen_spans(grays, fps),
              "lufs": lufs, "ses": ses, "son_kayma": son_kayma, "stil_kontrol": stil_kontrol,
              "prompt_var": bool((prompt or "").strip())}
    if sheet:
        report["temas"] = contact_sheet(path, fps, n, sheet)
    if crops:
        report["kirpinti"] = detail_crops(path, n, crops)
    return report


def summary(r):
    """Durum kutusu için tek satırlık Türkçe özet."""
    sec = lambda xs: " · ".join(f"{x:.1f}".replace(".", ",") for x in xs) or "yok"
    parts = [f"{r['saniye']:.2f} sn, {r['kare']} kare".replace(".", ","), f"kesmeler: {sec(r['kesmeler'])}"]
    ses = r.get("ses") or {}
    if r.get("lufs") is not None:
        s_txt = f"ses: {r['lufs']:.1f} LUFS".replace(".", ",")
        if ses.get("dolu") and (ses.get("konusma_bekleniyor") or ses.get("konusma_orani", 0) > 0):
            s_txt += f" (konuşma bandı: {ses['konusma_orani']:.2f})".replace(".", ",")
        parts.append(s_txt)
    if ses.get("uyari"):
        parts.append(f"⚠️ ses: {ses['uyari']}".replace(".", ","))
    if r["beklenen"]:
        parts.append(f"prompt'ta: {sec(r['beklenen'])}")
        if r["bulunamayan"]:
            parts.append(f"bulunamayan: {sec(r['bulunamayan'])} (ışık aynıysa ölçülemeyebilir, gözle bakın)")
    if r["beklenmeyen"] and r.get("prompt_var"):
        parts.append(f"⚠️ beklenmeyen kesme/sıçrama: {sec(r['beklenmeyen'])}")
    if r["donmus"]:
        parts.append("⚠️ donmuş: " + ", ".join(f"{a:.1f}–{b:.1f} sn".replace(".", ",") for a, b in r["donmus"]))
    td = r.get("son_kayma") or {}
    if td.get("bozuk"):
        parts.append(f"⚠️ sonda {td.get('neden', 'bozulma')} (son {td.get('kirp_kare', 6)} kare kırpılabilir)")
    sc = r.get("stil_kontrol") or {}
    if sc.get("kayma") and sc.get("uyari"):
        parts.append(f"⚠️ stil kayması: {sc['uyari']}".replace(".", ","))
    return "Kontrol: " + "; ".join(parts)
