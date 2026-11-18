# Colab: H3 başsız üretim

Kişisel ajan Muse'un, [H3 Video Stüdyosu](https://github.com/orha9n/h3-video-studyosu)'nu Google Colab API/CLI üzerinden tarayıcısız çalıştırması için rehber ve betikler.

- **[MUSE_REHBERI.md](MUSE_REHBERI.md)**: adım adım rehber. Buradan başla.
- **[GOREV_UZUN_VIDEO_DENEYI.md](GOREV_UZUN_VIDEO_DENEYI.md)**: Muse'un yapacağı uzun video deneyi (metin çapası vs. görsel referans).
- `muse/`: betikler (`senaryo.py`, `uzun_senaryo.py`, `h3_uret.py`, `runtime_runner.py`, `uzun_runtime.py`, `yama_411.py`).

- `tests/`: sahte `colab` ve sahte modla uçtan uca testler.

Uzun video geliştirmesi şimdilik H3 deposunu değiştirmeden, onun fonksiyonlarını (`plan_shots`, `block_request`, `rewrite`, `graphs.build`, `review`, `assemble`) kullanan bir katman olarak burada duruyor. H3 deposuna yazma izni gelince `h3app`'e taşınacak.

## Testler

```bash
pip install -r <h3-video-studyosu>/requirements-dev.txt   # ffmpeg/ffprobe da gerekli
H3_DIZIN=<h3-video-studyosu klonu, commit 70e0bc4> python -m pytest -q tests
```
`test_yama_411_idempotent` için `COLAB_CLI_CLIENT=<google-colab-cli 0.8.0 içindeki colab_cli/client.py>` verilmelidir; verilmezse atlanır.
