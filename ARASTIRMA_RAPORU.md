# Yerel Text-to-SQL Agent — Kapsamlı Kıyas Araştırması

> Hedef: MacBook M1 8GB RAM (gerekirse sunucu) · PostgreSQL · veri dışarı çıkmayacak (gizlilik-korumalı) · şirket içi veri analizi + SQL üretimi + otomatik rapor.
> Tarih: 2026-06-24 · 29 kaynak, 24 doğrulanmış iddia (3 oylu adversaryal doğrulama).

---

## 0. En Önemli Sonuç (TL;DR)

1. **Mimari = Framework + Yerel Inference + Dedike Model.** En sağlam yapı: açık kaynak bir orchestration framework (**Vanna**, MIT, ~23.7k ⭐) + yerel çalıştırıcı (**Ollama** veya **MLX**) + text-to-SQL'e özel bir açık model. Vanna ve WrenAI ikisi de PostgreSQL'i ve Ollama üzerinden yerel modelleri **doğrudan** destekler → veri ve sorgular bilgisayardan/sunucudan dışarı çıkmaz.

2. **8GB M1 ciddi darboğaz.** 4-bit kuantize 7B modeller (örn. **OmniSQL-7B**, **DuckDB-NSQL Q4_0 = 3.8GB**) teknik olarak çalışır ama *dar* — PostgreSQL + uygulama + model aynı anda çalışırken bellek baskısı/swap riski var. "Çalışır" evet, "rahat" hayır.

3. **İki gerçekçi yol var:**
   - **A) Hafif yerel:** 1.5B sınıfı özel-eğitilmiş model (SLM-SQL: 1.5B → BIRD-dev %67) — 8GB'de rahat döner ama özel fine-tune + inference-time düzeltme gerektirir.
   - **B) Kaliteli sunucu:** 32B (BASE-SQL → BIRD %67.5 / Spider %88.9) veya 70B model kiralık GPU'da — en yüksek doğruluk, ama 8GB laptopa **sığmaz**.

4. **Doğruluğu asıl artıran model değil, mimari:** şema linkleme + few-shot + çoklu aday üretip seçme (CHASE-SQL) + çok-turlu self-correction (RSL-SQL). Aynı küçük modelle bu teknikler doğruluğu büyük oranda yükseltir.

---

## 1. Açık Kaynak Framework Karşılaştırması

| Framework | Lisans | ⭐ (yaklaşık) | PostgreSQL | Yerel LLM | Mimari | Güçlü Yön | Zayıf / Dikkat |
|---|---|---|---|---|---|---|---|
| **Vanna** | MIT | ~23.7k | ✅ (`connect_to_postgres`) | ✅ Ollama | RAG-tabanlı agentic retrieval; başarılı sorgulardan öğrenir | En popüler, hafif, esnek; sadece şema/metadata indeksler (gerçek veri değil) | Saf kütüphane — UI/yönetişimi sen kurarsın |
| **WrenAI** | açık kaynak | büyük | ✅ (özel kılavuz) | ✅ Ollama | Semantik katman (MDL) + yönetişim (RLS/CLS) + GenBI | İş tanımları/metrik/ilişki tanımlama; 22+ veri kaynağı; hazır UI | Daha ağır kurulum; "GenBI" kısmen pazarlama |
| **Dataherald** | Apache 2.0 | ~3.6k | ✅ | ✅ | Kurumsal NL-to-SQL + RAG | Enterprise odaklı, fine-tune destekli | Topluluk ivmesi Vanna/WrenAI'dan düşük |
| **PremSQL** | MIT | orta | ✅ | ✅ Ollama + **Apple MLX** + HF | Tam-yerel pipeline + kendi SLM'i (Prem-1B-SQL) | **M1 için MLX native** — bu donanıma en uygun; "veriyi yerelde tut" tasarım amacı | Daha küçük topluluk; opsiyonel bulut konnektörleri de var |
| DB-GPT, LangChain/LlamaIndex SQL | açık | — | ✅ | ✅ | Genel agent/SQL modülleri | Esnek, ekosistem geniş | Text-to-SQL'e özel optimizasyon az; kendin çok şey kurarsın |

**Öneri:** Başlangıç için **Vanna** (en yalın, en kanıtlanmış) veya **PremSQL** (M1/MLX native + saf-yerel felsefe). Şirket büyüdükçe yönetişim/semantik katman gerekirse **WrenAI**.

---

## 2. Yerel Çalıştırılabilir Modeller (8GB M1 Perspektifi)

| Model | Boyut | 4-bit RAM | 8GB'de? | Text-to-SQL Skoru | Not |
|---|---|---|---|---|---|
| **DuckDB-NSQL-7B** | 7B (Llama-2) | **3.8GB (Q4_0)** | ✅ ama dar (~15-20 tok/s) | iyi | DuckDB diyalektine özel — Postgres'e prompt/şema ile yönlendirilmeli |
| **OmniSQL-7B** | 7B (Qwen2.5-Coder) | ~4-5GB | ✅ ama dar | **Spider %87.9** (greedy); GPT-4o/DeepSeek-V3 seviyesi | Apache 2.0; 2.5M sentetik veriyle eğitilmiş; **en güçlü 7B aday** |
| **Qwen2.5-Coder-7B** | 7B | ~4-5GB | ✅ ama dar | güçlü base | OmniSQL/BASE-SQL bunun üzerine kurulu |
| **SLM-SQL 1.5B** | 1.5B | ~1-1.5GB | ✅ **rahat** | **BIRD-dev %67, test %70.5** | SFT+GRPO + inference-time düzeltme şart; çıplak hali zayıf |
| **SLM-SQL 0.5B** | 0.5B | <1GB | ✅ çok rahat | BIRD-dev %56.9 | Sınırda; tek başına yetersiz (bu iddia doğrulamada **reddedildi**) |
| SQLCoder-7B (Defog) | 7B | ~4-5GB | ✅ dar | tarihsel referans | Eski nesil; yukarıdakiler geçti |

**Çıkarım:** 8GB'de iki seçenek — (a) **OmniSQL-7B-Q4** (en iyi kalite, ama bellek dar) ya da (b) **1.5B özel model** (rahat çalışır, doğruluğu mimari ile telafi et).

---

## 3. Benchmark Durumu (Spider & BIRD)

| Sistem | Model | BIRD | Spider | 8GB'de? |
|---|---|---|---|---|
| **CHASE-SQL** | (kapalı, agentic) | %73.0 test | — | ❌ (referans mimari) |
| **ExCoT** | LLaMA-3.1 **70B** | %68.51 dev | %86.59 | ❌ sunucu (~40GB+ VRAM); ağırlık CC-BY-NC (ticari değil) |
| **BASE-SQL** | Qwen2.5-Coder **32B** | %67.47 dev | %88.9 test | ❌ sunucu (~18-24GB) |
| **RSL-SQL** | GPT-4o + teknikler | %67.2 dev | %87.9 | teknikler taşınabilir |
| **OmniSQL** | 7B/14B/32B | 32B %67.0 | 7B %87.9 / 32B %89.8 | **7B ✅ dar** |
| **SLM-SQL** | 1.5B | %67-70 | %79 | **✅ rahat** |

> **Kritik bağlam:** Bu skorlar büyük ölçüde makale-içi (yazar-raporlu) ölçümler ve akademik diyalekt karışımı üzerinde. Gerçek PostgreSQL (window fonksiyonları, tarih/zaman, JOIN-yoğun analitik) performansı bu rakamlardan **düşük** olabilir. Kendi verinle test şart.

---

## 4. Doğruluğu Artıran Mimari Teknikler (En Önemli Bölüm)

Model küçük olsa bile bu teknikler doğruluğu büyük oranda yükseltir:

1. **Şema linkleme (schema linking):** Soruyla ilgili tablo/kolonları önceden seçip prompt'a sadece onları koy. Çift-yönlü linkleme (RSL-SQL) en iyi sonucu verir. → Küçük modelin context'ini boğmaz.
2. **Few-shot örnekleme:** Benzer geçmiş soru→SQL örneklerini RAG ile getir (Vanna bunu yerleşik yapar).
3. **Çoklu aday + seçici (CHASE-SQL):** Aynı soruya farklı stratejilerle birden çok SQL üret, çalıştır, en iyisini seç. Tek-atış doğruluğu büyük fark.
4. **Çok-turlu self-correction (RSL-SQL):** SQL'i çalıştır, hata/boş sonuç gelirse modele geri besle, düzelttir.
5. **Bağlamsal zenginleştirme:** Kolon açıklamaları, örnek değerler, iş tanımları (WrenAI'nin MDL'i, Vanna'nın dokümantasyon eğitimi).

---

## 5. 8GB M1 Gerçekçi Sınırları & Sunucu Eşiği

- **Çalışan çalıştırıcı sıralaması (Apple Silicon):** **MLX** (Apple-native, %10-50 daha hızlı) > llama.cpp ≈ Ollama. M1 unified memory avantajlı ama 8GB toplam paylaşımlı.
- **7B-Q4:** ~3.8-5GB model + KV cache + OS + PostgreSQL → 8GB'de **swap riski**. Pratikte modeli ve DB'yi aynı anda zorlama; sorgu sırasında diğer ağır uygulamaları kapat.
- **14B+:** 8GB'de pratik değil → **sunucu gerekir**.
- **32B / 70B (en yüksek kalite):** mutlaka GPU'lu sunucu — 32B ~18-24GB VRAM, 70B ~40GB+ VRAM.
- **Uygun maliyetli GPU sunucu:** RunPod, Vast.ai, Lambda, Spheron (saatlik kiralık). 32B için tek A100/A6000 sınıfı yeterli; sadece sorgu anında açıp kapatarak maliyet düşürülebilir.

> **Net tavsiye:** Prototipi 8GB M1'de **7B-Q4 (OmniSQL)** veya **1.5B** ile kur, gerçek doğruluğu kendi verinde ölç. Yeterli değilse → 32B'yi **kendi kontrolündeki** bir sunucuda (yine yerel/private, veri dışarı çıkmaz) çalıştır.

---

## 6. Güvenlik & Otomatik Raporlama

**SQL güvenliği (zorunlu katmanlar):**
- **Salt-okunur DB kullanıcısı + read replica:** DROP/DELETE/UPDATE'i *fiziksel olarak* imkânsız kıl (en güçlü koruma).
- **Sorgu doğrulama:** Üretilen SQL'i çalıştırmadan önce parse et; sadece `SELECT`'e izin ver, çoklu-statement/`;` engelle.
- **PII maskeleme & satır/kolon güvenliği:** Hassas kolonları view/grant ile gizle (WrenAI yerleşik RLS/CLS sunar).
- **OWASP SQL Injection önlemleri:** parametreli sorgular, allow-list yaklaşımı.

**Otomatik rapor üretimi:**
- SQL çalıştır → sonucu (tablo) al → modele "bu sonucu Türkçe özetle + matematiksel çıkarım yap" prompt'u → metin/grafik rapor.
- Vanna bunu yerleşik destekler (`vn.ask` → SQL + sonuç + Plotly grafik + açıklama). Bu, senin "bugün hangi ürün en çok satıldı, hangi mağazada ne çok satıyor" senaryona doğrudan oturur.

---

## 7. Bu Proje İçin Somut Öneri

**Önerilen başlangıç mimarisi:**

```
[Kullanıcı sorusu (TR)]
        ↓
[Vanna / PremSQL orchestration]
   ├─ Şema linkleme (ilgili tablolar)
   ├─ RAG: benzer örnek sorgular (few-shot)
   ↓
[Yerel Model: Ollama OmniSQL-7B-Q4  veya  MLX 1.5B]
   ↓ (çoklu aday + self-correction)
[SQL doğrulama: sadece SELECT, read-only kullanıcı]
   ↓
[PostgreSQL read replica]  ← veri ASLA dışarı çıkmaz
   ↓
[Sonuç → modele özet/rapor prompt'u]
   ↓
[Türkçe rapor + tablo + grafik]
```

**Faz planı:**
1. **Faz 1 (8GB M1):** Vanna + Ollama + **OmniSQL-7B-Q4**. Kendi PostgreSQL şemanı + 20-50 örnek soru-SQL ile eğit. Gerçek doğruluğu ölç.
2. **Faz 2:** Doğruluk düşükse → şema linkleme + few-shot + self-correction ekle (en büyük kazanç burada).
3. **Faz 3:** Hâlâ yetersizse → 32B modeli kendi kontrolündeki private sunucuda çalıştır (yine veri dışarı çıkmaz).
4. **Güvenlik:** Daha 1. günden read-only DB kullanıcısı + SELECT-only doğrulama.

---

## 8. Açık Sorular / Doğrulanması Gerekenler

- 8GB M1'de 7B-Q4'ün **gerçek** token/s ve eşzamanlı PostgreSQL+app yükü altında kullanılabilirliği (kendi makinende ölçülmeli).
- Hangi modelin **PostgreSQL diyalektinde** (window, tarih, analitik JOIN) gerçek-dünya doğruluğu en iyi — akademik skor ≠ saha performansı.
- Kesin GPU sunucu maliyet karşılaştırması (RunPod/Vast.ai fiyatları zamanla değişir).

---

## Kaynaklar (öne çıkanlar)

- Vanna: https://github.com/vanna-ai/vanna
- WrenAI: https://github.com/Canner/WrenAI · https://docs.getwren.ai
- Dataherald: https://github.com/Dataherald/dataherald
- PremSQL: https://github.com/premAI-io/premsql
- OmniSQL-7B: https://huggingface.co/seeklhy/OmniSQL-7B · arXiv 2503.02240
- DuckDB-NSQL: https://ollama.com/library/duckdb-nsql:7b
- SLM-SQL (küçük modeller): arXiv 2507.22478
- BASE-SQL (32B): arXiv 2502.10739 · ExCoT (70B): arXiv 2503.19988
- CHASE-SQL: arXiv 2410.01943 · RSL-SQL: arXiv 2411.00073
- Güvenlik: OWASP SQL Injection Cheat Sheet · rietta.com read-replica
- Awesome-Text2SQL listesi: https://github.com/eosphoros-ai/Awesome-Text2SQL
