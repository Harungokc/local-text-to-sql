# Kontrol 3 — Analiz Doğrulama Katmanı (Türetilmiş Metrik Güvenliği)

> Problem: SQL doğru olsa bile, sonuçtan TÜRETİLEN metrikler (pay/yüzde, oran) semantik yanlış olabiliyor. Kontrol 1 (güvenlik) ve Kontrol 2 (SQL doğruluk) bunu yakalamıyor çünkü SQL'i denetliyorlar, türetilmiş analizi değil.
> Somut hata: "en çok ciro 5 ürün" (LIMIT 5) → "Bal, toplam ciro içinde %25.1" (yanlış payda: sadece 5 satırın toplamı). Gerçek pay %10.7.
> Tarih: 2026-06-25 · Kaynak: Kimball additivity, dbt/MetricFlow ratio, sqlglot AST, PLOG/PCN numeric faithfulness (22 doğrulanmış iddia).

---

## 1. Kök Neden

Kontrol noktaları yalnızca **SQL evrenini** kapsıyordu:
- Kontrol 1: güvenlik (SELECT-only)
- Kontrol 2: şema grounding + EXPLAIN (SQL şemaya oturuyor + çalışıyor mu)

Ama hata **rapor.py'nin türetilmiş metrik hesabında**. Bu katmanı denetleyen kontrol yoktu → kör nokta. Çözüm: kontrol felsefesini **SQL'den analiz katmanına genişletmek** = Kontrol 3.

---

## 2. Temel İlke — Metrik Additivity Sınıflandırması

Her metriğin bir **geçerlilik ön-koşulu** vardır (kaynak: Kimball, dbt MetricFlow):

| Metrik tipi | Örnek | Kısmi/LIMIT'li sonuçtan güvenli mi? | Kural |
|---|---|---|---|
| **Additive** | toplam (SUM), adet (COUNT) | Kısmen — "dönen satırların toplamı" doğru, ama "grand total" DEĞİL | Toplamı yalnızca "gösterilenler için" diye etiketle |
| **Non-additive (oran)** | pay %, yüzde, oran | **HAYIR** — payda doğru evrenden gelmeli | Grand total'i AYRI hesapla; gelmiyorsa pay'ı BASTIR |
| **Non-additive (ortalama)** | AVG | Kısmi ortalama ≠ genel ortalama | Tam evren yoksa "gösterilenlerin ortalaması" de |
| **Sıralama / en yüksek-düşük** | top-1, max | Evet (ORDER BY + LIMIT zaten bunun için) | Güvenli — ama "en düşük" LIMIT'liyse YANLIŞ (sadece gösterilenler içinde) |

> Kritik içgörü: **pay/yüzde NON-ADDITIVE'dir.** "X, toplam içinde %P" demek için payda = TÜM evrenin toplamı olmalı. LIMIT'li sorguda dönen satırların toplamı ≠ grand total → iddia yanlış.

---

## 3. Kesik Sonuç Tespiti (deterministik, sqlglot)

SQL AST'den, sonuç gelmeden önce çıkarılır:

```python
import sqlglot
from sqlglot import expressions as exp

def sorgu_profili(sql: str) -> dict:
    """SQL'in türetilmiş metrik için 'tam evren mi kesik mi' profilini çıkarır."""
    agac = sqlglot.parse_one(sql, read="postgres")
    limit = agac.args.get("limit")
    return {
        "limit_var": limit is not None,
        "limit_n": int(limit.expression.name) if limit else None,
        "where_var": agac.find(exp.Where) is not None,
        "group_by_var": agac.find(exp.Group) is not None,
        # agregasyon ölçü kolonu (SUM/COUNT/AVG) — pay paydası için
        "olcu_ifadeleri": [f.sql() for f in agac.find_all(exp.Sum, exp.Count, exp.Avg)],
    }
```

Karar:
- `limit_var` True **veya** `len(satirlar) == limit_n` → sonuç **muhtemelen kesik (top-N)**.
- Kesikse: "toplam içinde pay" **geçersiz** → ya gerçek toplamı çek ya da bastır.

---

## 4. Gerçek Toplamı Güvenle Çekme (mühendislik çekirdeği)

Pay doğru olsun istiyorsak, paydayı **ayrı, güvenli bir agregat sorgusuyla** çekeriz: orijinal sorgudan ORDER BY + LIMIT atılır, ölçü kolonu toplanır.

```python
def grand_total_sorgusu(orijinal_sql: str, olcu_kolon: str) -> str:
    """Orijinal SELECT'ten LIMIT/ORDER BY çıkarıp grand total üretir.
       SELECT SUM(<olcu>) FROM ( <orijinal, limit/order yok> ) t
    """
    agac = sqlglot.parse_one(orijinal_sql, read="postgres")
    agac.set("limit", None)
    agac.set("order", None)
    return f"SELECT SUM(t.{olcu_kolon}) AS gercek_toplam FROM ({agac.sql('postgres')}) t"
```

- Bu türetilmiş sorgu da **Kontrol 1 + Kontrol 2'den geçer** (yine SELECT, şemaya oturur).
- Sonuç: `pay = deger / gercek_toplam` → doğru "grand total içinde pay".
- Çekilemezse (ör. hesaplanamayan ölçü) → pay metriğini **bastır** + çekince ekle.

---

## 5. Kontrol 3 — Analiz Doğrulama Aşaması (yeni)

**Konum:** SQL çalıştıktan SONRA, rapor üretilmeden ÖNCE.

```
... çalıştır → [KONTROL 3: Analiz Doğrulama] → bulgu üret → [sayısal sadakat kontrolü] → yanıt
```

**Sorumluluğu:** Her türetilmiş metriğin ön-koşulunu denetlemek.

```python
# Her bulgu artık bir GEÇERLİLİK KOŞULU taşır:
{
  "tip": "pay",
  "deger": ...,
  "payda_kaynagi": "grand_total" | "gosterilen",   # şeffaflık
  "gecerli": True/False,
  "cekince": "Sonuç ilk 5 ile sınırlı; pay tüm evren üzerinden hesaplandı." | None,
}
```

Karar mantığı (pay metriği için):
```
sonuç kesik mi? (sorgu_profili)
  ├─ HAYIR (tam evren)  → pay = deger / sum(dönenler)   ✓ geçerli
  └─ EVET (LIMIT/top-N) → grand_total'i ayrı çek
        ├─ başarılı → pay = deger / grand_total  ✓ geçerli ("grand total içinde")
        └─ başarısız → pay'ı BASTIR + çekince ("yalnızca gösterilenler içinde")
```

**Deterministik (LLM yok), ucuz** — en fazla 1 ek agregat sorgusu.

---

## 6. Sayısal Sadakat Kontrolü (faithfulness — PLOG/PCN ilhamı)

Anlatım (LLM) üretildikten sonra son bir kapı: **anlatımdaki her sayı, yapılandırılmış olgularda var mı?**

```python
def sadakat_kontrol(ozet_metni: str, olgular: list[dict]) -> tuple[bool, list]:
    """Anlatımdaki sayıları çıkar; her biri olgulardaki bir değere karşılık geliyor mu?
       Karşılığı olmayan sayı → halüsinasyon/uydurma sinyali."""
    metindeki = _sayilari_cikar(ozet_metni)
    gecerli = _olgulardaki_sayilar(olgular)
    uydurma = [s for s in metindeki if s not in gecerli]
    return (len(uydurma) == 0, uydurma)
```
- Uydurma sayı varsa → anlatımı reddet/yeniden üret veya çekince ekle.
- Bu, "logical form ara-temsili" (PLOG) + "doğrulamayı renderer'a koy" (PCN) prensiplerinin uygulaması.

---

## 7. Güncellenmiş Pipeline (tam resim)

```
Soru → şema linkleme → few-shot → SQL üret
  → KONTROL 1: güvenlik (SELECT-only)
  → KONTROL 2: doğruluk (grounding + EXPLAIN)
  → çalıştır (read-only)
  → KONTROL 3: ANALİZ DOĞRULAMA            ← YENİ
       · sorgu profili (kesik mi?)
       · pay/oran ön-koşulu (gerekirse grand total ayrı çek)
       · geçersiz metrikleri bastır + çekince
  → rapor üret (deterministik olgular → LLM anlatım)
  → SAYISAL SADAKAT kontrolü (anlatımdaki sayılar olgularda mı?)  ← YENİ
  → yanıt (+ çekinceler + güven)
```

---

## 8. Kod Değişiklikleri

| Dosya | Değişiklik |
|---|---|
| `sql_kontrol.py` | `sorgu_profili()` (AST'den LIMIT/WHERE/ölçü) ekle |
| yeni `analiz_kontrol.py` | Kontrol 3: metrik ön-koşul denetimi + grand_total çekme + sadakat kontrolü |
| `rapor.py` | `ozetle()` artık `sorgu_profili` + `gercek_toplam` alır; pay'ı doğru paydayla hesaplar veya bastırır; her bulguya `gecerli`/`cekince` ekler |
| `runner.py` | çalıştırma sonrası `analiz_kontrol`'ü çağır; gerekirse grand_total sorgusunu (Kontrol 1+2'den geçirerek) çalıştır; sadakat kontrolünü rapor sonrası uygula |
| `db_sorgu.py` | (mevcut `calistir_select` yeterli — grand_total da SELECT) |

---

## 9. Doğrulama
- Birim test: LIMIT'li sorguda pay → ya doğru grand-total payda ya "gösterilenler içinde" etiketi (asla yanlış "toplam içinde").
- Birim test: kesik olmayan (GROUP BY, LIMIT yok) sorguda pay → dönen toplamla doğru.
- Sadakat testi: olguda olmayan sayı içeren sahte anlatım → reddedilmeli.
- Canlı: "en çok ciro 5 ürün" → "Bal, tüm ciro içinde %10.7" (doğru) VEYA "gösterilen 5 ürün içinde %25.1" (dürüst etiket).

---

## 10. Tasarım Felsefesi (neden "mühendislik harikası")
- **Her metrik kendi geçerlilik koşulunu taşır** — kör "her zaman pay hesapla" yok.
- **Kontrol felsefesi tüm katmana yayıldı** — SQL + türetilmiş analiz + anlatım, üçü de denetleniyor.
- **Deterministik öncelik** — pahalı LLM yok; sadece AST + 1 agregat sorgu.
- **Dürüstlük** — koşul sağlanmazsa yanlış iddia etmek yerine bastır/çekince koy. ("emin değilim" > "kendinden emin yanlış")

## Kaynaklar
Kimball additive/semi/non-additive facts · dbt Ratio metrics (docs.getdbt.com/docs/build/ratio) · MetricFlow ratio metrics · sqlglot AST (find/find_all/args) · LogicNLG + PLOG (arXiv 2004.10404, table-to-logic) · PCN numeric faithfulness (presentation-layer verification) · Power BI totals semantics (sqlbi.com)
