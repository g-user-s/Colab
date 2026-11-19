# Colab: H3 başsız üretim

Kişisel ajan Muse'un, [H3 Video Stüdyosu](https://github.com/orha9n/h3-video-studyosu)'nu Google Colab API/CLI üzerinden tarayıcısız çalıştırması için rehber ve betikler.

- **[masaustu/BENIOKU.md](masaustu/BENIOKU.md)**: **H3 Stüdyo** — Linux masaüstü uygulaması (PySide6). Kurulum: `bash masaustu/kur.sh`.
- **[MUSE_REHBERI.md](MUSE_REHBERI.md)**: adım adım rehber. Buradan başla.
- **[GOREV_UZUN_VIDEO_URETIM.md](GOREV_UZUN_VIDEO_URETIM.md)**: ilk gerçek uzun video (45 sn, ref, yeniden üretim açık).
- **[GOREV_FATIH_2.md](GOREV_FATIH_2.md)**: Fatih'in girişi — elle yazılmış kart ve prompt'lar (`muse_gorevleri/20261119_fatih2/`), 60 sn, ters ışık.
- **[GOREV_FATIH.md](GOREV_FATIH.md)**: tarihî uzun video — Fatih'in Topkapı'dan girişi (ilham görselleriyle).
- **[GOREV_UZUN_VIDEO_2.md](GOREV_UZUN_VIDEO_2.md)**: uzun video 2 — aydınlık mutfak, köprü açık, kadraj sürekliliği, eşik orta.
- **[GOREV_KOPRU_DENEYI.md](GOREV_KOPRU_DENEYI.md)**: köprü deneyi (önceki bloğun son karesi + Gemini prompt'u) — geçişler daha akıcı olur mu?
- **[DENEY_SONUCLARI.md](DENEY_SONUCLARI.md)**: uzun video deneyinin sonucu (görsel referans açık ara daha iyi).
- **[muse_testleri/MUSE_TEST_GOREVLERI.md](muse_testleri/MUSE_TEST_GOREVLERI.md)**: Muse'un ortamını ve araçları ölçen test görevleri (önce bunlar).
- **[muse_testleri/MUSE_TEST_TUR2.md](muse_testleri/MUSE_TEST_TUR2.md)**: 2. tur (anahtar gerektiren testler, düzeltmelerin doğrulanması).
- **[muse_testleri/MUSE_TEST_TUR3.md](muse_testleri/MUSE_TEST_TUR3.md)**: 3. tur (video izleme karşılaştırması, aynı runtime'da yeniden üretim, köprü).
- **[GOREV_UZUN_VIDEO_DENEYI.md](GOREV_UZUN_VIDEO_DENEYI.md)**: Muse'un yapacağı uzun video deneyi (metin çapası vs. görsel referans).
- `muse/`: betikler (`senaryo.py`, `uzun_senaryo.py`, `h3_uret.py`, `runtime_runner.py`, `yama_411.py`).
- `h3/`: H3 Video Stüdyosu, [orha9n/h3-video-studyosu](https://github.com/orha9n/h3-video-studyosu)'dan `git subtree` ile alındı (geçmişiyle). Uzun video geliştirmesi burada: `h3app/hikaye.py` (hikâye kartı, referans görseller, blok planı), `h3app/uzun.py` (blok üretimi, izleme, birleştirme), `review.continuity_review` (süreklilik puanı).
- `tests/`: sahte `colab` ve sahte modla uçtan uca testler.

Asıl depodaki yeni değişiklikleri almak:
```bash
git subtree pull --prefix=h3 https://github.com/orha9n/h3-video-studyosu main
```
Buradaki değişiklikleri asıl depoya göndermek (yazma izni olan biri): `git subtree push --prefix=h3 <asıl depo> <dal>` ya da `git subtree split --prefix=h3` ile ayrı bir dal çıkarıp PR açmak.

## Testler

```bash
pip install -r h3/requirements-dev.txt   # ffmpeg/ffprobe da gerekli
(cd h3 && python -m pytest -q)           # H3 + uzun video modülleri
python -m pytest -q tests                # Muse betikleri (sahte colab ile uçtan uca)
```
`test_yama_411_idempotent` için `COLAB_CLI_CLIENT=<google-colab-cli 0.8.0 içindeki colab_cli/client.py>` verilmelidir; verilmezse atlanır.
