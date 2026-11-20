# Çekim Defteri — Fatih'in İstanbul'a Girişi (anahtar kare yöntemi)

> Bu belge, Muse'a verilen `GOREV_FATIH_KARE.md` görevinin **tamamen Türkçe** karşılığıdır. C2 ve C8'deki kapı hatası düzeltilmiş hâlidir. Bundan sonraki görevler bu defter örnek alınarak yazılır. Nasıl yazılacağı `H3_Ogrenme_Rehberi.pdf` içinde anlatılıyor.

## 1. Künye

| | |
|---|---|
| **Sahne** | Fethin üçüncü günü, Haziran 1453, ikindi. Sultan II. Mehmed, Topkapı'dan şehre giriyor. Fausto Zonaro'nun tablosunun canlı hâli. |
| **Süre** | ~62 sn, 10 tek çekim |
| **Yöntem** | Anahtar kare (her çekimin ilk ve son karesi önceden fotoğraf olarak üretilir) |
| **Görsel stil** | Gerçek çekim, tarihî sinema filmi; 35 mm film, anamorfik lens, yalnızca doğal ışık |
| **Model ayarları** | Pika, seed 22, eşik yüksek, yeniden üretim 1, 1344×768 |
| **Tahmini maliyet** | A100'de 64–120 dk, 7–14 CCU |

**Her karede geçerli yasaklar:**
- okunabilir yazı ve hat yok;
- sancaklarda yıldız yok, yalnızca tek beyaz hilal;
- kan, yara ve ceset yok.

## 2. Oyuncular ve mekân (fatih4'ten hazır görseller)

| Kimlik | Kim | Görsel | Tarif |
|---|---|---|---|
| K1 | Akşemseddin (S1) | `20261119_fatih4/gorseller/K1.png` | ~63 yaş, uzun ak sakal, beyaz sarık, lacivert yün cübbe; yaya. Sesi: sıcak, derin, hafif yıpranmış bariton, yavaş ve saygılı. |
| K2 | Sultan II. Mehmed (S2) | `…/K2.png` | 21 yaş, ince bıyık, kısa sakal; gümüş zırh, kırmızı ipek kaftan, beyaz sorguçlu miğfer; beyaz Arap atı. Sesi: ölçülü, tok, genç bariton; sakin ve buyurgan. |
| K3 | Rum anne ve oğlu (konuşmuyor) | `…/K3.png` | ~30 yaş kadın, ham keten başörtüsü, solgun çivit elbise, kahverengi şal; kucağında 6 yaşında, kıvırcık saçlı, bej tunikli oğlu. |
| MEKAN | Topkapı'nın şehir içinden görünüşü | `…/MEKAN.png` | Kireç taşı ve kırmızı tuğla bantlı, top izli büyük kemer, iç yüzünde solmuş Bizans freskosu. Kemerden şehre taş yol ve meydan. İki yanda yeniçeri kordonu ve kırmızı-yeşil sancaklar. Arkada yıkıntılarda, damlarda ve surun üstünde binlerce Rum. |
| TABLO | Zonaro'nun tablosu | `20261119_fatih/ilham/tablo.jpg` | Yalnızca 4. çekimin son karesinde **düzen referansı** olarak kullanılır. Resmin üslubu ve içindeki cesetler alınmaz. |

## 3. Işık ve mekân mantığı

- **Işık:** Güneş batıda, alçakta, **kapının tam arkasında**. Kamera kapıya baktığında kemerden altın ışık ve toz kameraya doğru gelir; kemerin altı gölgededir, yoldaki herkesin kenarları parlar (ters ışık).
- **Kamera kapıya bakmıyorsa** (anne çekimleri): kapı kadraj **dışında**, solda kalır. Güneş yüzlere soldan, yandan vurur. Annenin arkasında yalnızca kalabalık ve bir ev duvarı görünür.
- **Sultan'ın yakın planları:** Sultan kapıdan geldiği için kameraya bakarken arkasında kemer görünür. Bu doğrudur.

## 4. Anahtar kareler (20 kare)

Her çekimin iki karesi var:
- **a** = ilk kare;
- **b** = son kare.

"Taban" yazan kare, taban karenin **aynı kamera açısıyla, yalnızca söylenen şey değişmiş** hâlidir.

| Kare | Taban | Girdi görselleri | Tarif |
|---|---|---|---|
| **C1a** | — | MEKAN | Şehrin içinde düz bir damdan, ~15 m yükseklikten, 24 mm. Yol boyunca batıya, tam kapıya bakılıyor. Kemer kadrajın üst ortasını dolduruyor, ardındaki gök beyaz-altın parlıyor. Yol ve meydan bomboş. İki yanda yeniçeri kordonu ve sancaklar; arkada yıkıntılarda, surun üstünde, damlarda ve pencerelerde binlerce kişi, omuzlarda çocuklar. Herkes kıpırtısız ve sessiz, yüzler kapıya dönük. |
| **C1b** | C1a | MEKAN | Kamera ~5 m alçalmış: kemer kadrajda biraz yukarıda kalıyor, ön plandaki dam kenarı kadrajdan çıkmış, kalabalık daha yakın. Başka hiçbir şey değişmemiş, kimse kıpırdamamış. |
| **C2a** | — | K3 | Yol kenarındaki kalabalığın içinde, göz hizasında orta plan, 50 mm, sığ alan derinliği. Ortanın biraz sağında anne, yarı profil; oğlu kucağında, yüzünü annesinin omzuna gömmüş. Annenin yüzü gergin, kadraj dışında **soldaki kapıya** bakıyor. Yanında kasketini iki eliyle sıkan yaşlı bir adam. Arkalarında flu, sessiz kalabalık ve bir ev duvarı. **Kapı, kemer ve sur görünmüyor.** Güneş soldan, yandan vuruyor. |
| **C2b** | C2a | K3 | Anne oğlunu daha sıkı kavramış, çenesini kaldırmış, hâlâ sola bakıyor. Oğlan da başını sola çevirmiş; arkadakiler boyunlarını sola uzatıyor. |
| **C3a** | — | MEKAN | Yolun ekseninde alçak, cepheden geniş plan, 32 mm, kemere ~30 m. Mehter takımı geçidin gölgesinden kameraya doğru sıra sıra yürüyor: nakkareler ve kösler askıda, zurnalar havada, zilller; kırmızı-yeşil kaftanlar, uzun külahlar. Arkada atlı sancaktarlar, uzun sancaklar ve yaldızlı alem. Kenarlarda kordon ve kalabalık, yolun ortası açık. |
| **C3b** | C3a | MEKAN | Takım ~10 m yaklaşmış ve yolun iki yanına açılıyor, orta boşalıyor. Kemerin gölgesinde beyaz at ve sorguçlu binici yeni seçiliyor. |
| **C4b** | — | K2, K1, MEKAN + **TABLO (düzen)** | **Zonaro'nun anı, gerçek fotoğraf olarak.** Yolun ekseninde alçak, cepheden geniş plan, 32 mm. Sultan beyaz atıyla geçidin gölgesinden altın ışığa, kameraya doğru, hafif solda çıkıyor. At yüksek ve mağrur adımlıyor, yelesi ve sorguç ışıkta parlıyor. Sultan dimdik, sağ eli hafifçe kalkık, yüzü sakin. Birkaç adım önünde, solda Akşemseddin yürüyor: başı eğik, sağ eli göğsünde. Arkalarında geçidin tamamı beyaz sarıklı atlı paşalar, kırmızı kaftanlı solaklar, mızrak ve sancak ormanıyla dolu, arkalarında parlak gök. Kemerde solmuş, haleli fresko figürü. Sol ön planda, objektife yakın, kırmızı kaftanlı ve kırmızı-altın sarıklı bir muhafız alaya yarı dönük duruyor. Mehter yolun iki yanında. |
| **C4a** | C4b | K2, K1 | Aynı çekimin **birkaç saniye öncesi**: Sultan ve Akşemseddin hâlâ geçidin derin gölgesinde, ~10 m geride, daha küçük, çoğunlukla ışıkla çizilmiş siluetler; beyaz at hafifçe parlıyor. Ön plandaki muhafız, kemer, arkadaki askerler, sancaklar ve yandaki mehter aynı. |
| **C5a** | — | K2, K1, MEKAN | Yolun sol yanında, kordonun hemen arkasından geniş plan, 35 mm. Yolun karşısına ve meydana çapraz bakılıyor, kemer arkada solda parlıyor. Ön planda yeniçerilerin kırmızı sırtlarının arkasında ayakta, sık kalabalık. Orta planda Sultan beyaz atla soldan sağa geçiyor, Akşemseddin sağ üzengisinde, çevrede yaya solaklar, arkada atlı paşalar. |
| **C5b** | C5a | K2 | Sultan meydanın ortasında, kadrajın merkezinde durmuş, alay arkasında hareketsiz. Kadrajdaki bütün halk başı eğik, taşların üstünde diz çökmüş; yeniçeriler ayakta. |
| **C6a** | — | K1, K2, MEKAN | Duran alayın sağ önünden orta ikili plan, 50 mm. Sağda Sultan atının üstünde kıpırtısız, ters ışıkta. Solda, sağ üzengisinde Akşemseddin ona bakıyor, dudakları kapalı. Arkada flu: freskolu kemer, mızrak ve sancaklar, kırmızı kaftanlı solaklar. Kenarlarda diz çökmüş halk. |
| **C6b** | C6a | K1, K2 | Akşemseddin sözünü bitirmiş: dudakları kapalı, başı biraz daha eğik. Sultan ona bakıyor. |
| **C7a** | — | K2, MEKAN | Sultan'ın hafif alttan yakın-orta planı, 50 mm, göğüsten yukarı, atının üstünde. Yüzünün yarısı sıcak gölgede; altın ters ışık sorguçta ve gümüş omuzlarda. Arkada flu, parlak kemer. Sol aşağıya bakıyor, dudakları kapalı. |
| **C7b** | C7a | K2 | Konuştuktan sonra dudakları yine kapalı, bakışı soldan önündeki kalabalığa kalkmış. |
| **C8a** | — | K3 | Yol kenarındaki kalabalığın içinde, taşların üstünde diz çökmüş annenin yakın planı, 50 mm. Oğlunun kıvırcık başını iki koluyla göğsüne bastırıyor, gözleri yerde, titriyor. Arkasında flu, diz çökmüş halk ve ev duvarı. **Kapı görünmüyor**, ışık soldan. |
| **C8b** | C8a | K3 | Gözlerini yavaşça kadraj dışında sağdaki Sultan'a kaldırmış, dudakları aralık, oğlunu hâlâ sıkı tutuyor. Oğlan da yüzünü o yöne çevirmiş. |
| **C9a** | — | K2, MEKAN | Sultan'ın hafif alttan orta planı, 50 mm, belden yukarı; alt kadrajda beyaz atın boynu ve yelesi. Eyerde dimdik, önündeki diz çökmüş kalabalığa bakıyor, dudakları kapalı. Ters ışık, omzunun arkasında flu, parlak kemer. |
| **C9b** | C9a | K2 | Kamera yaklaşmış: kadraj daha sıkı, göğüsten yukarı. Sözünü bitirmiş, dudakları kapalı, yüzü sakin ve şefkatli. |
| **C10a** | C1b | MEKAN | C1b ile aynı damdan görüntü, ama alay meydanın ortasında durmuş, beyaz at merkezde, mehter ve sancaklar yanlarda. Yol boyunca, yıkıntılarda, damlarda ve surun üstünde herkes başı eğik diz çökmüş. |
| **C10b** | C10a | MEKAN | Kamera ~5 m yükselmiş: kemer kadrajda daha aşağıda, şehrin damları daha çok görünüyor. Herkes ayakta, başlar kalkık; alay aynı. |

## 5. Çekimler (10 tek çekim)

Her çekim **tek çekimdir**: kesme yok, ilk kareden başlayıp son karede biter. Zamanlar çekimin kendi içindedir.

| No | Süre | İlk → Son | Kamera | Ne oluyor | Ses | Müzik (yalnızca seyirci duyar) |
|---|---|---|---|---|---|---|
| 1 | 5 sn | C1a → C1b | Yavaş, küçük alçalma | Binlerce kişi sessizce bekliyor. Yalnızca sancaklar kıpırdıyor, toz ışıkta süzülüyor. Babasının omzundaki bir çocuk başını kapıya çeviriyor. | Damlarda rüzgâr, sancak hışırtısı, binlerce sessiz insanın alçak uğultusu; surların ötesinden boğuk, ağır mehter davulu | Yavaş tempolu, sürekli, alçak kontrbas uğultusu |
| 2 | 5 sn | C2a → C2b | Sabit | Mehter yaklaşıyor. Anne yutkunuyor, oğlunu sıkıca tutuyor. Oğlan başını kaldırıp sola bakıyor, arkadakiler de boyunlarını uzatıyor. **Kapı hiç görünmüyor.** | Mehter yükseliyor; yakındaki fısıltılar susturuluyor; oğlanın hızlı nefesi | Kontrbas uğultusu, altına hafif bir def vuruşu ekleniyor |
| 3 | 5 sn | C3a → C3b | Sabit | Mehter ağır adımlarla kemerden çıkıp yolun iki yanına açılıyor; gölgede beyaz at beliriyor. | Yüksek, ağır mehter marşı kemerde yankılanıyor; taşta ayak sesleri; sancakların çırpınışı | Yok |
| 4 | 8 sn | C4a → C4b | Yavaş, küçük ileri itme | **Tablonun anı.** Beyaz at gölgeden ışığa yavaş ve yüksek adımlarla çıkıyor; Sultan hafifçe sağ elini kaldırıyor, Akşemseddin başı eğik, eli göğsünde yürüyor. Atın yürüyüşü doğal dört vuruşlu. Çekim tam Zonaro'nun düzeninde bitiyor. | Mehter tam güçte, kemerin altında nal sesleri, koşum şıngırtısı, yükselen uğultu | Yok |
| 5 | 5 sn | C5a → C5b | Yavaş, küçük sağa çevrinme | Sultan geçerken kalabalık atın arkasından dalga dalga diz çöküyor. Sultan meydanın ortasında duruyor, mehter son bir derin davulla susuyor. | Mehter, son davul; binlerce kişinin diz çökme hışırtısı; nallar susuyor; yalnızca rüzgâr | Yok |
| 6 | 6 sn | C6a → C6b | Sabit | ~1. sn'de Akşemseddin başını kaldırıp konuşuyor: **"Hünkârım, Peygamber efendimizin müjdesi bugün gerçek oldu."** Dudakları yalnızca konuşurken kıpırdıyor, sonra başını eğiyor. | Derin sessizlik, kemerden hafif rüzgâr, atın usul horultusu, eyer gıcırtısı | Yok |
| 7 | 5 sn | C7a → C7b | Sabit | Sultan nefes alıyor, ~1. sn'de sakin bir sesle: **"Bu zafer bizim değil, Allah'ındır."** Sonra bakışını kalabalığa kaldırıyor. | Sessizlik, hafif rüzgâr, bir kez çırpınan sancak; at ağırlığını değiştiriyor | Yok |
| 8 | 5 sn | C8a → C8b | Sabit | Anne titreyerek oğlunu göğsüne bastırıyor, titrek bir nefes alıyor, sonra gözlerini yavaşça Sultan'a kaldırıyor; oğlan da bakıyor. | Sessizlik, annenin titrek nefesi, kumaş hışırtısı; uzakta bir at | Yok |
| 9 | 11 sn | C9a → C9b | Yavaş, küçük ileri itme | ~0,8. sn'de Sultan, meydana ulaşacak kadar yüksek ama sakin ve güven veren bir sesle: **"Kalkınız ve müsterih olunuz. Ben Sultan Mehmed; hepinize söylüyorum ki bu andan itibaren ne hürriyetleriniz ne de hayatlarınız hakkında korkmayınız."** Sözü bitince kıpırdamadan, sakin ve şefkatli bir yüzle duruyor. | Sesi sessiz meydanda taşıyor, kemerde hafifçe yankılanıyor; rüzgâr; atın nefesi | Yok |
| 10 | 5 sn | C10a → C10b | Yavaş, küçük yükselme | Halk sıra sıra başını kaldırıp yavaşça ayağa kalkıyor, sonunda bütün kalabalık ayakta. | Binlerce kişinin kalkarken çıkardığı geniş hışırtı, rahatlamış bir uğultu, rüzgâr | Sıcak, yavaşça kabaran ve sonuna kadar süren yaylı akoru; üstünde tek, pes bir ney notası |

## 6. Muse'a verilecek iş akışı (özet)

1. **Hazırlık:** `git pull`; fatih4 görselleri ve tablo.jpg yerinde mi kontrol et; senaryoyu klasöre kopyala.
2. **Kareler:** `uzun_senaryo.py kareler` ile 20 kareyi üret. Beğenilmeyeni `--yeniden` ile yenile, en fazla 2 kez. Taban kare yenilenirse ona bağlı kare de yenilenir.
3. **Onay 1:** 20 kareyi orhan'a çekim sırasıyla, a ve b yan yana göster.
4. **Onay 2:** süre, CCU ve bakiye ile üretim onayı.
5. **Üretim:** `h3_uret.py uret … --gpu a100,g4`.
6. **İnceleme:** rapor, süreklilik puanı ve çekim sınırlarından kareler.
7. **Teslim:** Drive'a yükle, orhan'a sor, ardından `FATİH KARE SONUCU` mesajını gönder.

Komutların tamamı: `GOREV_FATIH_KARE.md`.
