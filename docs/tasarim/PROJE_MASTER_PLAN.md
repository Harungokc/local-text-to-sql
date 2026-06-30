# Proje Master Planı — En Sağlam İşi Çıkarmak

> Bu belge: 3 araştırma raporu + kurulan Faz 1 iskeletinden **en sağlam işi nasıl çıkarırız** ve **ileride sorun yaşamamak için nelere dikkat ederiz** sorusunun cevabıdır.
> Tarih: 2026-06-24

---

## 0. Bu Proje Aslında Ne? (hedefi doğru anlamak)

Bu bir iç şirket aracı değil — **portföy / vitrin projesi.** Amaç: LinkedIn'de paylaşıp şirketlere "bu işi mühendislik disipliniyle yapabiliyorum" kanıtı sunmak.

Bu hedef her kararı belirler. "Sağlam iş" burada şu 4 şey demek:

1. **Demo-dayanıklı** — gösterim/video sırasında utandıracak hata olmaz.
2. **Ayrışan** — piyasadaki sıradan "Vanna + GPT API + Streamlit" demolarından net farklı.
3. **Tekrar üretilebilir & temiz** — başkası klonlayıp 10 dakikada çalıştırabilir.
4. **Anlatılabilir** — README + mimari diyagram + demo + **dürüst** doğruluk sayıları + LinkedIn yazısı.

> ⚠️ Demo **public** olacağı için gerçek şirket verisi KULLANILMAZ. Hem gizlilik pitch'iyle çelişir hem risklidir. Bunun yerine **sentetik ama gerçekçi perakende veri seti** kullanılır (aşağıda Faz 0).

---

## 1. Bu Projeyi Ne Ayrıştırır? (vitrin stratejisi)

Çoğu aday şunu yapar: bulut API + hazır kütüphane + "bakın çalışıyor". Bu projenin farkı **ciddiyet ve dürüstlük**:

| Sıradan demo | Bu proje |
|---|---|
| Bulut API → veri dışarı çıkar | **%100 yerel / gizlilik-korumalı** — şirketlerin asıl korkusunu çözer |
| SQL'i körü körüne çalıştırır | **Çok-katmanlı SQL güvenliği** (read-only kullanıcı + read-only transaction + sqlglot AST + timeout) |
| "Çalışıyor" der, kanıt yok | **Dürüst doğruluk ölçümü** (kendi gold set + execution accuracy) |
| Tek model, tek atış | **Araştırma-temelli mimari** (şema linkleme + few-shot + self-correction) |
| Sayıyı LLM uydurur | **Sayıyı pandas hesaplar, LLM sadece yorumlar** → halüsinasyon yok |

**Anlatının kalbi:**
> "Kurumsal text-to-SQL hâlâ çözülmemiş zor bir problem — Spider 2.0 benchmark'ında GPT-4o bile sadece ~%10 başarıyor. Ben buna mühendislik disipliniyle, veriyi hiç dışarı çıkarmadan yaklaştım."

Bu cümle, yaptığımız 3 araştırma raporunu doğrudan LinkedIn içerik yakıtına çevirir.

---

## 2. Sağlam MVP Kapsamı — Az Ama Kusursuz

**İlke: Yarım çalışan 10 özellik yerine, kusursuz çalışan 4 özellik. Demo'da çöken özellik, hiç olmayandan kötüdür.**

### MVP'ye DAHİL
- `POST /sor` tam akışı: TR soru → şema linkleme → few-shot → SQL üret → güvenlik doğrula → read-only çalıştır → 1 tur self-correction → pandas metrik + TR özet.
- Sentetik demo veri seti + 30-40 few-shot örneği + gold set.
- Çok-katmanlı güvenlik (kuruldu, test 15/15).
- Basit, şık tek-sayfa demo arayüzü.
- README + mimari diyagram + kurulum + dürüst doğruluk sonuçları.

### MVP'ye DAHİL DEĞİL (README "Yol Haritası"nda anlatılır, yapılmaz)
- Çoklu kullanıcı / RBAC / kimlik doğrulama.
- Çoklu aday üretimi + seçici (CHASE-SQL).
- Intent-based retrieval (Pinterest yöntemi).
- Grafik üretimi (vakit kalırsa opsiyonel).

---

## 3. "Nelere Dikkat Etmeli" — Risk Kaydı (en kritik bölüm)

İleride sorun çıkarabilecek her nokta ve önlemi:

| # | Risk | Etki | Önlem |
|---|---|---|---|
| **R1** | Yanlış SQL → yanlış rapor (sessiz hata) | Yüksek | Gold set + execution accuracy; self-correction; boş/şüpheli sonuçta uyarı |
| **R2** | LLM sayı uydurması (halüsinasyon) | Yüksek | Sayıyı pandas hesaplar, LLM yorumlar; promptta "verilen sayı dışında rakam üretme" |
| **R3** | Güvenlik açığı (yazma/silme/injection) | Kritik | 4 katman savunma (kuruldu, 15/15 test geçti) |
| **R4** | 8GB M1'de model çökmesi/yavaşlık | Orta | Faz 1 küçük 7B model; ağır demo'yu kiralık 32B'de yap |
| **R5** | Sunucu maliyeti kaçağı (açık unutulan GPU) | Orta | RunPod saatlik; demo öncesi aç, sonra kapat; README'de uyarı |
| **R6** | Şema değişince sistem kırılır | Orta | Şema runtime'da okunur (sabit DDL gömülü değil), önbellek yenilenebilir |
| **R7** | Demo sırasında canlı model hatası | Yüksek (vitrin!) | Sıcaklık 0 determinizm + önceden test edilmiş soru seti + **yedek kayıtlı GIF/video** |
| **R8** | Karmaşık soruda düşük doğruluk | Orta | Demo'yu sistemin güçlü olduğu sorularda göster; sınırları README'de dürüstçe yaz |
| **R9** | Aşırı mühendislik / hiç bitmeme | Orta | MVP kapsamına sadık kal; ertelenenleri "gelecek işi"ne yaz |
| **R10** | Tekrar üretilemezlik ("bende çalışıyor") | Orta | Pin'li requirements, tek-komut kurulum, sentetik veri scripti, `.env.ornek` |
| **R11** | Gizli bilgi sızması (repo'ya parola/veri) | Kritik | `.gitignore` (kuruldu); `.env` asla commit; veri sentetik |
| **R12** | Bağımlılık şişmesi | Düşük | Vanna yerine saf chromadb; minimum bağımlılık |

---

## 4. Kalite İlkeleri (kod sağlamlığı = "sorun yaşamamak")

1. **Her katman tek sorumluluk** — güvenlik/DB/LLM/şema/rapor ayrı dosyalar (zaten böyle).
2. **Hata yutma yok** — her `except` loglar, kullanıcıya net Türkçe hata döner.
3. **Demo'da determinizm** — SQL üretimi sıcaklık 0.0.
4. **Test edilebilirlik** — `test_guvenlik.py` + `gold_set.py` + eklenecek `test_pipeline.py`.
5. **Config env'den** — kod içinde sabit yok (`os.environ.get` + fallback).
6. **Her sorgu loglanır** — soru + üretilen SQL + süre → şeffaflık.
7. **Dokümantasyon kod kadar önemli** — vitrin projesinde README başarının yarısı.

---

## 5. Yol Haritası (sağlam MVP'ye giden fazlar)

| Faz | Amaç | Çıktı | "Bitti" kriteri |
|---|---|---|---|
| **0. Demo verisi** | Sentetik şema + veri | `demo_veri.py`, `.env.ornek` | Tablolar + birkaç bin satır; örnek sorular anlamlı sonuç veriyor |
| **1. MVP sağlamlaştırma** | İskeleti demo-dayanıklı yap | smoke test, loglama, net hatalar, README taslağı | 20 örnek soruda çökmeden çalışıyor; güvenlik 15/15 |
| **2. Doğruluk kanıtı** | Dürüst ölçüm | `gold/sorular.json`, ölçüm çıktısı | Execution accuracy ölçüldü + README'ye yazıldı |
| **3. Vitrin cilası** | Gösterilebilir hale getir | tek-sayfa UI, mimari diyagram, demo GIF | Biri klonlayıp 10 dk'da çalıştırıyor |
| **4. Yayın** | LinkedIn + GitHub | LinkedIn yazısı, temiz public repo | Repo public, README cilalı, post hazır |

**Sentetik veri seti (Faz 0):** `magazalar`, `kategoriler`, `urunler`, `satislar` (tarih, adet, birim_fiyat, magaza_id, urun_id) — mevsimsel desen + mağaza farklarıyla, "bugün en çok satan ürün" / "hangi mağazada hangi ürün" sorularına birebir uyar.

---

## 6. Vitrin Teslimatları (projeyi "satan" şeyler)

- **README.md** (en kritik): problem → neden zor (Spider 2.0 ~%10) → çözüm mimarisi → gizlilik vurgusu → güvenlik katmanları → dürüst doğruluk sayıları → kurulum → demo GIF → yol haritası.
- **Mimari diyagram** — veri akışı.
- **Demo video/GIF** (30-60 sn) — canlı demo riskine karşı yedek.
- **Gold set sonuç tablosu** — kategori bazında doğruluk (dürüstlük güven verir).
- **LinkedIn yazısı** — açı-odaklı, taktik (mevcut LinkedIn içerik sistemiyle uyumlu).

---

## 7. Doğrulama — Sistem Gerçekten Sağlam mı?

- **Güvenlik:** `python test_guvenlik.py` → 15/15.
- **Doğruluk:** `python gold_set.py` → execution accuracy + kategori dağılımı.
- **Smoke:** `python test_pipeline.py` → uçtan uca çökmeden.
- **Demo provası:** 20 soru elle, sıcaklık 0 tutarlılık.
- **Tekrar üretilebilirlik:** temiz dizinde `pip install` + `demo_veri.py` + `uvicorn` → 10 dk.

---

## 8. Özet — Üç Cümlede Strateji

1. **Az ama kusursuz** bir MVP kur; demo'da çökecek hiçbir şey bırakma.
2. **Ayrışmayı** gizlilik + güvenlik + dürüst ölçüm + araştırma derinliğinde göster — sıradan demolardan bu ayırır.
3. Her kararı **risk kaydına** göre al; sentetik veri + tekrar üretilebilirlik + yedek demo GIF ile sürprizleri ortadan kaldır.

---

## İlk Somut Adım
Faz 0: `demo_veri.py` (sentetik perakende şeması + tutarlı veri) + `.env.ornek` → `seed_sema.py` ile yükle → `POST /sor`'u demo verisinde çalıştırıp uçtan uca kanıtla. Sonra Faz 1 sağlamlaştırma.
