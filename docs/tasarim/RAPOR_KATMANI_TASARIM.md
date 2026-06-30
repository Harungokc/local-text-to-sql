# Matematik / Rapor Katmanı — GitHub Araştırması + Mimari Tasarım

> Amaç: SQL sonucundan (tablo) matematiksel/istatistiksel işleme + Türkçe rapor/içgörü üreten katmanı (`rapor.py`) en iyi açık kaynak örneklere göre güçlendirmek.
> Tarih: 2026-06-24 · Kaynak: 11 doğrulanmış bulgu (LIDA, PandasAI, ydata-profiling, Vanna, smolagents, llm-sandbox + benchmark'lar).

---

## 0. En Net Sonuç (önce bunu oku)

**Kanıt güçlü ve oybirliğiyle: HİBRİT mimari.** Yani:
- **Tüm sayıları/istatistikleri KOD (pandas) hesaplar** — deterministik.
- **Yerel LLM (Qwen2.5-Coder) SADECE yorumlar/anlatır** — asıl rakamı asla üretmez.

**Neden:** Code-Interpreter tarzı "LLM hesaplasın" yaklaşımı bile güvenilmez — benchmark'lar (CIBench) gösteriyor: GPT-4 uçtan uca sayısal doğrulukta sadece ~%78, en iyi açık model ~%65; LLM satır atlıyor, yanlış filtreliyor, farklı girdilere aynı sonucu veriyor, sessizce veri bozuyor. → **Sayıyı LLM'e bırakmak yasak.**

Bizim `rapor.py` zaten bu ilkeyle yazılmıştı (pandas hesaplar, LLM yorumlar). Araştırma bu kararı **birinci elden doğruladı** — şimdi onu en iyi açık kaynak kalıplarıyla genişleteceğiz.

---

## 1. Örnek Alınacak Açık Kaynak Kalıpları

| Repo | Lisans | Ne için örnek | Bize katkı |
|---|---|---|---|
| **Microsoft LIDA** | MIT | **Stats-then-narrate** ayrımının referansı | `rapor.py`'nin ana kalıbı (aşağıda) |
| **ydata-profiling** | MIT | Hazır deterministik otomatik-içgörü motoru | Bulgu katmanı (korelasyon, anomali, eksik/sıfır uyarıları) |
| **Vanna** | MIT | SQL + tablo + Plotly grafik + özet tek akışta | Grafik + özet kalıbı (`generate_plotly_code`, `generate_summary`) |
| **PandasAI** | (çekirdek açık) | Kod-üretme (Code Interpreter) yaklaşımı + Docker sandbox | Grafik/serbest analiz için referans (riskli kısım) |
| **smolagents** | Apache | `LocalPythonExecutor` — AST denetimli güvenli exec | Üretilen kod çalıştırılırsa 1. katman güvenlik |
| **llm-sandbox** | MIT | Docker/Podman izole kod çalıştırma | Üretilen kod için gerçek izolasyon |

---

## 2. İki Mimari Yaklaşım — Hangisi Ne Zaman

### (A) Deterministik + Anlatım (ÖNERİLEN ana yol)
- Metrikleri **sabit kodla** hesapla (pandas), LLM sadece Türkçe yorum yazar.
- **Artı:** Sayı %100 doğru, hızlı, güvenli (kod çalıştırma riski yok), öngörülebilir.
- **Eksi:** Sadece önceden tanımlı metrikleri hesaplar.
- **LIDA SUMMARIZER bunun referansı:** `summarizer.py` → `get_column_properties()` ile tip/min/max/benzersiz/örnek çıkarır (Aşama 1 deterministik), `summarize(method='default'|'llm')` ile opsiyonel LLM zenginleştirir (Aşama 2).

### (B) Kod-Üretme (Code Interpreter — dikkatli kullan)
- LLM pandas/grafik kodu yazar, **sandbox'ta çalıştırılır**; sayı çalıştırılan koddan gelir.
- **Artı:** Esnek, beklenmedik soruları da yanıtlar; Qwen2.5-Coder'ın kodlama gücünü kullanır.
- **Eksi:** Güvenlik riski (kod çalıştırma), gecikme, güvenilmezlik (benchmark ~%78).
- **PandasAI bunun referansı:** `df.chat()` kod üretir, `DockerSandbox` ile çalıştırır.

**Bizim karar:** **Hibrit, ağırlık (A).** Standart metrikler deterministik (A); grafik üretimi gibi esnek kısım için (B) ama mutlaka sandbox'la. (B)'yi sadece gerektiğinde, vitrin Faz 3'te.

---

## 3. Sayı Halüsinasyonunu Önleme — Kod Kalıpları

İki sağlam teknik (ikisini birleştir):
1. **Hesabı koddan al, LLM'e sadece hazır sayıları ver** (mevcut `rapor.py` yaklaşımı). Promptta: "sana verilen sayılar dışında rakam üretme."
2. **Slot-doldurma / şablonlu anlatım** (Schema-Guided NLG kalıbı): LLM Türkçe cümleyi **boşluklu** yazar (örn. "En çok satan ürün {urun}, toplam {adet} adet"), sayıları **kod mekanik olarak doldurur**. Böylece model sayıya hiç dokunmaz.

> ⚠️ Dürüst not: Araştırmada "tek sihirli çözüm" iddiaları (LIDA'nın PAL kullandığı, "LLM sadece yorumlayınca halüsinasyon biter") **çürütüldü (0-3)**. Doğru olan: hesaplama ile anlatımı ayırmak riski büyük ölçüde azaltır ama tek bir teknik %100 garanti vermez. Bu yüzden **iki tekniği birden** kullanırız.
> ⚠️ Türkçe için: slot-doldurma morfoloji/ek uyumunu bozabilir ("3 adet" vs ek çekimleri). Bu yüzden kritik sayılar slot, akıcı bağlam serbest LLM — karma yaklaşım.

---

## 4. Otomatik İçgörü (automated insights) — Satış Verisi İçin

Deterministik kodla hesaplanacak standart metrikler (şirket satış verisi için):
- **En yüksek/düşük + pay:** en çok satan ürün/mağaza + toplam içindeki yüzdesi.
- **Dönem karşılaştırması:** bu hafta vs geçen hafta, bu ay vs geçen ay (büyüme oranı %).
- **Trend:** hareketli ortalama, artış/azalış yönü.
- **Anomali/aykırı:** olağandışı yüksek/düşük satış (IQR/z-score).
- **Yoğunlaşma:** ilk N ürün toplam satışın %kaçı (Pareto).
- **Genel EDA uyarıları:** ydata-profiling hazır verir (eksik veri, sıfır, sabit kolon, korelasyon, çarpıklık).

> ydata-profiling tek satırla (`ProfileReport(df)`) bu uyarıları LLM'siz üretir — bulgu katmanı için doğrudan kullanılabilir (ama ağır; biz hafif kendi metriklerimizi yazıp ydata'yı opsiyonel tutarız).

---

## 5. Grafik / Görselleştirme

- **LIDA kalıbı:** Grafiği "kod" olarak gör — LLM bir **iskelet** (importlar + boş plot fonksiyonu) doldurur (fill-in-the-middle), kod çalıştırılır, derlenenler filtrelenir. Matplotlib/Plotly/Altair destekler.
- **Vanna kalıbı:** `generate_plotly_code()` + `get_plotly_figure()` — sonuçtan Plotly grafiği.
- **Otomatik grafik tipi:** kategori+sayı → bar; zaman serisi → çizgi; pay → pasta. Basit kural tablosuyla seçilebilir (LLM'siz).
- **Bizim karar:** Faz 3'te, Plotly ile; grafik kodu üretilirse sandbox'ta çalıştır.

---

## 6. Sandbox / Güvenlik (kod üretme yolunu seçersek)

- **Katman 1:** smolagents `LocalPythonExecutor(['numpy'])` — AST'yi operasyon operasyon çalıştırır, allowlist dışı importu reddeder (`random._os` bile yasak), operasyon sayısını sınırlar.
- **Katman 2 (gerçek izolasyon):** Docker / `llm-sandbox` (MIT) — host erişimi yok, CPU/bellek/süre limiti, ağ kapalı (`network=none`), otomatik matplotlib grafik çıkarma.
- **Uyarı:** Hiçbir yerel sandbox %100 güvenli değil (izinli paket Pillow'la disk doldurulabilir). Gizlilik-kritik kurulumda **derinlemesine savunma** şart: allowlist + konteyner + ağ kapalı + kaynak limiti.

> **Bizim için en güvenli ve basit yol:** Deterministik metrikleri (A) hiç kod çalıştırmadan yaptığımız için **sandbox gerekmez**. Sandbox sadece (B) grafik kod-üretmeyi seçersek devreye girer → o yüzden grafik Faz 3 opsiyonel.

---

## 7. `rapor.py` İçin Somut Mimari Öneri (LIDA'dan ilhamla)

Mevcut `rapor.py`'yi LIDA'nın modüler yapısına benzeterek 3 katmana ayır:

```
rapor.py
├── ozetle(satirlar)          # AŞAMA 1 — DETERMİNİSTİK (pandas, LLM yok)
│     → tip/sayı profili + standart satış metrikleri (en yüksek, pay,
│       dönem karşılaştırma, trend, anomali) → yapısal "bulgular" sözlüğü
├── icgoru_sec(bulgular)      # AŞAMA 2 — kural tabanlı önceliklendirme
│     → en dikkat çekici 2-3 bulguyu seç (LLM'siz)
└── anlat(soru, bulgular)     # AŞAMA 3 — LLM SADECE YORUM (Türkçe)
      → slot-doldurma + serbest bağlam; "verilen sayı dışında rakam üretme"
```

- **Sayı garantisi:** Aşama 1+2 tamamen kod → rakamlar %100 doğru. Aşama 3 sadece dil.
- **Genişleme:** Yeni metrik = Aşama 1'e fonksiyon ekle (LLM'e dokunma).
- **Grafik (Faz 3):** ayrı `grafik.py` — Vanna/LIDA kalıbı, gerekirse sandbox.

---

## 8. Fazlama

- **Faz 1 (şimdi):** `rapor.py`'yi 3 katmana ayır; standart satış metriklerini deterministik yaz (en yüksek/pay/dönem/trend/anomali); slot-doldurma + LLM anlatım. Bedava, güvenli, en yüksek getiri.
- **Faz 3:** ydata-profiling opsiyonel entegrasyon; grafik üretimi (Plotly, gerekirse sandbox); kod-üretme yolu (B) sadece "serbest analiz" modu için.
- **Gelecek işi:** Tam Code Interpreter modu (PandasAI tarzı) — vitrin için anlatılır.

---

## 9. Doğrulama
- Sayı doğruluğu: aynı veri için Aşama 1 metrikleri elle/SQL ile çapraz kontrol → %100 eşleşmeli.
- Halüsinasyon testi: LLM çıktısındaki her sayı, bulgular sözlüğünde var mı? (otomatik kontrol).
- Gold set: rapor metrikleri gerçek değerlerle uyuşuyor mu.

---

## Kaynaklar
LIDA (arXiv 2303.02927, github.com/microsoft/lida) · ydata-profiling (github.com/ydataai/ydata-profiling) · Vanna (github.com/vanna-ai/vanna) · PandasAI (github.com/sinaptik-ai/pandas-ai) · Schema-Guided NLG (github.com/alexa/schema-guided-nlg, arXiv 2005.05480) · CIBench (arXiv 2407.10499) · H-STAR (arXiv 2407.05952) · smolagents secure execution (huggingface.co/docs/smolagents) · llm-sandbox (pypi.org/project/llm-sandbox)
