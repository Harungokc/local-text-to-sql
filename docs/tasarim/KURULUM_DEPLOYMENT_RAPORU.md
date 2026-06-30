# Yerel/Self-Hosted Text-to-SQL Modeli — Kurulum & Deployment Raporu

> Soru: 8GB M1'le sınırlı kalmadan, KALİTELİ bir yerel modeli (32B-70B) kendi kontrolümüzdeki bir makinede/sunucuda nasıl ayağa kaldırırız — veri yine dışarı çıkmadan.
> Tarih: 2026-06-24 · 25 kaynak, 19 doğrulanmış iddia (3 oylu adversaryal doğrulama). 6 iddia reddedildi (aşağıda).

---

## 0. En Önemli Sonuç (TL;DR)

İki temiz, gizlilik-korumalı yol var — kullanım sıklığına göre seçilir:

| | **A) Mac satın al** | **B) Private GPU kirala** |
|---|---|---|
| Ne | 64GB+ Mac Studio/Mini, her şey tek kutuda yerel | RunPod/Vast/Hetzner'da tek-kiracı GPU, ihtiyaç anında aç |
| Model | 32B-Q4 rahat, 70B-Q4 zorlu | 32B/70B FP16'ya kadar |
| Serving | **Ollama veya MLX** (Mac'te vLLM uygun değil) | **vLLM** (OpenAI-uyumlu, batching, çok-GPU) |
| Maliyet | Tek seferlik ~$2.000-4.000 | RunPod A6000 **$0.49/saat** (tek-kiracı), Vast daha ucuz |
| Ne zaman | Sürekli/günlük kullanım | Ara sıra / değişken yük |
| Gizlilik | Tam (kutu senin) | Tek-kiracı "Secure Cloud" → veri izole instance'ta |

**Bu projeye özel öneri:** Önce **8GB M1'de 7B prototip** (önceki rapor). Kalite yetmezse → **kullanım sürekliyse Mac Studio 64GB satın al**, ara sıraysa **RunPod A6000'i ihtiyaç anında kirala**. İkisinde de veri dışarı çıkmaz.

---

## 1. Serving / Inference Stack Karşılaştırması

| Stack | En iyi donanım | OpenAI-uyumlu API | Eşzamanlı istek (batching) | Kurulum | Production? | Not |
|---|---|---|---|---|---|---|
| **vLLM** | NVIDIA GPU | ✅ | ✅ continuous batching, çok-GPU tensor parallelism | Orta | ✅ En iyi | Yüksek-eşzamanlılık için referans. **Apple Silicon'da production-ready DEĞİL** (deneysel, kaynaktan derleme, sadece FP32/FP16, llama.cpp'den yavaş) |
| **Ollama** | Her şey (Mac dahil) | ✅ | Sınırlı | **Tek komut** | Küçük/orta | En kolay başlangıç; tek kullanıcı/düşük yük için ideal. Vanna doğrudan bağlanır |
| **llama.cpp** | Her donanım (x86/ARM CPU, Apple Metal M1-M4, NVIDIA CUDA) | ✅ | Orta | Orta | Orta | Evrensel; GGUF'un yerli formatı. Mac'te sağlam taban |
| **Apple MLX (mlx-lm)** | Apple Silicon | ✅ | Orta | Kolay | Mac'te iyi | Apple-native; M-serisi için en uygun yollardan biri |
| **SGLang** | NVIDIA GPU | ✅ | ✅ **RadixAttention** (ortak prefix'li isteklerde KV cache yeniden kullanımı) | Zor | ✅ İleri | Aynı şema prompt'u tekrar tekrar gönderiliyorsa (text-to-SQL'de tipik) cache avantajı |
| **HF TGI** | NVIDIA GPU | ✅ | ✅ | Orta | ✅ | vLLM'e alternatif; ekosistem HF |
| **LM Studio** | Masaüstü (Mac/Win) | ✅ | Sınırlı | GUI, çok kolay | Hayır (geliştirme) | Deneme/keşif için pratik GUI |

**Çıkarım:**
- **Mac'te** → Ollama (kolay) veya MLX (hızlı). **vLLM'i Mac'te kullanma.**
- **NVIDIA sunucuda** → vLLM (production, OpenAI-uyumlu endpoint, batching, çok-GPU).
- **SGLang** ileri seviye: text-to-SQL'de şema hep aynı olduğu için RadixAttention KV-cache yeniden kullanımı throughput'u artırır.

> ⚠️ Reddedilen iddialar: "vLLM TGI'den 3.67x hızlı", "vLLM 120-160 req/sec", "MLX llama.cpp'den %20-40 hızlı", "Ollama 1-3 req/sec" — bunlar tek-kaynak/pazarlama, doğrulamada çürütüldü. Kesin sayılar yerine **kendi yükünde ölç.**

---

## 2. Donanım & VRAM Gereksinimleri

**Temel VRAM kuralı:** FP16 = parametre(milyar) × 2 GB. 4-bit (Q4/AWQ/GPTQ) ≈ FP16'nın ~¼'ü + KV cache.

| Model | FP16 | 4-bit (Q4/AWQ) | Hangi donanımda |
|---|---|---|---|
| 7B | ~14 GB | ~4-5 GB | 8GB M1 (dar), her GPU |
| 14B | ~28 GB | ~8-10 GB | 24GB GPU, 32GB+ Mac |
| **32B** | **~60-64 GB** | ~18-24 GB | **A6000 48GB (4-bit rahat)**, 64GB Mac (Q4), FP16 için H100/çift-GPU |
| 70B | ~140 GB | ~40-45 GB | Çift GPU / 96GB+ Mac (Q4 zorlu); FP16 için 2-4× GPU tensor parallelism |

**Apple Silicon gerçek hız (llama.cpp, doğrulandı):**
- **M4 Pro 24GB:** 7B Q4_K_M = **60-80 tok/s**, 13B Q4_K_M = **35-50 tok/s**.
- 32B-Q4 için pratikte **64GB Mac Studio/Mini** gerekir (unified memory model + KV cache + OS'i karşılar).

**NVIDIA tarafı:**
- Consumer GPU'lar 24GB'de tavan yapar (RTX 3090/4090). 32B'yi FP16 çalıştıramazlar.
- **RTX A6000 = 48GB GDDR6 ECC** → 32B'yi rahat, 70B'yi 4-bit'te taşır. "Tatlı nokta" kart.
- 70B FP16 için çok-GPU **tensor parallelism** (vLLM `--tensor-parallel-size 4`): 70B'de ~2.1× throughput artışı doğrulandı (4 GPU).

---

## 3. Private GPU Kiralama (Tek Kiracı — Veri İzole)

| Sağlayıcı | Donanım | Fiyat | Gizlilik notu |
|---|---|---|---|
| **RunPod** | RTX A6000 48GB | **$0.49/saat Secure Cloud** (tek-kiracı/dedicated), $0.33/saat Community | Secure Cloud = izole, tek-kiracı instance |
| **Vast.ai** | Karşılaştırılabilir GPU'lar | Ortalama **$0.29/saat RunPod'dan ucuz** (ör. A100 PCIE: Vast $0.58 vs RunPod $1.19) | Pazar yeri; sağlayıcı seç |
| **Hetzner GEX44** | RTX 4000 SFF Ada **20GB**, i5-13500, 64GB RAM | Aylık dedicated (AI inference) | Tam dedicated fiziksel sunucu (Almanya, KVKK/GDPR dostu) |
| **Hetzner GEX131** | RTX PRO 6000 Blackwell **96GB GDDR7**, Xeon Gold 24c, 256GB DDR5 ECC | Aylık dedicated (AI training) | 70B'ye kadar; tam dedicated |
| Lambda Labs | A100/H100 | Saatlik | Eğitim/ağır iş |

**Maliyet hissi (RunPod A6000 @ $0.49/saat):**
- İhtiyaç-anında ~8 saat/gün × 22 gün ≈ **~$86/ay**
- 7/24 açık ≈ **~$353/ay**
- → Sürekli açık tutacaksan, birkaç ayda bir Mac satın almanın maliyetine yaklaşır → **satın al** mantıklı olur.

> Not: vLLM'in **GGUF** desteği "highly experimental ve under-optimized" (resmi doküman). Sunucuda vLLM kullanacaksan **AWQ veya GPTQ** kuantizasyon tercih et, GGUF'u Ollama/llama.cpp'ye bırak.

---

## 4. Adım Adım Ayağa Kaldırma

### Yol A — Mac'te (Ollama + Vanna), en kolay
```bash
# 1) Ollama kur ve model çek
brew install ollama
ollama serve &
ollama pull qwen2.5-coder:7b        # veya 32B (64GB Mac'te): qwen2.5-coder:32b

# 2) Vanna kur ve yerel Ollama'ya bağla (veri dışarı çıkmaz)
pip install 'vanna[chromadb,ollama,postgres]'
```
```python
from vanna.ollama import Ollama
from vanna.chromadb import ChromaDB_VectorStore

class MyVanna(ChromaDB_VectorStore, Ollama):
    def __init__(self, config=None):
        ChromaDB_VectorStore.__init__(self, config=config)   # embeddingler YERELDE (ChromaDB)
        Ollama.__init__(self, config=config)

vn = MyVanna(config={'model': 'qwen2.5-coder:7b'})           # model config dict ile seçilir
vn.connect_to_postgres(host='localhost', dbname='sirket', user='readonly_user', password='...', port=5432)

# Şemayı + örnek soruları eğit
vn.train(ddl="CREATE TABLE satislar (...)")
vn.train(question="bugün en çok satan ürün?", sql="SELECT urun, SUM(adet) ...")

# Kullan
vn.ask("bu hafta hangi mağazada hangi ürün en çok sattı?")    # SQL + sonuç + grafik + açıklama
```

### Yol B — NVIDIA sunucuda (vLLM, OpenAI-uyumlu endpoint)
```bash
# 1) vLLM ile modeli OpenAI-uyumlu API olarak serve et
pip install vllm
vllm serve Qwen/Qwen2.5-Coder-32B-Instruct-AWQ \
    --tensor-parallel-size 1 \           # çok GPU varsa 2/4 yap (70B için)
    --port 8000
# (GGUF de mümkün ama deneysel: vllm serve unsloth/...-GGUF:Q4_K_M --tokenizer <base>)

# 2) Vanna'yı bu yerel/iç-ağ endpoint'ine OpenAI-uyumlu olarak bağla
```
```python
from openai import OpenAI
client = OpenAI(base_url="http://10.0.0.5:8000/v1", api_key="dummy")  # sadece iç ağ
# Vanna'nın OpenAI-uyumlu wrapper'ı ile base_url'i bu sunucuya yönlendir
```

---

## 5. Production Mimari

```
[İç ağ / VPN — dışarı kapalı]
  Kullanıcı → Vanna/PremSQL uygulaması (Docker)
                 │  OpenAI-uyumlu HTTP (sadece iç ağ)
                 ▼
            Model sunucusu (vLLM @ NVIDIA  veya  Ollama/MLX @ Mac)
                 │
                 ▼
            PostgreSQL READ REPLICA + readonly_user (sadece SELECT)
```

- **Docker** ile paketle (vLLM resmi Docker image var); taşınabilir + tekrarlanabilir.
- **Sürekli açık vs istek-anında:** Sunucu kiralıyorsan ve yük seyrekse → otomatik aç/kapat (maliyet ↓). Kendi Mac'inse zaten hep açık.
- **Eşzamanlı kullanıcı:** vLLM continuous batching + (opsiyonel) SGLang RadixAttention ile aynı şema prompt'u tekrar tekrar geldiğinde KV cache yeniden kullanılır.
- **Güvenli ağ:** Model endpoint'i ASLA internete açma; sadece iç ağ/VPN. Bu, "veri dışarı çıkmaz" garantisinin ağ katmanı.

---

## 6. Maliyet/Performans Kararı

- **Sürekli kullanım (her gün, çok sorgu):** 64GB **Mac Studio satın al**. Tek seferlik ~$2.000-2.500 (64GB) / ~$3.500+ (128GB). Aylık kira yok, sessiz, tam yerel. 32B-Q4 rahat döner.
- **Ara sıra / pilot:** **RunPod A6000 kirala** ($0.49/saat, tek-kiracı). Sadece sorgu seansında aç. Aylık ~$86 (8s/gün) seviyesinde tutulabilir.
- **KVKK/GDPR hassasiyeti yüksek + Avrupa:** **Hetzner dedicated** (GEX44/GEX131) — tam fiziksel dedicated sunucu, Almanya.
- **70B kalite şart:** Çok-GPU sunucu (vLLM tensor parallelism) ya da 96GB+ donanım — sadece gerçekten gerekiyorsa; 32B çoğu text-to-SQL için yeterli.

---

## 7. Doğrulamada Reddedilen / Şüpheli İddialar (dikkat)

- ❌ "vLLM, TGI'den 3.67× hızlı" (0-3 çürütüldü)
- ❌ "vLLM 120-160 req/sec, 50-80ms TTFT" (pazarlama, kaynaksız)
- ❌ "MLX llama.cpp'den %20-40 hızlı" (0-3 çürütüldü — ikisi yakın)
- ⚠️ "Ollama 1-3 req/sec eşzamanlılıkta zayıf" (kısmen — yeni Ollama batching iyileşti)
- ⚠️ "Marlin-AWQ en yüksek throughput" — sayılar gerçek (H200/Qwen2.5-32B: Marlin-AWQ 741, FP16 461, GGUF 93 tok/s) ama "kesin en iyi" çerçevesi tartışmalı
- ✅ Genel ilke: **kuantizasyon + kernel hız sayıları donanıma/yüke çok bağlı — kendi setinde ölç.**

---

## Kaynaklar (öne çıkanlar)

- Serving karşılaştırma: tensorfoundry.io/blog/llm-inference-servers-compared · arXiv 2511.17593 (LLM serving comparison)
- vLLM: docs.vllm.ai (GGUF/quantization, parallelism) · qwen.readthedocs.io/.../vllm.html
- Apple Silicon: contracollective.com (M4 Pro tok/s) · compute-market.com (MLX vs llama.cpp) · sitepoint M3 Max vs RTX 4090
- VRAM: llmconfigurator.com/vram-requirements · jarvislabs.ai/vllm-quantization-benchmarks
- Kiralama: runpod.io/gpu-models/rtx-a6000 · computeprices.com/compare/runpod-vs-vast · hetzner.com/.../matrix-gpu · spheron.network gpu-pricing-2026
- Vanna kurulum: try.vanna.ai/docs/postgres-ollama-vannadb · medium "Vanna AI + Ollama text-to-SQL"
- SGLang RadixAttention: lmsys.org/blog/2024-01-17-sglang · arXiv 2312.07104
