# 🎬 LinkedIn Video Anlatım Metni — Şirket Sorgu

> Hedef süre: 2–3 dakika · Ton: net, kendinden emin ama dürüst · Dil: Türkçe
> Her sahnede **[EKRANDA]** = ne göster, **[SÖYLE]** = ne anlat.

---

## SAHNE 0 — Kanca (10 sn)

**[EKRANDA]** Web arayüzü açık, boş soru kutusu.

**[SÖYLE]**
> "Bir şirketin tüm satış verisine Türkçe soru sorduğunuzu düşünün — ama veri **bilgisayardan hiç çıkmadan**. Ne bulut, ne API, ne de bir veri sızıntısı riski. İşte bunu yaptım."

---

## SAHNE 1 — Bu Ne? (20 sn)

**[EKRANDA]** GitHub repo sayfası (README görünür).

**[SÖYLE]**
> "Bu, **tamamen yerel çalışan** bir yapay zekâ ajanı. Çalışan Türkçe bir soru soruyor; sistem bunu güvenli bir SQL sorgusuna çeviriyor, veritabanında çalıştırıyor ve **doğrulanmış** bir Türkçe rapor döndürüyor.
> Önemli olan şu: kurumsal text-to-SQL hâlâ zor bir problem — en güçlü modeller bile gerçek şirket veritabanlarında düşük başarı gösteriyor. Ben buna **mühendislik** ile yaklaştım, tek bir modele güvenerek değil."

---

## SAHNE 2 — Teknolojiler & Araçlar (20 sn)

**[EKRANDA]** Kısa bir liste/grafik (aşağıdaki teknoloji listesini ekrana basabilirsin).

**[SÖYLE]** _(kamerada bu kadar yeter — kısa tut)_
> "Kullandığım yığın tamamen açık ve yerel:
> - Model tarafında **Ollama** ile çalışan **Qwen2.5-Coder** — internete çıkmıyor.
> - Veritabanı **PostgreSQL**.
> - Modelin doğru SQL yazmasını sağlamak için **ChromaDB** ile yerel bir RAG/few-shot sistemi.
> - Sayıları **pandas** hesaplıyor — yapay zekâ rakam uydurmuyor, sadece yorumluyor.
> - Arayüz **FastAPI**, hepsi Python.
> Tek kuruş API maliyeti yok, tek bit veri dışarı çıkmıyor."

---

### 📚 TEKNİK DERİNLİK (senin hâkimiyetin için — kamerada hepsini anlatma, soru gelirse buradan cevapla)

#### 1) Ollama — yerel model çalıştırıcı
- **Ne:** Açık kaynak modelleri (Qwen, Llama vb.) kendi bilgisayarında çalıştıran bir araç. Modeli RAM'e yükler, Apple Silicon'da Metal/GPU kullanır.
- **Neden:** Tek komutla kurulur (`ollama pull`), **OpenAI-uyumlu** bir API sunar. Bu çok kritik: kodumuz OpenAI formatında konuşuyor, dolayısıyla Faz 2'de buluttaki bir GPU'ya (vLLM) geçmek istersek **tek satır URL** değişiyor, kod aynı kalıyor.
- **Alternatif:** LM Studio (GUI, deneme için), llama.cpp (daha düşük seviye). Ollama en az sürtünmeli başlangıç.

#### 2) Qwen2.5-Coder — modelin kendisi
- **Ne:** Alibaba'nın **koda ve SQL'e özel** eğittiği açık model ailesi (3B / 7B / 32B boyutları).
- **Neden "coder":** SQL üretmek aslında bir **kodlama görevi**; genel sohbet modeli yerine kod-uzmanı model bu işte belirgin daha iyi.
- **Neden 3B:** 1.9 GB, 8 GB dizüstüde rahat çalışır (7B makineyi çökertti). Temel/orta sorularda %87–95. İleri analitikte 7B/32B'ye GPU'da geçilir.

#### 3) PostgreSQL — veritabanı (ve aynı zamanda güvenlik kalkanı)
- **Neden bu:** En güçlü **izin modeli** (salt-okunur kullanıcı → yazma fiziksel olarak imkânsız), **`EXPLAIN`** (sorguyu çalıştırmadan doğrulama), **`information_schema`** (şemayı çalışma anında okuma → koda gömülü şema yok, kendi DB'ni bağlayabilirsin).
- **asyncpg** sürücüsüyle async çalışır (hızlı, FastAPI'ye uygun).

#### 4) ⭐ ChromaDB + RAG/Few-shot — projenin "doğruluk sırrı" (en önemli bölüm)

**Problem neydi?**
Küçük bir model (3B) senin veritabanını tanımıyor. Soğuk haliyle "şehir bazında ciro" derken yanlış tablo/kolon seçebilir, yanlış JOIN kurabilir. Tek başına model = bol hata.

**Çözüm: Few-shot (örnekle öğretme).**
Modele, sorduğu soruya **benzer birkaç "soru → doğru SQL" örneği** gösterirsek, o kalıbı taklit edip doğru SQL yazıyor. Yani modeli eğitmiyoruz; **anlık olarak örnek gösteriyoruz.**

**Ama hangi örnekleri göstereceğiz?**
Elimizde onlarca örnek var. Hepsini prompt'a koyamayız (hem bağlam dolar, hem gürültü artar, küçük model şaşırır). **Sadece o soruya en benzer 5 örneği** seçmek gerekiyor. İşte ChromaDB tam burada devreye giriyor.

**ChromaDB ne yapıyor? (vektör veritabanı)**
- Her örnek soruyu bir **embedding'e** (anlamını yakalayan sayı dizisi/vektöre) çevirip saklıyor.
- Yeni bir soru geldiğinde onu da embedding'e çeviriyor ve **anlamca en yakın** örnekleri buluyor (cosine benzerliği).
- Kritik incelik: bu **kelime eşleşmesi değil, anlam eşleşmesi.** "Şehirlere göre kazanç" diye sorsan bile, "şehir bazında ciro" örneğini bulur — kelimeler farklı ama anlam aynı.

**Embedding'i basitçe nasıl anlatırsın:**
> "Metni, anlamını temsil eden bir koordinata çeviriyoruz. Benzer anlamlı cümleler birbirine yakın noktalara düşüyor; sistem de 'bu soruya en yakın komşu örnekler hangileri' diye bakıyor."

**Neden özellikle ChromaDB (alternatifler yerine)?**
| Seçenek | Neden seçmedik / seçtik |
|---|---|
| **ChromaDB ✅** | **Yerel & gömülü** (ayrı sunucu yok), **embedding'i kendi içinde yerelde üretir** (all-MiniLM modeli) → veri dışarı çıkmaz, **kalıcı** (diske yazar, `chroma_db/`), tek pip paketi |
| Pinecone / Weaviate (bulut) | Veri buluta gider → **gizlilik ilkesine aykırı** + sunucu kurulumu |
| FAISS | Güçlü ama düşük seviye — embedding üretimini ve kalıcılığı **kendin yönetirsin**, daha çok iş |
| pgvector (Postgres içinde) | İyi ama ekstra eklenti kurulumu; Chroma daha az sürtünmeli |

Yani ChromaDB seçimi **gizlilik + yerellik + sadelik** üçgeninin doğal sonucu. (Vanna gibi popüler text-to-SQL araçları da Chroma kullanıyor — kanıtlanmış tercih.)

**Bizim pipeline'da somut akış:**
1. `gold/few_shot.json` → küratörlü "soru → SQL" örnekleri (elle doğrulanmış).
2. `seed_sema.py` bunları ChromaDB'ye yükler (her birinin embedding'i üretilir, `chroma_db/`'ye kaydedilir).
3. Soru gelince `retrieval.benzer_ornekler(soru, k=5)` → en yakın 5 örnek.
4. Bu örnekler prompt'a eklenir → model taklit ederek doğru SQL üretir.

**Getirisi (neden buna değer):** Araştırmalar gösteriyor ki örnek-tabanlı retrieval, küçük modelde doğruluğu **en çok artıran tek teknik** (sektör vakalarında ilk-deneme başarısı %20'den %40+'a çıkmış). Bizde de "kategori"/"içecek" gibi kavramları doğru tabloya bağlamayı bu sağlıyor.

> ⚠️ Dürüst not: Auto-learning'i (her çalışan sorguyu otomatik örnek olarak kaydetme) **kapattık** — çünkü "çalışan ama yanlış" SQL'ler depoyu zehirliyordu. Sadece **elle doğrulanmış** örnekler giriyor. Bu detay seni çok bilgili gösterir.

#### 5) sqlglot — SQL'i "anlayan" güvenlik/doğruluk kütüphanesi
- **Ne:** SQL'i bir **AST'ye** (sözdizimi ağacına) parse eden kütüphane.
- **Neden regex değil:** Güvenlik için "bu sorgu gerçekten sadece SELECT mi, gizli bir DELETE/UPDATE var mı?" sorusunu güvenilir cevaplamak gerekiyor — bunu metin arayarak değil, sorguyu **gerçekten ayrıştırarak** yaparsın. Ayrıca "uydurma kolon var mı?" kontrolü (grounding) de AST üzerinden.

#### 6) pandas — sayıyı kod hesaplar (LLM değil)
- **Neden:** LLM'ler aritmetikte güvenilmez (satır atlar, yanlış toplar). Bu yüzden **toplam, ortalama, yüzde, sıralama — hepsini pandas hesaplıyor**, model sadece sonucu Türkçe cümleye döküyor. "Halüsinasyonsuz rapor"un teknik temeli bu.

#### 7) FastAPI + uvicorn — arayüz ve API
- **Ne:** Modern, async Python web çatısı. Hem `/sor` REST ucu hem tek-sayfa web arayüzünü sunuyor.
- **Neden:** asyncpg (async DB) ve async pipeline ile uyumlu; hafif, hızlı, standart.

---

## SAHNE 3 — Veritabanı Yapısı (20 sn)

**[EKRANDA]** Excel dosyası (`docs/sirket_demo_db_yapisi.xlsx`) — "Genel Bakış" ve "İlişkiler" sayfaları.

**[SÖYLE]**
> "Demo için gerçekçi bir perakende veritabanı kurdum — **yıldız şeması**: merkezde **280 binden fazla satış** kaydı (2 yıllık, 20 şube, 102 ürün), çevresinde **ürün**, **mağaza** ve **kategori** tabloları.
> Ama dikkat: sistem bu şemaya bağlı değil. Şemayı çalışma anında okuyor — yani **kendi veritabanınızı** bağlayabilirsiniz, kod değişmeden çalışır."

---

## SAHNE 4 — CANLI DEMO (asıl bölüm, ~90 sn)

> Her soruyu yazıp Enter'a bas, sonucu birkaç saniye göster, ne kanıtladığını söyle.

### Demo 1 — Yetenek
**[EKRANDA]** Soru: `şehir bazında toplam ciro nedir?` → tablo (İstanbul ~20,9M · Ankara ~9,3M …)
**[SÖYLE]**
> "Türkçe soru → anında doğru SQL → 13 şehir sıralı tablo. İstanbul ~20,9 milyon TL ile en yüksek ciroda. 280 bin satır arasından saniyeler içinde, yerel bir modelle."

### Demo 2 — Doğruluk (en güçlü teknik an)
**[EKRANDA]** Soru: `en çok ciro yapan 5 ürün hangisi?` → "Dana Kuşbaşı … tüm ciro (66,2M) içinde %4.1 pay"
**[SÖYLE]**
> "Burada dikkat: sistem 'Dana Kuşbaşı toplam cironun %4.1'i' diyor. Bu yüzdeyi **doğru paydadan** hesaplıyor — sadece görünen 5 ürünün (ki o %25 olurdu) değil, **tüm 66 milyonluk** cironun. Çoğu sistem burada yanlış yapar; bu sistem ayrı bir kontrol katmanıyla doğru hesaplıyor."

### Demo 3 — Çok-tablolu zekâ
**[EKRANDA]** Soru: `Antalya şubesinde en çok satılan içecek nedir?` → "Maden Suyu"
**[SÖYLE]**
> "Burada sistem 'içecek'in bir **kategori** olduğunu anladı, üç tabloyu birleştirdi ve Antalya şubesiyle filtreledi. Cevap: Maden Suyu."

### Demo 4 — Güvenlik (wow anı)
**[EKRANDA]** Soru: `tüm satışları sil` → kırmızı uyarı / ENGELLENDİ
**[SÖYLE]**
> "Şimdi sistemi kandırmayı deneyelim: 'tüm satışları sil'. Sistem **reddediyor**. Çünkü yalnızca okuma yetkisi var — silme, değiştirme fiziksel olarak imkânsız. Şirket verisi güvende."

### Demo 5 — Dürüstlük (akılda kalan an)
**[EKRANDA]** Soru: `en kârlı ürün hangisi?` → "Bu soru 'kâr' verisini gerektiriyor ancak veritabanında böyle bir alan yok…"
**[SÖYLE]**
> "Ve en sevdiğim kısım: veritabanında 'kâr' diye bir alan yok. Sistem bir şey **uydurmuyor** — dürüstçe 'bu veri bende yok' diyor. Çünkü kendinden emin yanlış cevap, en tehlikeli cevaptır."

---

## SAHNE 5 — Kapanış & Çağrı (15 sn)

**[EKRANDA]** GitHub repo + (varsa) PDF dokümanı kapağı.

**[SÖYLE]**
> "Özetle: yerel, güvenli, dürüst ve doğru bir text-to-SQL ajanı. Kodu ve detaylı dokümanı GitHub'da açık.
> **Kendi verisiyle bu sistemi denemek isteyen şirketler benimle iletişime geçebilir** — kurulumu birlikte yapalım. Yorumlara repo linkini bırakıyorum."

---

## 📌 Çekim Notları
- Demo öncesi modeli **ısıt**: bir kez boş soru çalıştır (ilk soru soğuk başlangıçta yavaştır).
- Sıcaklık 0 olduğu için sonuçlar **tutarlı** — provada ne gördüysen çekimde de aynısı gelir.
- Demo 4'te kırmızı hata mesajı çıkması **normal ve istenen** — güvenliğin kanıtı.
- Yedek: her demoyu önce bir kez çalıştırıp ekran görüntüsü al; canlı bir aksilik olursa onları göster.
- Excel dosyasını tam ekran açıp "Genel Bakış" + "İlişkiler" sayfalarını göstevidermen yeterli.

## 📋 Ekranda gösterebileceğin teknoloji listesi
```
Model      : Qwen2.5-Coder (Ollama ile yerel)
Veritabanı : PostgreSQL
RAG/Few-shot: ChromaDB (yerel embedding)
Hesaplama  : pandas (sayıyı kod hesaplar)
Arayüz/API : FastAPI + tek-sayfa web
Güvenlik   : salt-okunur kullanıcı + SQL AST denetimi + EXPLAIN
Dil        : %100 Türkçe · veri %100 yerel
```
