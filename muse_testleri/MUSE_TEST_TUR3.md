# Muse test görevleri — 3. tur

**Depo:** https://github.com/g-user-s/Colab (dal `claude/trusting-johnson-c5d0tf`). Önce: `cd ~/workspace/Colab && git pull`.

RAPOR 2'ye göre yapılan değişiklikler:

- **İzleme artık senin makinende.** Colab runtime'ı yalnızca GPU işi yapıyor: render, birleştirme, otomatik kontrol. Videonun Gemini'ye izletilmesi, yeniden üretim kararı, süreklilik puanı ve köprü prompt'u senin makinenden yapılıyor; anahtar runtime'a hiç gitmiyor. Kusur bulunursa yeni seed ile **aynı runtime'da** tekrar üretiliyor.
- **`h3_uret.py` artık `~/workspace/tools/h3muse-venv/bin/python` ile çalıştırılıyor.** İzleme için `google-genai` gerekiyor.
- **`NO_PROXY` hatası:** köşeli IPv6 kayıtları artık betikler tarafından düzeltiliyor.
- **İlk yanıt sınırı:** senin ortamında 60 sn (önce 10 sn'ydi; brief bu yüzden yedek modele düşüyordu).
- **Prompt kuralları:** brief, fikirde adı geçmeyen bir yeri ("Boğaz" gibi) eklemiyor. Hikâye kartı adlarda Türkçe harfleri koruyor.
- **Rehber:** vekil anahtar, onay kartları ve tentedeki sözde yazı eklendi.

**Bütçe:** CCU ~0,02 (yalnızca CPU), Gemini ~1 istek (T13). GPU açılmıyor.

---

## T13 — Video izleme: sen ile Gemini

`muse_testleri/MUSE_TEST_T13_VIDEO.md` dosyasını uygula. T12'nin videosu kullanılıyor. Kendi değerlendirmeni Gemini'nin sonucuna bakmadan yaz.

## T14 — Aynı runtime'da yeniden üretim (CPU, ~0,01 CCU, Gemini 0)

Yeni akışın Colab'de denenmemiş tek parçası, aynı runtime'da arka arkaya birden fazla GPU işi çalıştırmak. Bunu kuru denemeyle sınıyoruz. `H3MUSE_TEST_INCELEME` değişkeni izleme sonucunu taklit eder: ilk video "yüksek kusurlu", ikincisi "temiz" sayılır. Böylece betik yeniden üretime zorlanır ve Gemini'ye hiç gidilmez.

```bash
cd ~/workspace/Colab
~/workspace/tools/h3muse-venv/bin/python muse/senaryo.py --fikir 'Kuru deneme' --sure 5 --sahte \
  --cikti ~/workspace/h3uretim/test_t14/senaryo.json
H3MUSE_TEST_INCELEME='[{"verdict":"fail","defects":[{"start_s":1,"end_s":2,"severity":"high","category":"test","description":"zorunlu yeniden üretim testi"}],"summary":"test"},{"verdict":"pass","defects":[],"summary":"ok"}]' \
  ~/workspace/tools/h3muse-venv/bin/python muse/h3_uret.py uret --senaryo ~/workspace/h3uretim/test_t14/senaryo.json \
  --oturum-dizini ~/workspace/h3uretim/test_t14/oturum --gpu cpu --anahtar ~/.config/h3muse/gemini.key \
  --aralik 15 --sorunlu-kabul
```

**Beklenen:**
- tek bir `Runtime açıldı` satırı;
- `İş 1` ve `İş 2` satırları;
- `🔁 Yüksek önemde kusur; aynı runtime'da yeni seed (1022)` satırı;
- `⭐ Seçilen: …seed1022.mp4 … 2 aday`;
- raporda iki `aday` satırı ve `aktif atama: 0`.

Yazman gerekenler: bütün ilerleme satırları ve `rapor.md`.

## T15 — Uzun video, köprüyle (CPU, ~0,01 CCU, Gemini 0)

```bash
cd ~/workspace/Colab
K=~/workspace/h3uretim/test_t15
~/workspace/tools/h3muse-venv/bin/python muse/uzun_senaryo.py kart --dizin $K --fikir 'Kuru deneme: "Merhaba." "Hoşça kal."' --sure 24 --sahte
~/workspace/tools/h3muse-venv/bin/python muse/uzun_senaryo.py gorsel --dizin $K
~/workspace/tools/h3muse-venv/bin/python muse/uzun_senaryo.py plan --dizin $K --kol ref --kopru
H3MUSE_TEST_INCELEME='[{"verdict":"pass","defects":[],"summary":"ok"},{"verdict":"pass","defects":[],"summary":"ok"}]' \
H3MUSE_TEST_SUREKLILIK='[{"kimlik":9,"kiyafet":9,"mekan":9,"ses":7,"hikaye":8,"ortalama":8.4,"sorunlar":[]}]' \
  ~/workspace/tools/h3muse-venv/bin/python muse/h3_uret.py uret --senaryo $K/uzun_senaryo.json --oturum-dizini $K/oturum \
  --gpu cpu --anahtar ~/.config/h3muse/gemini.key --aralik 15
```

(`$K` değişkeni komutlar arasında kaybolursa tam yolu yaz.)

**Beklenen:**
- 3 GPU işi (blok 1, blok 2, birleştirme);
- `kopru_ref_2.png` yüklendi satırı;
- raporda `ses 7 … ortalama 8.4`;
- `aktif atama: 0`.

Yazman gerekenler: ilerleme satırları ve `rapor.md`.

---

Bitince `RAPOR 3` başlığıyla tek mesajda gönder: T13, T14, T15.
