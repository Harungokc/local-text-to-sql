# Kurulum — Şirket Sorgu Text-to-SQL Agent

## Faz 1 — Yerel Geliştirme (MacBook M1, ücretsiz)

### 1) Ollama + model
```bash
brew install ollama
ollama serve &                 # arka planda
ollama pull qwen2.5-coder:7b   # ~4-5 GB; 8GB M1'de dar ama çalışır
```

### 2) Python ortamı
```bash
cd ~/Desktop/Local-şirket-sorgu
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3) Veritabanı — salt-okunur kullanıcı (ÖNERİLEN)
PostgreSQL'de yalnızca SELECT yetkili bir kullanıcı oluştur:
```sql
CREATE USER sorgu_ro WITH PASSWORD 'guclu_parola';
GRANT CONNECT ON DATABASE sirket TO sorgu_ro;
GRANT USAGE ON SCHEMA public TO sorgu_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO sorgu_ro;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO sorgu_ro;
ALTER ROLE sorgu_ro SET default_transaction_read_only = on;
ALTER ROLE sorgu_ro SET statement_timeout = '8s';
```

### 4) Ortam değişkenleri
```bash
export SORGU_DATABASE_URL="postgresql://sorgu_ro:guclu_parola@localhost:5432/sirket"
export YEREL_MODEL="qwen2.5-coder:7b"
export VLLM_BASE_URL="http://127.0.0.1:11434/v1"   # Ollama OpenAI-uyumlu uç
```

### 5) Şema keşfi + few-shot yükleme
```bash
# Önce kendi örneklerini hazırla:
cp gold/few_shot.ornek.json gold/few_shot.json   # sonra kendi şemana göre düzenle
python seed_sema.py
```

### 6) Servisi başlat
```bash
uvicorn api:app --host 127.0.0.1 --port 9000
```

### 7) Test et
```bash
curl http://127.0.0.1:9000/saglik
curl -X POST http://127.0.0.1:9000/sor \
     -H "Content-Type: application/json" \
     -d '{"soru":"bugün hangi ürün en çok satıldı?"}'
```

### 8) Güvenlik testi + doğruluk ölçümü
```bash
python test_guvenlik.py                  # SQL güvenlik katmanı birim testi
cp gold/few_shot.json gold/sorular.json  # gold sete "gold_sql" + "tip" ekle
python gold_set.py                       # execution-match doğruluk
```

---

## Faz 2 — Kiralık Sunucu (RunPod A6000, 32B)

Uygulama + model **aynı izole instance'ta** çalışır; veri makineyi terk etmez.

```bash
# RunPod A6000 Secure Cloud instance içinde:
pip install vllm
vllm serve Qwen/Qwen2.5-Coder-32B-Instruct-AWQ \
    --quantization awq --tensor-parallel-size 1 \
    --max-model-len 16384 --gpu-memory-utilization 0.92 \
    --host 127.0.0.1 --port 8000     # DİKKAT: 0.0.0.0 DEĞİL → dışa kapalı
```

Uygulama tarafında SADECE şu env'ler değişir (kod aynı):
```bash
export YEREL_MODEL="Qwen/Qwen2.5-Coder-32B-Instruct-AWQ"
export VLLM_BASE_URL="http://127.0.0.1:8000/v1"
```

**Ağ güvenliği:** vLLM ve PostgreSQL asla internete açılmaz; güvenlik duvarında
yalnızca SSH (22) açık. Uygulama da aynı kutuda → trafik dışarı çıkmaz.

---

## Ortam Değişkenleri Özeti

| Değişken | Açıklama | Varsayılan |
|---|---|---|
| `SORGU_DATABASE_URL` | Salt-okunur DB bağlantısı (readonly_user) | `DATABASE_URL`'e düşer |
| `YEREL_MODEL` | Model adı (Ollama etiketi / HF repo) | `qwen2.5-coder:7b` |
| `VLLM_BASE_URL` | OpenAI-uyumlu yerel endpoint | `http://127.0.0.1:11434/v1` |
| `SORGU_TIMEOUT_MS` | Sorgu zaman aşımı | `8000` |
| `SORGU_SATIR_LIMITI` | Maks dönen satır | `1000` |
| `MAKS_DUZELTME` | Self-correction tur sayısı | `2` |
| `CHROMA_YOLU` | Few-shot deposu dizini | `./chroma_db` |
