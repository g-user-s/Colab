#!/usr/bin/env bash
# H3 Stüdyo kurulumu (Linux). Kullanım: bash masaustu/kur.sh
# Kurar: kendi Python ortamı (~/.local/share/h3studyo/venv), PySide6, google-genai, Colab CLI (+411 yaması),
# başlatıcı (~/.local/bin/h3studyo) ve uygulama menüsü kısayolu. sudo gerektirmez (ffmpeg hariç).
set -euo pipefail
DEPO="$(cd "$(dirname "$0")/.." && pwd)"
VENV="${H3STUDYO_VENV:-$HOME/.local/share/h3studyo/venv}"
BIN="$HOME/.local/bin"
UYG="$HOME/.local/share/applications"
SIMGE_DIZIN="$HOME/.local/share/icons/hicolor/scalable/apps"
AYAR="${H3STUDYO_AYAR:-$HOME/.config/h3studyo/ayarlar.json}"

PY="${PYTHON:-python3}"
if ! "$PY" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)'; then
  echo "HATA: Python 3.12 veya üstü gerekli (Colab CLI bunu istiyor). Şu an: $("$PY" --version 2>&1)"
  echo "      Ubuntu 24.04+ ya da Fedora 39+ bunu içerir; başka python için: PYTHON=/yol/python3.12 bash $0"
  exit 1
fi
for arac in ffmpeg ffprobe; do
  command -v "$arac" >/dev/null || { echo "HATA: $arac yok. Kur: sudo apt install ffmpeg  (ya da: sudo dnf install ffmpeg)"; exit 1; }
done

echo "1/5 Python ortamı: $VENV"
"$PY" -m venv "$VENV"
"$VENV/bin/pip" install -q --upgrade pip
echo "2/5 Paketler (PySide6, google-genai, google-colab-cli) — birkaç dakika sürebilir"
"$VENV/bin/pip" install -q "PySide6==6.8.1" "google-genai==2.34.0" "google-colab-cli==0.8.0" keyrings.alt
echo "3/5 Colab CLI 411 yaması"
"$VENV/bin/python" "$DEPO/muse/yama_411.py"

echo "4/5 Başlatıcı ve menü kısayolu"
mkdir -p "$BIN" "$UYG" "$SIMGE_DIZIN"
cat > "$BIN/h3studyo" <<SON
#!/usr/bin/env bash
export PYTHONPATH="$DEPO/masaustu\${PYTHONPATH:+:\$PYTHONPATH}"
exec "$VENV/bin/python" -m h3studyo "\$@"
SON
chmod +x "$BIN/h3studyo"
cp "$DEPO/masaustu/h3studyo/h3studyo.svg" "$SIMGE_DIZIN/h3studyo.svg"
cat > "$UYG/h3studyo.desktop" <<SON
[Desktop Entry]
Type=Application
Name=H3 Stüdyo
Comment=Colab GPU'sunda Türkçe konuşmalı video üretimi
Exec=$BIN/h3studyo
Icon=h3studyo
Terminal=false
Categories=AudioVideo;Video;
StartupWMClass=h3studyo
SON
command -v update-desktop-database >/dev/null && update-desktop-database "$UYG" >/dev/null 2>&1 || true

echo "5/5 Ayarlar: $AYAR"
mkdir -p "$(dirname "$AYAR")"
# Sistem anahtarlığı (GNOME Keyring / KWallet) yoksa keyring düz dosya yedeğine (keyrings.alt) düşer
ANAHTARLIK=$("$VENV/bin/python" -c 'import keyring; m = type(keyring.get_keyring()).__module__; print("yok" if m.startswith(("keyrings.alt", "keyring.backends.fail", "keyring.backends.null")) else "var")' 2>/dev/null || echo yok)
"$VENV/bin/python" - "$AYAR" "$VENV" "$ANAHTARLIK" <<'SON'
import json, os, sys
yol, venv, anahtarlik = sys.argv[1:]
ayar = json.load(open(yol)) if os.path.isfile(yol) else {}
ayar.update(python=f"{venv}/bin/python", colab=f"{venv}/bin/colab")
ayar.setdefault("uretim_dizini", os.path.expanduser("~/H3Uretimler"))
ayar.setdefault("gpu", "a100,g4")
if anahtarlik == "yok":
    ayar["duz_anahtarlik"] = True
json.dump(ayar, open(yol, "w"), ensure_ascii=False, indent=2)
print(f"   sistem anahtarlığı: {anahtarlik}" + (" → Colab girişi düz dosyada saklanacak" if anahtarlik == "yok" else ""))
SON

echo
echo "✅ Kurulum tamam. Uygulama menüsünde “H3 Stüdyo”yu aç ya da terminalde: $BIN/h3studyo"
case ":$PATH:" in *":$BIN:"*) ;; *) echo "   (Not: $BIN PATH'te değil; menüden açabilir ya da tam yolu kullanabilirsin.)";; esac
echo "   İlk açılışta: Durum ve kurulum → Giriş yap → Gemini anahtarı → Kuru deneme. Ayrıntı: masaustu/BENIOKU.md"
