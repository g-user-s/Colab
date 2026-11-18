# Muse test görevleri — 2. tur

**Depo:** https://github.com/g-user-s/Colab (dal `claude/trusting-johnson-c5d0tf`). Önce: `cd ~/workspace/Colab && git pull`.

İlk turdaki raporun için teşekkürler; çok değerliydi. Raporuna göre şunlar düzeltildi:

- **Yama kontrolü:** `yama_411.py`, elle yapılmış işaretsiz yamayı artık tanıyor ve ikinci kez eklemiyor.
- **Anahtar mesajları:** anahtar eksikse betikler Gemini'ye gitmeden önce durup ne eksik olduğunu ve kimin vereceğini söylüyor. `gorsel` ve `plan` adımları, kart yoksa "önce kart adımını çalıştır" diyor.
- **CCU tahmini:** rapor artık "açık kalma süresi × saatlik oran" tahminini 3 ondalıkla yazıyor.
- **T7 betiği:** T7 için hazır bir betik var: `muse_testleri/t7_kesinti.sh`.
- **Rehber:** rehberin başına senin ortamına özgü notlar eklendi (uzun komutlar, kabuk değişkenleri, `pkill`, Drive, `drivemount`).

Bu tur, anahtar olmadığı için yapamadığın testleri tamamlıyor. Raporlama kalıbı ilk turdakiyle aynı.

**Bütçe:**
- H0–T10b: CCU ~0,02, Gemini ~8 istek;
- T12 (isteğe bağlı, onay gerekir): ~1–1,5 CCU.

---

## H0 — Hazırlık: Gemini anahtarı

orhan anahtarı güvenli giriş kartıyla verecek. Anahtarı `~/.config/h3muse/gemini.key` dosyasına tek satır olarak yaz (rehber 2.5), sonra doğrula:

```bash
stat -c '%a' ~/.config/h3muse/gemini.key       # 600
wc -c < ~/.config/h3muse/gemini.key             # yalnızca uzunluk
grep -c -F -f ~/.config/h3muse/gemini.key ~/.bash_history 2>/dev/null || echo 0   # 0
```

Anahtar sohbete, komut satırına ya da ekrana düştü mü? Dürüstçe yaz.

## T2b — Yama kontrolü (tekrar)

```bash
~/workspace/tools/colab-cli-venv/bin/python muse/yama_411.py --kontrol
```

Beklenen: `✅ Yama işlevsel olarak var (elle uygulanmış, işaretsiz)` ve çıkış kodu 0.

## T5 — Gerçek senaryo

İlk turdaki T5'in aynısı: komut, kontrol listesi ve prompt özeti. Ek olarak şunu yaz: Gemini'nin prompt'unda T4'teki 9 hata türünden herhangi biri var mı?

## T9 — Hikâye kartı ve görseller

İlk turdaki T9'un aynısı. Görsellere 1–10 puan verirken şunlara ayrıca bak:
- karakter tam boy mu?
- tek kişi mi?
- mekân görselinde insan var mı?

Beğenmediğin bir görsel olursa **bir kez** `--yeniden K1` dene ve ikisini karşılaştır.

## T10b — Drive

T9'un `gorseller/K1.png` dosyasını `H3_Video_Studyosu/_muse_test/` klasörüne yükle ve boyutunu doğrula.

## T6b — Yeni rapor biçimi (CCU: ~0,01)

Rehber 2.6'yı yeni bir klasörle (`test_t6b`) bir kez daha çalıştır. `rapor.md`'deki `CCU:` satırını aynen yaz.

## T12 — İsteğe bağlı: kısa gerçek üretim (onay gerekir)

T5'in senaryosu `hazir` ise ve orhan onay verirse, ilk turdaki T12'yi uygula. Bu, gerçek GPU ve gerçek Gemini izlemesinin ilk uçtan uca denemesi olacak. Raporda şunlar olsun:
- tam `rapor.md`;
- Gemini izlemesinin söylediği;
- videodan senin gördüklerin (izleyemiyorsan `_kontrol.jpg` dosyası);
- toplam süre.

---

Bitince `RAPOR 2` başlığıyla tek mesajda gönder. Bu turda yeni bir şeyde zorlandıysan özellikle yaz.
