# Görev: Fatih — anahtar kare, 2. sürüm (kapı tutarlılığı, sancaklar, ses)

**Depo:** https://github.com/g-user-s/Colab (dal `claude/trusting-johnson-c5d0tf`). Önce: `cd ~/workspace/Colab && git pull`.

## Neden

1. sürümün (`20261120_fatih_kare`) kesmelerinde üç sorun bulundu. Bu sürüm üçünü de düzeltiyor:

| Sorun | Neden | Düzeltme |
|---|---|---|
| Kapı her çekimde başka bir yapı (1. ve 10. çekim ile 3–6. çekim farklı) | Her kare mekânı ayrı ayrı çizdi | Önce bir **mekân plakası** (`P_YOL`) üretilir. Kapıyı gören bütün kareler bu plakadan ya da bir tabandan türetilir. Plaka videoya girmez. |
| Sancaklarda yıldız | Model kırmızı sancak + hilali Türk bayrağına tamamladı | Sancaklar **sembolsüz**, düz kırmızı ve düz yeşil |
| Sessiz sahneler mehter kadar yüksek; son kesmede +19 dB sıçrama | Her çekimin sesi ayrı ayrı −16 LUFS'a çekiliyordu | Artık yalnızca birleşik film dengeleniyor (kodda) |

Ayrıca anne çekimlerinde (C2, C8) kamera kapıya bakmıyor: kapı kadraj dışında, ışık yandan. Senin 1. sürümde yaptığın düzeltmenin aynısı.

**Ayarlar:** 1. sürümle aynı: 10 tek çekim, ~62 sn, Pika, seed 22, eşik yüksek, yeniden üretim 1.

**Tahmini maliyet:** A100'de ~64–120 dk, **~7–14 CCU**. 1. sürüm 10,9 CCU tutmuştu.

**Onay noktaları:**
1. plaka ve kareler;
2. üretim.

---

## 1. Hazırlık

```bash
ls ~/workspace/h3uretim/20261119_fatih4/gorseller/{K1,K2,K3,MEKAN}.png ~/workspace/h3uretim/20261119_fatih/ilham/tablo.jpg \
   ~/workspace/h3uretim/20261120_fatih_kare/kareler/{C8a,C8b}.png
D=~/workspace/h3uretim/20261120_fatih_kare2
mkdir -p $D
cp ~/workspace/Colab/muse_gorevleri/20261120_fatih_kare2/uzun_senaryo.json $D/
~/workspace/tools/h3muse-venv/bin/python -c "import json; s=json.load(open('$D/uzun_senaryo.json')); print(s['h3app_surum'], s['durum'], len(s['kareler']), [k['id'] for k in s['kareler'] if k.get('plaka')])"
```

**Beklenen:** `1311603f4c37 hazir 21 ['P_YOL']`. Biri eksikse dur ve bana yaz.

`uzun_senaryo.json`'u elle düzenleme; `plan` adımını çalıştırma.

## 2. Plaka ve kareler (21 görsel)

C8a ve C8b'yi senin düzelttiğin 1. sürüm karelerinden al, diğerlerini yeniden üret:

```bash
cd ~/workspace/Colab
~/workspace/tools/h3muse-venv/bin/python muse/uzun_senaryo.py kareler --dizin ~/workspace/h3uretim/20261120_fatih_kare2 \
  --ref C8a=~/workspace/h3uretim/20261120_fatih_kare/kareler/C8a.png \
  --ref C8b=~/workspace/h3uretim/20261120_fatih_kare/kareler/C8b.png
```

**Komutun yaptıkları:**
- Önce kare listesini denetler.
- Sonra sırayla üretir: önce `P_YOL`, sonra ondan türeyen kareler.
- Yarıda kalırsa aynı komutu tekrar çalıştır; var olanları atlar.

**Kontrol et:**
1. **P_YOL (en önemlisi):**
   - kapı yol hizasından, tam karşıdan; kireç taşı ve kırmızı tuğla bantlı kemer, top izleri, kemerin üstünde solmuş fresko;
   - yol boş;
   - sancaklar **düz kırmızı ve düz yeşil, üzerinde hiçbir işaret yok**.

   Beğenmezsen önce bunu yenile (`--yeniden P_YOL`). Plaka değişirse ondan türeyen her şeyi de yenile (aşağıdaki liste).
2. **Kapı tutarlılığı:** C1, C3, C4, C5, C6, C7, C9 ve C10'da görünen kapı **P_YOL'daki kapının aynısı** mı? Kemerin biçimi, tuğla bantları, fresko aynı yerde mi?
3. **Sancaklar:** hiçbir karede hilal, yıldız ya da yazı yok.
4. **Anne (C2, C8):** kapı görünmüyor; arkada kalabalık ve ev duvarı.
5. 1. sürümdeki diğer kontroller: kimlik, a→b farkı, C4b'de Zonaro düzeni, ceset yok.

**Bağlılıklar** (birini yenilersen altındakileri de yenile):
- P_YOL → C1a, C3a, C4b, C5a, C6a, C7a, C9a;
- C1a → C1b → C10a → C10b;
- C2a → C2b; C3a → C3b; C4b → C4a; C5a → C5b; C6a → C6b; C7a → C7b; C9a → C9b.

Örnek: `--yeniden P_YOL --yeniden C1a --yeniden C1b …`. Her kare için en fazla 2 kez yenile.

P_YOL'u ve 20 kareyi orhan'a göster: önce plaka, sonra çekim sırasıyla a ve b yan yana.

## 3. Onay mesajı

```
Fatih kare 2. sürüm hazır: kapı artık her çekimde aynı (tek plakadan), sancaklar sembolsüz, sesler birleşik filmde dengeleniyor.
10 tek çekim, ~62 sn. Plaka ve kareler ekte. GPU: A100 (yoksa G4). Tahmini ~64–120 dk, ~7–14 CCU. Güncel bakiye: <colab usage>.
Başlayayım mı?
```

## 4. Üretim

```bash
~/workspace/tools/h3muse-venv/bin/python muse/h3_uret.py uret --senaryo ~/workspace/h3uretim/20261120_fatih_kare2/uzun_senaryo.json \
  --oturum-dizini ~/workspace/h3uretim/20261120_fatih_kare2/oturum --gpu a100,g4
```

Plaka Colab'a yüklenmez; bu normal.

## 5. İnceleme

Sınır kareleri 1. sürümle aynı zamanlardan:

```bash
cd ~/workspace/h3uretim/20261120_fatih_kare2
for t in 5.1 5.3 10.2 10.4 15.4 15.6 23.4 23.6 28.6 28.8 35.2 35.4 40.3 40.5 45.5 45.7 57.0 57.2; do
  ffmpeg -v error -y -ss $t -i oturum/cikti/kare_pika_h3_flex_birlesik.mp4 -frames:v 1 sinir_$t.png; done
```

1. sürümle karşılaştırarak yaz:
- **Kapı:** bütün çekimlerde aynı yapı mı? Kesmeler "aynı yerdeyiz" hissi veriyor mu?
- **Sancaklar:** yıldız ya da hilal kaldı mı (karede ya da videoda)?
- **Ses:**
  - 6–8. çekimlerdeki sessizlik mehterden belirgin biçimde daha sessiz mi?
  - son kesmede (57,1 sn) ani yükselme kaldı mı?
  - herhangi bir kesmede ses kopması var mı?
- 1. sürümdeki öteki gözlemler: at bacakları, eller, kalabalık hareketi, konuşma.

## 6. Teslim ve sorular

Drive: `H3_Video_Studyosu/20261120_fatih_kare2/`. Şunları yükle:
- birleşik video ve 10 çekim dosyası. Videoların hepsine "bağlantıya sahip herkes görüntüleyebilir" iznini ver; ben de ölçeceğim.
- `rapor.md`;
- `uzun_sonuc.json`;
- `uzun_senaryo.json`;
- `kareler/`;
- `_kontrol.jpg`;
- sınır kareleri.

orhan'a sor:
- **1. sürüm mü, 2. sürüm mü daha iyi?** Neden?
- **Kesmeler artık aynı yerde gibi mi?**
- **Ses dinamiği nasıl?**
- **gözüne batan:** ne varsa.

## 7. Sonuç mesajı

Başlık `FATİH KARE 2 SONUCU`. Şunları içersin:
- video ve çekim bağlantıları;
- GPU, süre, CCU;
- kare üretiminde yenilemeler;
- süreklilik puanları;
- çekim çekim kusurlar;
- 5. adımdaki karşılaştırma;
- orhan'ın cevapları;
- hatalar ve uyarılar.
