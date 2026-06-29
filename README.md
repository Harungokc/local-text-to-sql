# 🏪 Şirket Sorgu — Yerel, Gizlilik-Korumalı Text-to-SQL Ajanı

> Türkçe iş sorusu → güvenli SQL → çalıştır → **doğrulanmış** Türkçe rapor.
> **Veri makineden hiç çıkmaz** — tüm yapay zekâ yerel modelle (Ollama) çalışır.

![durum](https://img.shields.io/badge/durum-MVP%20(Faz%201--2)-2a9d8f)
![python](https://img.shields.io/badge/python-3.11%2B-0f4c5c)
![db](https://img.shields.io/badge/veritaban%C4%B1-PostgreSQL-0f4c5c)
![model](https://img.shields.io/badge/model-Ollama%20%2F%20yerel-2a9d8f)
![lisans](https://img.shields.io/badge/veri-d%C4%B1%C5%9Far%C4%B1%20%C3%A7%C4%B1kmaz-c1440e)

---

## Bu nedir?

Bir şirketin kendi veritabanına **doğal Türkçe ile** soru sormasını sağlayan, **tamamen yerel çalışan** bir text-to-SQL yapay zekâ ajanı. Kullanıcı "en çok ciro yapan 5 ürün hangisi?" diye sorar; sistem soruyu güvenli bir SQL'e çevirir, salt-okunur çalıştırır, sonucu işler ve doğrulanmış bir Türkçe rapor döndürür.

**Neden önemli?** Kurumsal text-to-SQL hâlâ çözülmemiş zor bir problemdir (Spider 2.0 benchmark'ında GPT-4o bile yalnızca ~%10). Bu projede soruna **mühendislik disipliniyle** ve **veriyi hiç dışarı çıkarmadan** yaklaşıldı.

> 📄 Detaylı tasarım dokümanı: [`docs/sirket_sorgu_tanitim.pdf`](docs/sirket_sorgu_tanitim.pdf)

---

## Öne çıkanlar

- 🔒 **%100 yerel / gizlilik-korumalı** — soru, şema ve veri bilgisayardan çıkmaz (KVKK/GDPR dostu).
- 🛡️ **Çok-katmanlı güvenlik** — salt-okunur kullanıcı + read-only transaction + AST denetimi + timeout.
- 🧮 **Halüsinasyonsuz rapor** — sayıyı **pandas** hesaplar, LLM yalnızca yorumlar.
- ✅ **Dürüst doğruluk ölçümü** — kendi gold set'i + execution accuracy (uydurma sayı yok).
- 🔎 **Denetim izi** — her kontrol katmanının kararı şeffaf görünür.
- 🌐 **Basit web arayüzü** + terminal CLI + REST API.

---

## Ekran görüntüsü

`web/` arayüzünde soru sor, anında SQL + sonuç tablosu + özet + Excel/CSV indir:

> _(Ekran görüntüsünü buraya ekleyin: `docs/ekran_goruntusu.png`)_

---

## Mimari

Soru, her adımı denetlenen bir hattan geçer:

```
Türkçe Soru
  → K0  Eksik-kavram guard'ı   (müşteri/kâr/stok şemada yoksa → "bu veri yok")
  → Şema linkleme + RAG few-shot (benzer örnekler — ChromaDB)
  → SQL ÜRET                   (yerel model, sıcaklık 0 = determinizm)
  → K1  GÜVENLİK               (yalnızca-SELECT)
  → K2  DOĞRULUK               (şema grounding + EXPLAIN dry-run)
  → ÇALIŞTIR                   (read-only kullanıcı + transaction + timeout)
       ↳ hata → self-correction (hatayı modele geri besle, maks 2 tur)
  → K3  ANALİZ DOĞRULAMA       (türetilmiş metrik / "pay" güvenliği)
  → RAPOR                      (pandas hesaplar, LLM yalnızca yorumlar)
  → SADAKAT KAPISI             (anlatımdaki her sayı/isim olgularda var mı?)
  → Doğrulanmış Türkçe Rapor + Denetim İzi
```

**Felsefe:** Önce ucuz **deterministik** kontroller, en son pahalı LLM. *Kendinden emin yanlış cevap vermektense "emin değilim / bu veri yok" demek daha sağlamdır.*

---

## Hızlı Başlangıç

### Gereksinimler
- Python 3.11+
- [PostgreSQL](https://www.postgresql.org/)
- [Ollama](https://ollama.com) (yerel model çalıştırıcı)

### Kurulum
```bash
# 1) Klonla
git clone <repo-linki> && cd Local-sirket-sorgu

# 2) Sanal ortam + bağımlılıklar
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 3) Yerel modeli indir (Ollama açık olmalı)
ollama pull qwen2.5-coder:3b

# 4) Demo veritabanını kur (sentetik perakende verisi, 6511 satış)
createdb sirket_demo
export DATABASE_URL="postgresql://$USER@localhost:5432/sirket_demo"
.venv/bin/python demo_veri.py

# 5) Few-shot örneklerini ChromaDB'ye yükle (gold/few_shot.json'dan)
export SORGU_DATABASE_URL="postgresql://$USER@localhost:5432/sirket_demo"
.venv/bin/python seed_sema.py
```

### Çalıştırma

**Web arayüzü:**
```bash
export SORGU_DATABASE_URL="postgresql://$USER@localhost:5432/sirket_demo"
export YEREL_MODEL="qwen2.5-coder:3b"
.venv/bin/python -m uvicorn api:app --host 127.0.0.1 --port 9000
# → tarayıcıda http://127.0.0.1:9000
```

**Terminal:**
```bash
.venv/bin/python sor.py                                  # etkileşimli
.venv/bin/python sor.py "en çok ciro yapan 5 ürün?"      # tek soru
```

**REST API:**
```bash
curl -X POST http://127.0.0.1:9000/sor \
  -H "Content-Type: application/json" \
  -d '{"soru":"şehir bazında toplam satış adedi nedir?"}'
```

> ⚠️ **Üretimde:** uygulama **salt-okunur** bir DB kullanıcısı kullanmalı (`SORGU_DATABASE_URL`). Yazma yetkisi yalnızca veri kurulumunda gerekir.

---

## Kendi Veritabanınla Kullanmak

Sistem belirli bir şemaya bağlı değildir — şemayı **runtime'da** `information_schema`'dan okur. Kendi PostgreSQL veritabanını bağlamak için:

1. Salt-okunur bir kullanıcı oluştur (`GRANT SELECT`).
2. `SORGU_DATABASE_URL`'i kendi veritabanına yönlendir.
3. (Önerilir) `gold/few_shot.json`'a kendi şemana uygun birkaç **soru→SQL örneği** ekle — doğruluğu belirgin artırır.

### Hangi veritabanları?
PostgreSQL ile geliştirildi (güçlü izin modeli + `EXPLAIN` + yaygınlık). Mimari veritabanı-agnostiktir; **MySQL/MariaDB, SQLite, DuckDB, SQL Server** ile de uygulanabilir — yalnızca SQL diyalekti ve `EXPLAIN` söz dizimi değişir, kontrol/rapor mantığı aynı kalır.

---

## Model Seçimi: Hangisi Ne Kadar Yeterli?

| Model | Boyut | 8GB dizüstüde | Rol |
|---|---|---|---|
| `qwen2.5-coder:3b` | 1.9 GB | ✅ rahat | Yerel geliştirme + günlük raporlama |
| `qwen2.5-coder:7b` | 4.7 GB | ❌ (8GB'ı zorlar) | Kiralık GPU |
| `Qwen2.5-Coder:32B` | ~18–24 GB | ❌ | GPU'da ileri analitik |

**Ölçülen doğruluk (3B, dizüstü):**

| Soru sınıfı | Doğruluk |
|---|---|
| Temel/orta (agregasyon, filtre, 2–3 join, oran) | **%87–95** |
| İleri analitik (pencere fn., top-N-per-group, percentile, nested) | **~%20** |

3B; **pencere fonksiyonu / grup-başına-top-N / percentile** gibi ileri analitiği çözemez (kavramsal sınır). Bu sorular için 7B/32B (GPU) gerekir. Geçişte yalnızca `YEREL_MODEL` + `VLLM_BASE_URL` değişir, kod aynı kalır.

> Tüm bu sayılar gerçekten ölçüldü (`gold_set.py`, stres testleri) — uydurma yok.

---

## Güvenlik Katmanları

| Katman | Koruma |
|---|---|
| Salt-okunur DB kullanıcısı | Yazma/silme'yi **fiziksel olarak** imkânsız kılar |
| Read-only transaction | İkinci savunma hattı |
| AST denetimi (sqlglot) | Yalnızca tek `SELECT`; INSERT/UPDATE/DELETE/DDL reddedilir |
| `EXPLAIN` dry-run | Çalıştırmadan şema/tip uyumunu doğrular |
| Timeout + satır limiti | Kaçak sorgu koruması |

Test: `python test_guvenlik.py` → **15/15**.

---

## Proje Yapısı

```
runner.py          Orkestratör (uçtan uca akış)
sema.py            Şema okuma + linkleme + değer enjeksiyonu
retrieval.py       Few-shot örnek deposu (ChromaDB, yerel)
llm.py             Yerel LLM sarmalayıcı (OpenAI-uyumlu: Ollama/vLLM)
sql_guvenlik.py    K1 — güvenlik (SELECT-only)
sql_kontrol.py     K2 — doğruluk (grounding + EXPLAIN)
analiz_kontrol.py  K3 — türetilmiş metrik denetimi + sadakat
on_kontrol.py      K0 — eksik-kavram guard'ı
rapor.py           Rapor (pandas hesaplar, LLM yorumlar)
db_sorgu.py        Read-only PostgreSQL (asyncpg)
api.py             FastAPI servisi + web arayüzü
sor.py             Terminal CLI
web/index.html     Tek-sayfa web arayüzü
demo_veri.py       Sentetik demo veritabanı
gold/              Gold set + few-shot örnekleri
docs/              Tanıtım PDF'i (+ kaynak .typ)
```

---

## Test & Doğruluk Kanıtı

```bash
python test_guvenlik.py     # güvenlik (K1)         → 15/15
python gold_set.py          # execution accuracy    → 7/8
python metrik_test.py       # türetilmiş metrik (K3) → 3/3
```

---

## Yol Haritası

- **Faz 3:** Koşullu LLM-critic · güven skoru ("emin değilim") · intent-based retrieval · kolon budama (büyük şema)
- **Faz 4:** Semantik metrik katmanı · GPU'da 32B · grafik üretimi · çoklu kullanıcı

---

## Notlar

- Demo verisi **sentetiktir**; gerçek şirket verisi içermez.
- Bu, kurumsal text-to-SQL'e mühendislik yaklaşımını gösteren bir **vitrin/MVP** projesidir.
- Sistem bir **analist asistanıdır**, otomatik karar verici değil — kritik kararlarda SQL ve sonuç doğrulanmalıdır.

---

*Yapımcı: Harun Gökçe · İletişim/LinkedIn: ‹profil-linki›*
