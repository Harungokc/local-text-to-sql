# SQL Kontrol/Doğrulama Ajanı — Araştırma + Mimari Tasarım

> Amaç: Üretilen SQL, çalıştırılmadan önce (ve sonra) "doğru mu, soruyu gerçekten cevaplıyor mu, her şey yerli yerinde mi" diye denetleyen bir katman. "Sessizce yanlış SQL" (R1) problemine doğrudan saldırır.
> Tarih: 2026-06-24 · Kaynak: 8 doğrulanmış akademik bulgu (SQLens, SQLCritic, MAC-SQL, RSL-SQL, CHESS, DIN-SQL, CHASE-SQL + sqlglot/PostgreSQL docs).

---

## 1. Araştırmanın En Kritik 5 Bulgusu

1. **Katmanlı/hibrit tasarım kazanır.** Önce ucuz **deterministik** kontroller, en son pahalı **LLM-critic**. Kanıt: SQLens'in DB+LLM hibrit dedektörü, **saf LLM self-evaluation'ı %25.78 F1 geçti.** → Küçük modelde (Qwen 7B) LLM-as-judge **tek başına yetersiz**; mutlaka deterministik sinyallerle desteklenmeli.

2. **Temel mekanizma = üret→doğrula→düzelt döngüsü** (max N tur). MAC-SQL Refiner, RSL-SQL, CHESS hep bunu yapar: sözdizimi → çalıştırılabilirlik → boş-olmayan sonuç sırasıyla diagnoz et, hatayı LLM'e geri besle. (Bizde self-correction olarak zaten var — onu güçlendireceğiz.)

3. **Doğrulama AYRI bir modül olmalı.** MAC-SQL'de Refiner ayrı ajan, DIN-SQL'de self-correction ayrı modül. → Bizde `sql_kontrol.py` olarak bağımsız yazılacak.

4. **"Sessizce yanlış"ı yakalamak için clause-bazlı semantik hizalama gerekir** (SQLCritic): her clause (SELECT/WHERE/GROUP BY) sorunun istediğiyle uyuşuyor mu? Bu, sözdizimi/EXPLAIN'in **yakalayamadığı tek katman** — ve asıl değerli olan bu.

5. **Çoklu aday uyuşmazlığı = güven sinyali** (RSL-SQL): iki adayı (tam şema vs sade şema) çalıştır, sonuçlar aynıysa **yüksek güven**, farklıysa **düşük güven → "emin değilim" + kullanıcıya sor.** CHASE-SQL'in fine-tuned selector'ı ağır; RSL-SQL'in eğitimsiz hali bize uygun.

**Küçük model uyarısı:** LLM-critic'in 7B'de katkısı mütevazı (CodeS-7B'de SQLCritic +2.28pp). → Ağırlığı deterministik katmanlara ver, LLM-critic'i **koşullu** ve **muhafazakâr** kullan.

---

## 2. Önerilen Mimari — 3 Katmanlı Kontrol Ajanı

Akış: **SQL üretildi → [KONTROL AJANI] → çalıştır → [çalıştırma sonrası kontrol] → rapor**

```
                    Üretilen SQL adayı
                           │
   ┌───────────────────────────────────────────────────┐
   │  KATMAN 1 — DETERMİNİSTİK (LLM YOK, milisaniye)     │
   │  1a. Güvenlik: sadece-SELECT (mevcut sql_guvenlik)  │
   │  1b. Sözdizimi: sqlglot parse (ParseError?)         │
   │  1c. Şema grounding: kullanılan tablo/kolonlar       │
   │      sema.py'deki GERÇEK şemada var mı? (uydurma?)  │
   │  1d. EXPLAIN dry-run: PostgreSQL çalıştırMADAN plan  │
   │      üretebiliyor mu? (şema/tip %100 garanti)        │
   └───────────────────────────────────────────────────┘
            │ geçti                       │ kaldı
            ▼                             ▼
   ┌──────────────────────────┐    self-correction
   │ KATMAN 2 — ÇALIŞTIRMA      │    (hatayı LLM'e besle,
   │ db_sorgu ile çalıştır,     │     max 2 tur) → baştan
   │ sinyalleri topla:          │
   │  • boş sonuç?              │
   │  • hepsi NULL/0?          │
   │  • anormal satır sayısı?   │
   │  • runtime hata?          │
   └──────────────────────────┘
            │
            ▼
   ┌───────────────────────────────────────────────────┐
   │  KATMAN 3 — LLM-CRITIC (KOŞULLU, pahalı)            │
   │  Sadece şu durumda tetiklenir:                      │
   │   - Katman 1-2 temiz AMA risk sinyali var           │
   │     (boş/şüpheli sonuç, belirsiz soru) VEYA          │
   │   - güven skoru düşük                                │
   │  Clause-bazlı kontrol (Türkçe prompt):              │
   │   "SELECT kolonları soruyu cevaplıyor mu?           │
   │    WHERE filtreleri doğru mu?                        │
   │    GROUP BY/agregasyon mantığı yerinde mi?"          │
   └───────────────────────────────────────────────────┘
            │
            ▼
   GÜVEN SKORU + KARAR: kabul / düzelt / "emin değilim"+sor
```

---

## 3. Katman Katman — Ne Kontrol Edilir

### Katman 1 — Deterministik (her zaman çalışır, LLM yok, ~ms)
| Kontrol | Nasıl | Yakaladığı hata |
|---|---|---|
| Güvenlik | mevcut `sql_guvenlik.dogrula_ve_hazirla` | yazma/DDL/injection |
| Sözdizimi | `sqlglot.parse_one` → ParseError | bozuk SQL |
| **Şema grounding** | `find_all(exp.Table/Column)` → `sema.py` gerçek şemayla karşılaştır | **uydurma tablo/kolon** |
| **EXPLAIN dry-run** | `EXPLAIN <sql>` (ANALYZE'sız, çalıştırmaz) | şemaya oturmayan ad/tip, yan etkisiz |

> EXPLAIN, gerçek veriyi çekmeden tablo/kolon varlığını ve tip uyumunu **%100 garanti eder** — read-only pipeline için ideal, yan etkisiz.

### Katman 2 — Çalıştırma sinyalleri (sonuç geldikten sonra)
- **Boş sonuç** → şüpheli (yanlış filtre olabilir) → güven düşür.
- **Tümü NULL / 0** → anormal → güven düşür.
- **Anormal satır sayısı** (0 ya da limit'e dayanmış) → şüpheli.
- **Runtime hata** → self-correction'a git.

### Katman 3 — LLM-critic (KOŞULLU — sadece gerekince)
- **Ne zaman:** Katman 1-2 temiz ama risk sinyali var (boş/şüpheli sonuç) **veya** güven düşük. Her sorguda DEĞİL (maliyet).
- **Ne yapar:** Clause-bazlı Türkçe denetim — SELECT/WHERE/GROUP BY soruyla uyuşuyor mu?
- **Çıktı:** `{uygun: true/false, gerekçe, varsa düzeltme önerisi}`.
- **Muhafazakâr:** Sadece yüksek-güvenli düzeltme yap (7B'de yanlış-pozitif regresyon riskine karşı).

### Güven Skoru (opsiyonel, Faz sonrası)
- **RSL-SQL iki-aday:** Tam şema + sade şema ile iki SQL üret, ikisini de çalıştır. Sonuç aynı → yüksek güven. Farklı → düşük güven → kullanıcıya **"emin değilim, şunu mu demek istediniz?"** (clarification).
- Maliyet: +1 LLM çağrısı. Faz 1'de kapalı, Faz 3'te aç (vitrin için etkileyici "güven skoru" göstergesi).

---

## 4. Karar Mantığı (red / kabul / düzelt / sor)

```
Katman 1 KALDI        → düzelt (self-correction) → max 2 tur → hâlâ kaldıysa: "üretemedim"
Katman 1 GEÇTİ
  → Katman 2 çalıştır
     → runtime hata    → düzelt (self-correction)
     → boş/şüpheli     → Katman 3 (LLM-critic) → düzelt veya "emin değilim"
     → temiz sonuç     → güven yüksek → KABUL → rapor
Güven düşük her durumda → kullanıcıya güven skoru + "emin değilim" notu göster
```

> İlke: **Yanlış cevabı kendinden emin vermektense, "emin değilim" demek daha sağlam.** Vitrin için de güven verir.

---

## 5. Bizim Koda Entegrasyon (somut)

**Yeni dosya: `sql_kontrol.py`** (bağımsız modül)
```python
# Katman 1 (deterministik)
def statik_kontrol(sql, tum_ddl) -> KontrolSonucu        # sqlglot + şema grounding
async def explain_kontrol(sql) -> KontrolSonucu          # EXPLAIN dry-run

# Katman 2 (çalıştırma sinyalleri)
def sonuc_sinyalleri(satirlar) -> list[str]              # boş/NULL/anormal

# Katman 3 (koşullu LLM-critic)
def llm_critic(soru, sql, sema_metni, model) -> Karar     # clause-bazlı, Türkçe

# Birleştirici
def guven_skoru(sinyaller, critic) -> float
```

**`runner.py` değişimi** (mevcut pipeline'a ekleme):
```
üret → [statik_kontrol + explain_kontrol]  ← çalıştırMADAN ÖNCE (Katman 1)
      → kaldıysa self-correction
çalıştır → [sonuc_sinyalleri]              ← çalıştırma sonrası (Katman 2)
      → risk varsa [llm_critic]            ← koşullu (Katman 3)
      → guven_skoru → kabul/düzelt/sor
rapor (+ güven skoru yanıta eklenir)
```

**`prompts/sql_critic.md`** (yeni) — clause-bazlı Türkçe denetim promptu.

**Mevcut dosyalara dokunmadan:** `sql_guvenlik.py`, `db_sorgu.py`, `sema.py` aynen kullanılır (kontrol ajanı onları çağırır).

---

## 6. Yerel Model / Maliyet Dengesi (kritik)

| Katman | Maliyet | Sıklık |
|---|---|---|
| 1 (deterministik) | ~0 (LLM yok, ms) | **Her sorgu** |
| 2 (çalıştırma) | ~0 (zaten çalıştırıyoruz) | **Her sorgu** |
| 3 (LLM-critic) | 1 LLM çağrısı | **Sadece risk sinyalinde** (koşullu) |
| Güven (iki-aday) | +1 LLM çağrısı | Opsiyonel, Faz 3 |

> Deterministik kapılar bedava ve hataların çoğunu yakalar (uydurma kolon, bozuk SQL, şemaya oturmama). LLM-critic'i sadece gerçekten gerektiğinde çağırarak yerel modelde gecikme/maliyeti minimumda tutuyoruz.

---

## 7. Fazlama (MVP'ye uygun)

- **Faz 1 (şimdi):** Katman 1 (statik + EXPLAIN) + Katman 2 (sinyaller). Deterministik, bedava, en yüksek getiri. Self-correction tetikleyicisini bu sinyallere bağla.
- **Faz 3:** Katman 3 (koşullu LLM-critic, clause-bazlı) + güven skoru (iki-aday) + kullanıcıya "emin değilim".
- **Gelecek işi:** CHASE-SQL tarzı eğitilmiş selector (vitrin için gereksiz, anlatılır).

---

## 8. Doğrulama
- Kontrol ajanının kendi testi: uydurma kolonlu SQL, şemaya oturmayan SQL, mantık hatası olan ama çalışan SQL → her biri doğru sınıflanmalı.
- Gold set ile A/B: kontrol ajanı **AÇIK vs KAPALI** execution accuracy farkı ölçülür (vitrin için somut kanıt: "kontrol ajanı doğruluğu %X→%Y yaptı").

---

## Kaynaklar
SQLens (arXiv 2506.04494) · SQLCritic (arXiv 2503.07996) · MAC-SQL (2312.11242) · RSL-SQL (2411.00073) · CHESS (2405.16755) · DIN-SQL (2304.11015) · CHASE-SQL (2410.01943) · sqlglot (github.com/tobymao/sqlglot) · PostgreSQL EXPLAIN docs
