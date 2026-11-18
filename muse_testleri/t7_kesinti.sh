#!/usr/bin/env bash
# T7: kesinti ve devam testi. Kullanım: bash muse_testleri/t7_kesinti.sh <senaryo.json>
# Üretimi arka planda başlatır, "arka planda başlatıldı" satırı görünce yerel süreci öldürür
# (makinenin yeniden başlamasını taklit eder), sonra rehber bölüm 7'deki gibi durum + devam çalıştırır.
set -u
cd "$(dirname "$0")/.."
SENARYO="${1:?senaryo.json yolu ver}"
D="$HOME/workspace/h3uretim/test_t7_$(date +%H%M%S)"
mkdir -p "$D"
echo "Klasör: $D"
nohup python3 muse/h3_uret.py uret --senaryo "$SENARYO" --oturum-dizini "$D/oturum" \
  --gpu cpu --anahtar '' --aralik 15 --sorunlu-kabul > "$D/cikti.log" 2>&1 &
for i in $(seq 1 120); do
  if grep -q "runtime'da başlatıldı" "$D/cikti.log" 2>/dev/null; then break; fi
  sleep 2
done
if ! grep -q "runtime'da başlatıldı" "$D/cikti.log"; then
  echo "HATA: 4 dk içinde başlatma satırı görülmedi. Log:"; cat "$D/cikti.log"; exit 1
fi
pkill -f "[h]3_uret.py uret --senaryo $SENARYO" && echo "Yerel süreç durduruldu (kesinti taklidi)."
sleep 2
echo "--- oturum aşaması: $(python3 -c "import json;print(json.load(open('$D/oturum/oturum.json'))['asama'])")"
echo "--- durum:"; python3 muse/h3_uret.py durum --oturum-dizini "$D/oturum" | grep -E '"asama"|"canli"|"son_satir"'
echo "--- devam:"; python3 muse/h3_uret.py devam --oturum-dizini "$D/oturum"
echo "--- sunucudaki oturumlar:"; "${COLAB_BIN:-$HOME/workspace/tools/colab}" sessions
