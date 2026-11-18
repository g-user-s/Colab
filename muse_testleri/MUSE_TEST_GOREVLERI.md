# Muse için test görevleri

**Depo:** https://github.com/g-user-s/Colab (herkese açık), dal `claude/trusting-johnson-c5d0tf`
```bash
cd ~/workspace
git clone -b claude/trusting-johnson-c5d0tf https://github.com/g-user-s/Colab   # zaten varsa: cd Colab && git pull
cd ~/workspace/Colab
```
Bütün komutlar `~/workspace/Colab` içinden çalıştırılır.

**Amaç:** Bu testler senin bir sınavın değil, bizim araçlarımızın sınavı. Rehberin ve betiklerin senin ortamında gerçekte nasıl çalıştığını öğrenmek istiyoruz:
- hangi adımlar sorunsuz yürüyor;
- hangilerinde zorlanıyorsun;
- hangileri senin ortamında hiç mümkün değil.

Sonra kodu ve rehberi buna göre düzelteceğiz.

**En değerli bilgi, yapamadığın şeydir.** Bir adımı yapamazsan bunu açıkça yaz; bu başarısızlık sayılmaz. Şunları yapma:
- bir adımı yapmış gibi gösterme;
- sonucu tahmin edip yazma;
- kendi geçici çözümünü sessizce uygulama.

Bir şeyi rehberden farklı yaptıysan bunu ve nedenini yaz.

**Onay kuralların her zamanki gibi geçerli.** Her testin başında maliyetini ve ne yapacağını yazdım. GPU açan tek test T12'dir ve isteğe bağlıdır.

**Toplam bütçe:**
- T0–T11 (CPU testleri): en fazla ~0,1 CCU;
- T12 (isteğe bağlı GPU testi): ~1–1,5 CCU;
- Gemini: en fazla ~12 istek.

---

## Nasıl raporlanır

Her testten sonra şu kalıpla kısa bir kayıt tut ve hepsini sonunda tek bir `RAPOR` mesajında gönder:

```
### T<n> — <ad>
Durum: BAŞARILI | KISMEN | BAŞARISIZ | ATLANDI (neden)
Süre: <dakika>
Ne yaptım: <çalıştırdığım komutlar, sırasıyla>
Ne oldu: <önemli çıktı satırları — olduğu gibi kopyala, kısaltırsan "…" koy>
Nerede zorlandım: <belirsiz talimat, eksik araç, zaman aşımı, izin sorunu…>
Rehberden farklı yaptığım: <yoksa "yok">
Önerim: <rehberde ya da betikte neyin değişmesi işini kolaylaştırırdı>
```

Gizli bilgiyi (Gemini anahtarı, token) hiçbir zaman rapora koyma. Bir çıktıda böyle bir şey görürsen `***` ile değiştir.

---

## T0 — Ortam envanteri (CCU: 0)

Aşağıdaki soruları komut çalıştırarak cevapla. Yalnızca bildiğine dayanarak cevap yazma.

1. İşletim sistemi ve Python sürümü: `uname -a; python3 --version`
2. Boş disk: `df -h ~`
3. Araçlar kurulu mu: `which git ffmpeg ffprobe; ls ~/workspace/tools/`
4. Ağ: bu adreslere ulaşabiliyor musun? `curl -sI https://github.com | head -1`, `curl -sI https://huggingface.co | head -1`, `curl -sI https://colaboratory.googleapis.com | head -1`
5. Tek bir komutu en fazla ne kadar süre bekletebiliyorsun? `sleep 120; echo bitti` ve ardından `sleep 600; echo bitti` dene. İkisi de bitiyor mu, yoksa bir zaman aşımı mı var?
6. Arka planda süreç çalıştırabiliyor musun? `nohup sh -c 'sleep 30; date > /tmp/muse_bg.txt' &`, ardından 40 sn sonra `cat /tmp/muse_bg.txt`.
7. Görsel görebiliyor musun? `h3/tests/fixtures/referans.png` dosyasını aç ve ne gördüğünü bir cümleyle anlat. Göremiyorsan "göremiyorum" yaz.
8. Hangi bağlayıcıların var (Drive, Gmail…)? Her birini bir cümleyle yaz.
9. Makine yeniden başlarsa hangi klasörler kalıcı? Bildiğin kadarını yaz. Emin olmadığın yerde "bilmiyorum" de.

## T1 — Depo (CCU: 0)

Rehber 2.3'ü uygula: depoyu klonla ya da güncelle, `claude/trusting-johnson-c5d0tf` dalına geç.
- `git log --oneline | head -3` çıktısını yaz.
- `ls h3/h3app/hikaye.py muse/` çıktısını yaz.

## T2 — Colab CLI (CCU: 0)

```bash
~/workspace/tools/colab whoami
~/workspace/tools/colab-cli-venv/bin/python muse/yama_411.py --kontrol
~/workspace/tools/colab usage
~/workspace/tools/colab sessions
```

Her birinin çıktısını yaz. Hesap e-postasını rapora koyma, "hesap görünüyor" demen yeterli. `sessions` açık bir oturum gösteriyorsa ona dokunma, yalnızca yaz.

## T3 — Kurulum: venv ve anahtar (CCU: 0)

1. Rehber 2.4: `h3muse-venv` venv'ini oluştur ve `google-genai` paketini kur. Kurulum süresini yaz.
2. Rehber 2.5: Gemini anahtarı dosyası. Anahtar zaten varsa yeniden yazma.
3. Doğrulama (anahtarı göstermeden):
   ```bash
   stat -c '%a' ~/.config/h3muse/gemini.key          # 600 olmalı
   wc -c < ~/.config/h3muse/gemini.key                # yalnızca uzunluk
   grep -c -F -f ~/.config/h3muse/gemini.key ~/.bash_history 2>/dev/null || echo 0   # 0 olmalı
   ```
4. Anahtarı dosyaya nasıl yazdın (hangi araçla)? Anahtar herhangi bir anda ekrana, komut satırına ya da sohbete düştü mü? Dürüstçe yaz.

## T4 — Okuduğunu anlama: hatalı senaryo (CCU: 0, Gemini: 0)

`muse_testleri/hatali_senaryo.json` bilerek hatalı hazırlanmış bir test dosyasıdır. Üretimde kullanma.

Rehberin **bölüm 3, Adım 3**'teki kontrol listesini bu dosyaya uygula ve bulduğun bütün sorunları listele. Her sorun için:
- hangi alanda olduğunu;
- ne olması gerektiğini;
- bu sorun üretime giderse videoda ne olacağını

yaz. Dosyada birden fazla hata var; kaç tane bulduğunu söyle. Hiçbir betik çalıştırma, yalnızca oku ve değerlendir.

## T5 — Gerçek senaryo (CCU: 0, Gemini: ~2–3 istek)

```bash
D=~/workspace/h3uretim/test_t5
~/workspace/tools/h3muse-venv/bin/python muse/senaryo.py --sure 8 --stil real --yontem pika \
  --fikir 'Akşamüstü, deniz kenarında bir çay bahçesi. Beyaz önlüklü, kır bıyıklı çaycı solda, elinde çay tepsisiyle duruyor; sağda masada genç bir kadın oturuyor. Çaycı tepsiyi bırakırken sıcak, tok bir sesle "Çaylar taze, buyurun." diyor. Kadın gülümseyip "Eline sağlık." diyor. Kamera: orta plan, yavaş yaklaşma. Ses: dalga sesi, uzaktan martılar.' \
  --cikti $D/senaryo.json
```

- Çıkış kodunu, süreyi ve yazdırılan model satırlarını yaz.
- Kontrol listesini (Adım 3) bu senaryoya uygula. Her madde için evet/hayır ve gerekçe yaz.
- Prompt'u Türkçe olarak 3–4 cümleyle özetle: Gemini ne yazmış?

## T6 — Kuru deneme: tek video (CCU: ~0,01)

Rehber 2.6'yı uygula: CPU runtime, sahte mod. Şunları yaz:
- toplam süreyi;
- yazdırılan ilerleme satırlarını (ilk 10 ve son 10 satır);
- `rapor.md`'nin içeriğini.

Komut uzun sürerse onu nasıl beklediğini anlat: ön planda mı bekledin, arka planda çalıştırıp yokladın mı?

## T7 — Kesinti ve devam (CCU: ~0,01)

Bu test, makinen yeniden başladığında ne olacağını taklit eder.

1. T6'daki komutu yeni bir klasörle (`D=~/workspace/h3uretim/test_t7`) **arka planda** başlat ve çıktısını bir dosyaya yönlendir:
   ```bash
   nohup python3 muse/h3_uret.py uret --senaryo <T6'daki senaryo.json> --oturum-dizini $D/oturum \
     --gpu cpu --anahtar '' --aralik 15 --sorunlu-kabul > $D/cikti.log 2>&1 &
   ```
2. `cikti.log`'da `Üretim arka planda başlatıldı` satırı görünür görünmez süreci durdur: `pkill -f "h3_uret.py uret"`.
3. Rehber bölüm 7'yi uygula: bitmemiş oturumu bul, `durum` ve `devam` ile tamamla.
4. Sonunda `colab sessions` çıktısını yaz. Açık oturum kalmamalı.

## T8 — Kuru deneme: uzun video (CCU: ~0,02)

`GOREV_UZUN_VIDEO_DENEYI.md`'nin **yalnızca 1. adımını** (uzun akışın kuru denemesi) uygula. Raporun içeriğini ve `cikti/` klasörünün dosya listesini yaz.

## T9 — Gemini ile hikâye kartı ve görseller (CCU: 0, Gemini: ~4–5 istek)

```bash
D=~/workspace/h3uretim/test_t9
PY=~/workspace/tools/h3muse-venv/bin/python
$PY muse/uzun_senaryo.py kart --dizin $D --sure 20 --stil real \
  --fikir 'Bir sahaf dükkânında öğleden sonra. Gözlüklü, gri sakallı sahaf Rıza, raf tozunu alıyor. Sarı yağmurluklu bir genç kız içeri girip "Eski haritalarınız var mı?" diye soruyor. Rıza gülümseyip "En güzelleri arka odada." diyor.'
$PY muse/uzun_senaryo.py gorsel --dizin $D
```

1. Kartı (`hikaye.json`) Türkçe olarak özetle: karakterler, kıyafetler, sesler, bloklar.
2. `gorseller/` içindeki her görseli aç ve tarif et. Karttaki tarife uyuyor mu? Her görsel için 1–10 puan ver ve gerekçesini yaz.
3. Görsel üretimi hata verdiyse tam mesajı yaz (anahtar yerine `***`).
4. `plan` adımını **çalıştırma** (kota tasarrufu).

## T10 — Drive bağlayıcısı (CCU: 0)

1. Drive'da `H3_Video_Studyosu/_muse_test/` klasörünü oluştur (varsa kullan).
2. T6'nın `rapor.md` dosyasını ve T9'un `gorseller/K1.png` dosyasını oraya yükle.
3. Drive'daki boyutlarını yereldeki boyutlarla (`wc -c`) karşılaştır.
4. Hiçbir şeyi silme.

## T11 — Colab içinden Drive bağlama denemesi (CCU: ~0,01)

Bu test, Colab runtime'ının Drive'ı kendisinin bağlayıp bağlayamadığını öğrenmek için. Bizim betikler şu an bunu kullanmıyor.

```bash
~/workspace/tools/colab new -s dmtest
~/workspace/tools/colab drivemount -s dmtest
```

- Bir bağlantı (URL) basıp onay isterse **onaylama**. Ne istediğini ve tam metni yaz, sonra iptal et (Ctrl-C) ya da süreç kendiliğinden bitsin.
- Onay istemeden bağlarsa şunu çalıştır ve çıktıyı yaz: `echo 'import os; print(os.listdir("/content/drive/MyDrive")[:5])' | ~/workspace/tools/colab exec -s dmtest`
- **Her durumda** testi şöyle bitir:
  ```bash
  ~/workspace/tools/colab stop -s dmtest
  ~/workspace/tools/colab sessions
  ```

## T12 — İsteğe bağlı: kısa gerçek üretim (CCU: ~1–1,5, onay gerekir)

Yalnızca T0–T11 bittikten ve orhan onay verdikten sonra yap.

T5'teki senaryo (`test_t5/senaryo.json`) `hazir` ise, rehber bölüm 3'ün Adım 4–6'sını uygula:

```bash
python3 muse/h3_uret.py uret --senaryo ~/workspace/h3uretim/test_t5/senaryo.json \
  --oturum-dizini ~/workspace/h3uretim/test_t5/oturum --gpu a100,g4
```

Videoyu izleyebiliyorsan izle (göremiyorsan kontrol görsellerine bak) ve şunları yaz:
- çaycı ile kadın tarife uyuyor mu?
- replikler doğru kişide mi?
- Gemini izlemesi ne dedi?
- toplam süre ve CCU ne kadar tuttu?

---

## Sonunda

Bütün kayıtları tek bir mesajda `RAPOR` başlığıyla gönder. En sona şu üç soruyu cevapla:

1. Bu rehberde ve betiklerde en çok zorlandığın üç şey nedir?
2. Senin ortamında hiç yapamadığın şeyler hangileri?
3. Bir sonraki sürümde neyin farklı olmasını isterdin? (Ör. daha az adım, farklı çıktı biçimi, tek bir komut.)
