# Text-to-SQL — Kaynak Haritası & Üretim Dersleri (GitHub Dışı)

> 3. araştırma turu. Odak: GitHub dışında nereye bakılmalı + gerçek üretim sistemlerinden dersler.
> Tarih: 2026-06-24 · 9 doğrulanmış iddia (3 oylu adversaryal doğrulama) + ek kaynak listesi.

---

## 0. En Çarpıcı Bulgu (önce bunu oku)

**Kurumsal/gerçek-dünya text-to-SQL hâlâ "çözülmüş" bir problem DEĞİL.**
- Basit benchmark'larda (Spider 1.0) SOTA ~%86-91.
- **Gerçek kurumsal şemalarda (Spider 2.0 — 1000+ kolonlu DB'ler, 100+ satırlık SQL): GPT-4o sadece ~%10, o1-preview ~%21** (geç-2024/erken-2025). 2026 ortası agentic sistemler bunu yükseltti ama uçurum gerçek.
- BIRD'de en iyi sistem %81.95, insan %92.96 — yani ~11 puan açık hâlâ var.

**Sonuç:** Model seçimi (yerel/bulut) tek başına belirleyici değil. **Doğruluğu MİMARİ belirliyor** — retrieval, şema linkleme, ajan ayrıştırması, semantik katman. Bu, senin projenin neden "Vanna+tek model" değil de custom pipeline (şema linkleme + few-shot + self-correction) olarak tasarlandığını birinci-elden doğruluyor.

---

## 1. Otorite Kaynak Haritası (GitHub dışında nereye bakılmalı)

### A) Resmi Benchmark & Liderlik Tabloları (ilk durak)
| Kaynak | Ne için | URL |
|---|---|---|
| **BIRD** | Gerçekçi/gürültülü kurumsal veri + harici bilgi gerektiren benchmark; 12.751 soru, 95 büyük DB, 37+ alan. Canlı leaderboard. | bird-bench.github.io |
| **Spider** | Cross-domain genelleme (train/test şemaları ayrık); 10.181 soru, 200 DB. Metrik tanımlarının kaynağı. | yale-lily.github.io/spider |
| **Spider 2.0** | **Gerçek kurumsal iş akışları** (632 görev, BigQuery/Snowflake, 1000+ kolon). Senin senaryona en yakın zorluk seviyesi. | spider2-sql.github.io |
| **llm-stats / Papers With Code** | Model bazlı güncel BIRD/Spider skorları, hızlı kıyas | llm-stats.com/benchmarks/bird-sql |

### B) Akademik (yöntem aileleri için tek otorite)
- **LLM-Text-to-SQL Survey** (arXiv 2406.08426, Hong et al.) — **GitHub repo listesi yerine yöntemleri anlamak için bunu oku.** Yöntemleri ikiye ayırır: In-Context Learning (Vanilla, Decomposition→DIN-SQL/MAC-SQL/CHESS, Prompt Optimization→DAIL-SQL, Reasoning→CoT/agentic, Execution Refinement→Self-Debugging/LEVER) ve Fine-Tuning.
- **arXiv cs.CL + cs.DB**, **ACL Anthology**, **VLDB / SIGMOD / NeurIPS / EMNLP** — survey'in atıf ağı üzerinden taranır.
- **Hugging Face** — modeller, datasetler, model kartlarındaki benchmark skorları.

### C) Değerlendirme araçları
- **taoyds/test-suite-sql-eval** (GitHub, ama referans araç) — Test Suite Accuracy resmi implementasyonu.

---

## 2. Gerçek Üretim Vaka Çalışmaları (en değerli kısım)

### Uber — QueryGPT (multi-agent ayrıştırma)
Doğrudan kopyalanabilir mimari şablon:
1. **Intent Agent** — soruyu iş alanlarına/workspace'lere eşler (Mobility, Ads… 12 workspace).
2. **Table Agent** — doğru tabloları seçer, **kullanıcıya onaylatır** (human-in-the-loop).
3. **Column Prune Agent** — LLM ile alakasız kolonları **budar** → token/maliyet/gecikme düşer, context limitine sığar.
- Altyapı: LLM + vektör DB + benzerlik araması. Alan bilgisi "Workspaces" (alana özel SQL örnekleri + tablo koleksiyonları) olarak organize.
- **Senin projene:** Şeman büyürse kolon budama özellikle kritik — yerel 7B/32B'nin sınırlı context'i için. `sema.py`'ye eklenecek doğal genişleme.

### Pinterest — ölçülmüş kazanımlar (en güçlü dersler)
- Tablolara **dokümantasyon ekleyip vektör aramaya** koyunca: tablo arama isabeti **%40 → %90**.
- RAG-tabanlı tablo retrieval + olgunlaşma: ilk-deneme kabul **%20 → %40+**.
- **Niyet-tabanlı (intent-based) retrieval** (en yenilikçi fikir): 100.000+ tabloda anahtar-kelime/özet yetmedi → **geçmiş SQL sorgularını LLM ile doğal dile çevirip** (özet + analitik sorular + detay) vektörleştirdiler.
- **Senin projene (KRİTİK):** Şirketinde zaten **birikmiş geçmiş SQL sorguları en değerli alan-bilgisi kaynağıdır.** Bunları NL'e çevirip few-shot deposuna koymak, salt şema dokümantasyonundan çok daha iyi retrieval verir. Gizlilik-korumalı yerel kurulum için ideal — veri hiç çıkmadan domain bilgisi elde edilir. Bu, `retrieval.py`'nin doğal Faz 3 yükseltmesi.

### Diğer (kaynak listesinde, derinlemesine doğrulanmadı ama okumaya değer)
- **Swiggy — Hermes** (bytes.swiggy.com) — text-to-SQL üretim sistemi.
- **ZenML LLMOps DB** — çok-ajanlı text-to-SQL üretim mimarisi vaka derlemesi.

---

## 3. Topluluk & Pratik Deneyim Kaynakları
- **Hacker News** tartışmaları: news.ycombinator.com/item?id=45733525 ve 39261486 (yerel model + text-to-SQL pratik deneyimler).
- **localaimaster.com/blog/talk-to-your-database-local-llm** — yerel LLM ile DB konuşma rehberi.
- Takip edilecekler (genel öneri): **r/LocalLLaMA** (yerel model pratiği), **r/dataengineering** (analitik/üretim), HF blog.
> Not: Bu turda topluluk kaynakları "doğrulanmış iddia"ya dönüşmedi; yukarıdakiler kaynak listesinden, başlangıç noktası olarak.

---

## 4. Değerlendirme & Test (senin gold_set.py'ni doğruluyor)

**Metrik taksonomisi:**
- **Exact Set Match** — cümle yapısı karşılaştırması (yanıltıcı: aynı sonucu veren farklı doğru SQL'leri kaçırır).
- **Execution Accuracy (EX)** — sonuç eşitliği (senin `gold_set.py`'nin kullandığı — doğru seçim).
- **Test Suite Accuracy** — Kasım 2020'den beri resmi metrik; dağıtılmış test DB'leriyle yanlış-pozitifleri eler (Faz 3 yükseltmesi).
- **BIRD: Valid Efficiency Score** — doğruluk + sorgu verimliliği.

**Çok önemli uyarı — benchmark'lar bile "bozuk":** Bağımsız akademik çalışma (CIDR 2026, UIUC) gösterdi ki **BIRD Mini-Dev'in %52.8'i, Spider 2.0-Snow'un ~%66'sı anotasyon hatası içeriyor** (yanlış gold SQL / belirsiz soru). Düzeltilince model sıralamaları 3 pozisyon kaydı.
- **Senin projene:** Dış skorlara körü körüne güvenme. **Kendi şemanda titiz, çift-kontrollü bir gold set** kur ve EX ile ölç. `gold_set.py` tam da bunu yapıyor — doğru yoldasın. Gold set'i hazırlarken her soru-SQL çiftini iki kez kontrol et.

---

## 5. Semantik Katman & BI Ürünlerinden Tasarım Dersleri

**Ortak prensip:** Metrik/iş tanımlarını **LLM'den ÖNCE sabitle** → serbest SQL üretimini kısıtla → hata azalt.
- **dbt Semantic Layer, Cube, MetricFlow, Malloy, LookML** — metrikleri (ciro, aktif kullanıcı vb.) önceden tanımlar; LLM bunları çağırır, sıfırdan SQL uydurmaz.
- **ThoughtSpot Spotter** — "governed semantik katman + agentic + human-in-the-loop doğrulama" (pazarlama dili, ama tasarım dersi geçerli).
- **WrenAI** — semantik katmanın text-to-SQL güvenilirliğine etkisini blog dizisinde işliyor (halüsinasyon azaltma).
- **Senin projene:** Faz 3/4'te, sık sorulan iş metriklerini (örn. "ciro", "en çok satan") sabit, onaylanmış SQL parçalarına bağlayan hafif bir "metrik sözlüğü" eklemek doğruluğu belirgin artırır. Bu, few-shot'un üstünde bir güvenilirlik katmanı.

---

## 6. En Güncel (2025-2026) Yönelimler
- **Agentic text-to-SQL** baskın trend: tek-atış üretim yerine niyet→tablo→kolon→üret→çalıştır→düzelt ajan zinciri (Uber/CHASE/RSL-SQL hep bu yönde).
- **Reasoning modelleri (o1 / DeepSeek-R1 tarzı)** text-to-SQL'i iyileştiriyor (Spider 2.0'da o1-preview, GPT-4o'nun 2 katı). Yerelde R1-distill modelleri ileride değerlendirilebilir.
- **Spider 2.0** yeni zorluk standardı — gerçek kurumsal karmaşıklık.

---

## 7. Bu Turun Projeye Net Katkıları (özet)

| Ders | Nereye uygulanır |
|---|---|
| Kolon budama (Uber Column Prune) | `sema.py` — büyük şemada context daraltma |
| **Geçmiş SQL'leri NL'e çevirip retrieval'a koy** (Pinterest intent-based) | `retrieval.py` Faz 3 — en yüksek getirili tek iyileştirme |
| Tablo dokümantasyonu ekle (%40→%90 isabet) | `sema.py` — kolon yorumları + tablo açıklamaları |
| Kendi gold set'in + Execution Accuracy | `gold_set.py` (zaten var) — çift-kontrol şart |
| Test Suite Accuracy | `gold_set.py` Faz 3 yükseltmesi |
| Metrik sözlüğü (semantik katman) | Faz 4 — iş metriklerini sabitle |
| Table Agent + kullanıcı onayı | Faz 3/4 — human-in-the-loop tablo seçimi |

---

## 8. Sonraki Araştırma Yönleri (bu turda açık kalanlar)
- Yerel/açık reasoning modelleri (DeepSeek-R1 distill, Qwen-reasoning) PostgreSQL'de hangi EX seviyesine ulaşıyor, kapalı API'lere kıyasla açık ne kadar?
- Vanna/WrenAI/Dataherald'ın RAG + training-data mimarisi Pinterest/Uber'e kıyasla yerel kurulum için ne sunuyor; dbt/Cube/MetricFlow entegrasyonunun ölçülebilir doğruluk katkısı.
- Sentetik test verisi / gold set üretimi için açık çerçeveler; CIDR 2026'nın otomatik anotasyon-hata tespiti (SAR-Agent) kendi gold set kalite kontrolüne nasıl uyarlanır.

---

## Doğrulama Notları (caveat)
- Pinterest %40-analist / #1-ajan / 10x / %35-hız rakamları **şirket öz-raporu** (bağımsız doğrulanmadı; %35 gözlemsel).
- ThoughtSpot iddiaları **satıcı pazarlaması** — bağımsız halüsinasyon/doğruluk ölçümü yok, sadece tasarım dersi.
- "Spider 2.0'da %10/%21" geç-2024/erken-2025 SOTA'sına ait; 2026 leaderboard agentic sistemlerle daha yüksek.
- LinkedIn/Shopify/Airbnb/Nubank/Databricks Genie/Snowflake Cortex Analyst bu turda doğrulanmış iddiaya dönüşmedi (kapsam sınırı).

---

## Kaynaklar (tam liste)
**Benchmark/akademik:** bird-bench.github.io · yale-lily.github.io/spider · spider2-sql.github.io · arXiv 2411.07763 (Spider 2.0) · arXiv 2406.08426 (Survey) · vldb.org/cidrdb/papers/2026/p5-jin.pdf (CIDR 2026 — benchmark hataları) · arXiv 2502.00675 · llm-stats.com/benchmarks/bird-sql · taoyds/test-suite-sql-eval
**Üretim blogları:** uber.com/blog/query-gpt · pinterest-engineering (how-we-built + unified-context-intent-embeddings) · bytes.swiggy.com/hermes · zenml.io/llmops-database
**Semantik katman/ürün:** docs.getdbt.com/blog/semantic-layer-vs-text-to-sql-2026 · wrenai blog (semantic layer + hallucination) · thoughtspot.com/product/agents · typedef.ai (MetricFlow vs Snowflake vs Databricks)
**Topluluk:** news.ycombinator.com (45733525, 39261486) · localaimaster.com/blog/talk-to-your-database-local-llm
