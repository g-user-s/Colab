# Görev: tarihî uzun video — Fatih Sultan Mehmed İstanbul'a giriyor (fethin üçüncü günü, 1453)

**Depo:** https://github.com/g-user-s/Colab (dal `claude/trusting-johnson-c5d0tf`). Önce: `cd ~/workspace/Colab && git pull`.

**Ayarlar:**
- 45 sn, 3 blok, görsel referanslı (ref);
- köprü açık; kadraj sürekliliği kuralı; yeni köprü kuralı (köprülü bloğun ilk 1,5 sn'si önceki bloğun son karesini sürdürür);
- yeniden üretim eşiği **yüksek** (varsayılan).

**Tahmini maliyet:**
- A100'de ~45–75 dk, **~5–8 CCU**;
- Gemini ~15 istek.

**Onay noktaları:**
1. kart;
2. görseller;
3. üretim.

## İlham görselleri

orhan iki görsel gönderecek. Onları şu adlarla kaydet:
- `~/workspace/h3uretim/20261119_fatih/ilham/kapi.jpg`: Topkapı'nın (Theodosius surları) **bugünkü** fotoğrafı;
- `~/workspace/h3uretim/20261119_fatih/ilham/tablo.jpg`: Fausto Zonaro'nun "Fatih'in İstanbul'a Girişi" tablosu.

İkisini de **doğrudan referans olarak kullanma** (`--ref` değil). Neden:
- **fotoğraf** bugünün hâli: çimen, parke yol, tabela, demir kapı;
- **tablo** bir resim (üslubu videoya geçer); ayrıca yerdeki cesetler ve sancaklardaki yazılar videoya girmemeli.

Bunun yerine `--ilham` ile Gemini'ye ilham olarak ver:
- **mekân:** fotoğraftaki mimariyi korur, 1453'e çevirir, modern öğeleri siler;
- **karakterler:** tablodaki kıyafet, zırh ve duruştan esinlenir ama gerçekçi çizer.

## Tarihî ve içerik kuralları

Kartta ve görsellerde bunlara uy:
- **Sultan II. Mehmed 21 yaşında:** ince bıyık, kısa sakal. Yaşlı ya da gür sakallı olmamalı.
- **Kan, ceset, yaralı, yağma sahnesi yok.** Saygılı, törensel bir giriş. Halk korku içinde, ama yaralı ya da perişan gösterilmiyor.
- **Sancaklarda yazı yok:** yalnızca tek bir beyaz hilal, **yıldız yok** (ay-yıldızlı bugünkü bayrak 1453'e ait değil). Arapça hat dahil hiçbir yazı olmamalı.
- **Mekân görseli bomboş:** insan, yeniçeri, halk, at ve sancak yok. Bunların hepsi bloklarda gelir. Mekân görseli bütün blokların sahne çapasıdır; içine konan her şey her bloğa taşınır.
- **Modern öğe yok:** çimen, parke yol, tabela, demir kapı, kablo.
- Akşemseddin, Sultan'ın hocası: yaşlı, ak sakallı, beyaz sarıklı, koyu mavi cübbeli, yaya.

---

## 1. Kart

```bash
cd ~/workspace/Colab
~/workspace/tools/h3muse-venv/bin/python muse/uzun_senaryo.py kart --dizin ~/workspace/h3uretim/20261119_fatih --sure 45 --stil real --fikir 'Fethin üçüncü günü, Haziran 1453, öğleden sonra, açık ve güneşli bir gök. İstanbul kara surlarındaki Topkapı: kalker taş bloklar arasında kırmızı tuğla bantlar, mazgallı burçlar, tuğla kemerli büyük kapı; surlarda kuşatmadan kalma gedikler ve kararmış taşlar, kapının önünde sıkıştırılmış toprak yol. Yirmi bir yaşındaki genç Sultan II. Mehmed, ince bıyıklı ve kısa sakallı, kırmızı kaftanın üstüne gümüş zırh giymiş, başında sorguçlu çelik miğfer, süslü eğerli beyaz bir atın üzerinde kapıya doğru ağır ağır ilerliyor. Yanında yaya yürüyen hocası Akşemseddin, ak sakallı, beyaz sarıklı ve koyu mavi cübbeli. Yolun iki yanında kırmızı börklü yeniçeriler saf tutmuş; üzerinde yalnızca beyaz hilal olan, yazısız kırmızı sancaklar rüzgârda dalgalanıyor. Kapının önünde Sultan atını durdurup surlara bakıyor. Akşemseddin ona dönüp: "Hünkârım, Peygamber efendimizin müjdesi bugün gerçek oldu." Sultan derin bir nefes alıp sakin bir sesle: "Bu zafer bizim değil, Allah'ındır." Sultan kemerin altından geçip hemen içeride atını durduruyor; arkasında kapının kemeri, önünde şehrin halkı, sade yün giysili kadınlar, erkekler ve yaşlılar, korku içinde diz çökmüş, başları önde bekliyor. Sultan onlara bakıp yüksek, sakin ve güven veren bir sesle: "Kalkınız ve müsterih olunuz. Ben Sultan Mehmed; hepinize söylüyorum ki bu andan itibaren ne hürriyetleriniz ne de hayatlarınız hakkında korkmayınız." Halk şaşkınlıkla başını kaldırıyor ve yavaşça ayağa kalkıyor. Kan, ceset, yaralı ya da yağma sahnesi yok; saygılı ve törensel bir giriş.'
```

Fikri değiştirme. Kartta şunları kontrol et:
- 3 blok, 15 + 15 + 15 sn;
- 3 replik harfi harfine aynı: Akşemseddin 1, Sultan 2. Sultan S1, Akşemseddin S2; gerekirse elle düzelt.
- Sultan'ın son sözü 22 kelime ve tek blokta (3. blok) olmalı, bölünmemeli. Halk bu sözlerden sonra ayağa kalkıyor.
- Türkçe harfler korunmuş ("Hünkârım", "Allah'ındır", "Akşemseddin");
- 2 karakter: K1 Sultan II. Mehmed (21 yaş), K2 Akşemseddin. At ve yeniçeriler karakter değil; tarifte geçsinler.
- mekân: 1453'teki Topkapı, dışarıdan; modern öğe yok;
- ışık: açık, güneşli öğleden sonra.

Kartı orhan'a özetle.

## 2. Görseller (ilhamlı)

```bash
~/workspace/tools/h3muse-venv/bin/python muse/uzun_senaryo.py gorsel --dizin ~/workspace/h3uretim/20261119_fatih \
  --ilham MEKAN=~/workspace/h3uretim/20261119_fatih/ilham/kapi.jpg \
  --ilham K1=~/workspace/h3uretim/20261119_fatih/ilham/tablo.jpg \
  --ilham K2=~/workspace/h3uretim/20261119_fatih/ilham/tablo.jpg
```

Kontrol et:
- **K1:** genç (21), ince bıyık ve kısa sakal, zırh ve kaftan, sorguçlu miğfer; tam boy, tek kişi, gerçekçi (resim gibi değil).
- **K2:** ak sakal, beyaz sarık, koyu mavi cübbe; tam boy, tek kişi, gerçekçi.
- **MEKAN:** fotoğraftaki kapının mimarisi (taş ve tuğla bantlar, tuğla kemer, mazgallar); 1453 hâli; insan, at, yazı ve modern öğe yok; güneşli.

Beğenmediğini yeniden üret. İlhamı tekrar vermek için `--yeniden K1 --ilham K1=…` kullan; her görsel için en fazla 2 kez. Görselleri orhan'a göster.

## 3. Plan

```bash
~/workspace/tools/h3muse-venv/bin/python muse/uzun_senaryo.py plan --dizin ~/workspace/h3uretim/20261119_fatih --kol ref
```

`uzun_senaryo.json` dosyasında şunları kontrol et:
- `"kopru": true`, `"yeniden_uretim": 1`;
- blok 2 ve 3'ün ilk çekimi önceki bloğun son kadrajıyla açılıyor mu? (Bu bilgiyi yalnızca raporda yaz.)

## 4. Onay mesajı

```
Tarihî video hazır: "<başlık>", Topkapı 1453, 45 sn, 3 blok. Köprü açık, kadraj sürekliliği, eşik yüksek.
GPU: A100 (yoksa G4). Tahmini ~45–75 dk, ~5–8 CCU. Güncel bakiye: <colab usage>. Kart ve görseller ekte. Başlayayım mı?
```

## 5. Üretim

```bash
~/workspace/tools/h3muse-venv/bin/python muse/h3_uret.py uret --senaryo ~/workspace/h3uretim/20261119_fatih/uzun_senaryo.json \
  --oturum-dizini ~/workspace/h3uretim/20261119_fatih/oturum --gpu a100,g4
```

Günlükte köprü satırlarını kontrol et: `kopru_ref_2.png`, `kopru_ref_3.png` ve iki kez `köprü prompt'u yazılıyor`.

## 6. İnceleme ve teslim

`GOREV_UZUN_VIDEO_2.md`'nin 6. ve 7. adımlarını uygula: rapor, süreklilik puanı, sınır kareleri (14,9 / 15,2 / 30,0 / 30,3), kare kare inceleme. Drive klasörü: `H3_Video_Studyosu/20261119_fatih/`.

Bu videoya özel olarak şunlara da bak:
- At: bacaklar doğal mı, binici atın üstünde sabit mi?
- Sultan kemerin altından geçerken: kimlik ve zırh korunuyor mu?
- Sancaklarda yazı var mı?
- Kalabalıkta kopya yüzler var mı? Halk Sultan'ın sözünden sonra ayağa kalkıyor mu?
- Kan ya da ceset var mı?

orhan'a sor:
- 15. ve 30. saniyelerdeki geçişler: akıcı / fark ediliyor ama rahatsız etmiyor / rahatsız ediyor;
- karakterler ve mekân baştan sona aynı mı?
- tarihî görünüm inandırıcı mı?
- gözüne batan bir şey oldu mu?

## 7. Sonuç mesajı

`UZUN VIDEO 2 SONUCU`'ndaki başlıklarla, başlık `FATİH VİDEOSU SONUCU` olsun. Ayrıca:
- ilham görsellerinin işe yarayıp yaramadığı (görseller fotoğrafa ve tabloya ne kadar benziyor, modern öğe ya da resim üslubu sızdı mı?);
- at ve kalabalık gözlemlerin.
