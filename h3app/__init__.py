"""H3 Video Stüdyosu: ham bir video fikrini Gemini ile MiniMax-H3 prompt'una çevirir ve
ComfyUI üzerinde Pika H3 Flex ve/veya MiniMax-H3 ile video üretir (Google Colab, G4 GPU)."""

__version__ = "1.0.0"


def launch(**kwargs):
    from .ui import launch as _launch
    return _launch(**kwargs)
