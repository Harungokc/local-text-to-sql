"""
Rapor Modülü — 3 Katmanlı Analiz + Türkçe Rapor (LIDA kalıbı)
=============================================================

Microsoft LIDA'nın "önce deterministik istatistik, sonra opsiyonel LLM anlatım"
ayrımından ilhamla 3 katman:

  1) ozetle(satirlar)         → AŞAMA 1: DETERMİNİSTİK (pandas, LLM YOK)
                                Kolon profili + standart satış metrikleri
                                (en yüksek/düşük, pay, yoğunlaşma, anomali) +
                                her bulgu için sayısı KODLA gömülmüş "olgu cümlesi".
  2) icgoru_sec(ozet, k)      → AŞAMA 2: KURAL TABANLI önceliklendirme (LLM YOK)
                                En dikkat çekici k bulguyu önem skoruna göre seçer.
  3) anlat(soru, olgular,llm) → AŞAMA 3: LLM SADECE YORUM (Türkçe)
                                Kod tarafından üretilmiş olguları akıcı metne çevirir;
                                sayı UYDURAMAZ (olgular hazır verilir).

İlke: Sayıyı KOD hesaplar ve cümleye KOD gömer; LLM yalnızca akıcılık katar.
Bu, sayı halüsinasyonunu önler ve Türkçe ek/morfoloji uyumunu korur.
"""
import pandas as pd

import analiz_kontrol
import sql_kontrol
from araclar import prompt_yukle


# ---------- Yardımcılar ----------

def _fmt(x) -> str:
    """Sayıyı okunaklı biçimlendirir: tam sayıysa ondalık gösterme."""
    try:
        f = float(x)
    except (TypeError, ValueError):
        return str(x)
    if f == int(f):
        return f"{int(f):,}".replace(",", ".")  # binlik ayıracı: 12.500
    return f"{f:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# Yaygın kolon adlarını okunabilir Türkçe etikete çevir
_ETIKET = {
    "urun": "ürün", "sehir": "şehir", "magaza": "mağaza", "marka": "marka",
    "kategori": "kategori", "ad": "kalem",
    "toplam_adet": "toplam adet", "toplam_ciro": "toplam ciro", "ciro": "ciro",
    "toplam_tutar": "toplam tutar", "ortalama_tutar": "ortalama tutar",
    "gunluk_ciro": "günlük ciro", "adet": "adet",
}


def _human(kol: str) -> str:
    """Kolon adını okunabilir hale getirir (toplam_adet → 'toplam adet')."""
    return _ETIKET.get(kol, kol.replace("_", " "))


def _kategori_kolon(df: pd.DataFrame) -> str | None:
    """Etiket/kategori kolonu: ilk metinsel (sayısal olmayan) kolon."""
    for kol in df.columns:
        if not pd.api.types.is_numeric_dtype(df[kol]) and not kol.startswith("_"):
            return kol
    return None


def _deger_kolon(df: pd.DataFrame) -> str | None:
    """Değer kolonu: ilk sayısal kolon (_pay_yuzde hariç)."""
    for kol in df.columns:
        if pd.api.types.is_numeric_dtype(df[kol]) and not kol.startswith("_"):
            return kol
    return None


# Agregat (ölçü) fonksiyonları — profil.olculer'den
_AGG = {"sum", "count", "avg", "minmax"}


def _olcu_ve_boyutlar(df: pd.DataFrame, profil: dict | None) -> tuple[str | None, list[str]]:
    """Sonuç kolonlarını ÖLÇÜ (measure) ve BOYUT (dimension) olarak ayırır.

    Sağlam yöntem: profil.olculer (SQL AST'den) ile agregat kolonları (SUM/
    COUNT/AVG...) ölçü, geri kalan TÜM kolonları (metin VEYA id/yıl gibi sayısal)
    boyut sayar. Böylece "şehir + ürün + SUM(adet)" gibi çok-boyutlu sonuçta
    HER İKİ boyut da etikete girer (önceden sadece ilki kullanılıyordu).

    profil yoksa: ilk sayısal = ölçü, sayısal olmayanlar = boyut (geri uyum).
    Dönüş: (olcu_kolon | None, boyut_kolonlari).
    """
    olculer = (profil or {}).get("olculer") or {}
    kolonlar = [c for c in df.columns if not str(c).startswith("_")]
    agg = [c for c in kolonlar if olculer.get(str(c).lower()) in _AGG]
    # BOYUT (etiket) = yalnızca METİN kolonlar. Sayısal ölçü-olmayan kolonlar
    # (ör. modelin eklediği ROUND(...)=100.0 ya da id'ler) ETİKET OLAMAZ.
    if agg:
        olcu = agg[0]
    else:
        olcu = _deger_kolon(df)
    boyutlar = [
        c for c in kolonlar
        if c != olcu and not pd.api.types.is_numeric_dtype(df[c])
    ]
    return olcu, boyutlar


def olcu_kolonu(satirlar: list[dict], profil: dict | None = None) -> str | None:
    """Sonuçtaki ölçü kolonunun adını döndürür — Kontrol 3 grand total için."""
    if not satirlar:
        return None
    olcu, _ = _olcu_ve_boyutlar(pd.DataFrame(satirlar), profil)
    return olcu


# ---------- AŞAMA 1: Deterministik özet (KONTROL 3 entegre) ----------

def ozetle(satirlar: list[dict], profil: dict | None = None,
           gercek_toplam: float | None = None) -> dict:
    """Sorgu sonucundan deterministik metrikler + olgu cümleleri üretir.

    KONTROL 3 (additivity farkındalığı): pay/oran NON-ADDITIVE'dir. Sonuç
    kesikse (LIMIT/top-N), 'toplam içinde pay' yalnızca DOĞRU payda (grand
    total) varsa hesaplanır; yoksa 'gösterilenler içinde' diye etiketlenir.

    profil: sql_kontrol.sorgu_profili çıktısı (limit_var/limit_n...).
    gercek_toplam: Kontrol 3'ün ayrı sorguyla çektiği grand total (varsa).

    Dönüş: {
      "df", "satir_sayisi", "metrikler",
      "bulgular": [{tip, onem, olgu, gecerli, payda_kaynagi?, cekince?}],
    }
    """
    df = pd.DataFrame(satirlar)
    ozet: dict = {"df": df, "satir_sayisi": len(df), "metrikler": {}, "bulgular": []}

    if df.empty:
        ozet["bulgular"].append(
            {"tip": "bos", "onem": 1.0, "olgu": "Sorgu sonucunda hiç kayıt bulunamadı."}
        )
        return ozet

    bulgular: list[dict] = ozet["bulgular"]

    # Sayısal kolonların temel istatistikleri
    sayisal = df.select_dtypes("number")
    sayisal = sayisal[[k for k in sayisal.columns if not k.startswith("_")]]
    for kol in sayisal.columns:
        s = sayisal[kol]
        ozet["metrikler"][kol] = {
            "toplam": float(s.sum()),
            "ortalama": round(float(s.mean()), 2),
            "medyan": round(float(s.median()), 2),
            "maks": float(s.max()),
            "min": float(s.min()),
        }

    olcu, boyutlar = _olcu_ve_boyutlar(df, profil)

    # KONTROL 3 — Sonuç kesik mi? (LIMIT var VE satır sayısı tam limit kadar)
    kesik = bool(
        profil and profil.get("limit_var")
        and profil.get("limit_n") is not None
        and len(df) >= profil["limit_n"]
    )

    def _etiket(satir) -> str:
        """Çok-boyutlu etiket: 'İstanbul – Portakal Suyu 1L' (tüm boyutlar)."""
        return " – ".join(str(satir[b]) for b in boyutlar)

    # --- Boyut(lar) + ölçü varsa: LİSTE (soruyu doğrudan yanıtlar) + pay + yoğunlaşma ---
    if olcu and boyutlar and len(df) >= 1:
        kullan = boyutlar + [olcu]
        sirali = df[kullan].dropna(subset=[olcu]).sort_values(olcu, ascending=False).reset_index(drop=True)
        donen_toplam = float(sirali[olcu].sum())
        deg_h = _human(olcu)
        boyut_h = ", ".join(_human(b) for b in boyutlar)

        # Pay paydası (additivity kuralı — Kontrol 3):
        if not kesik:
            payda, kaynak, cekince = donen_toplam, "tam", None
        elif gercek_toplam and gercek_toplam > 0:
            payda, kaynak, cekince = float(gercek_toplam), "grand_total", None
        else:
            payda, kaynak = donen_toplam, "gosterilen"
            cekince = f"Sonuç ilk {profil.get('limit_n')} ile sınırlı; pay yalnızca gösterilenler içindir."
        # WHERE-filtreli sorguda payda 'tüm evren' DEĞİL, 'seçili kapsam'dır
        filtreli = bool((profil or {}).get("where_var"))
        if kaynak in ("tam", "grand_total"):
            kapsam = "seçili kapsamdaki" if filtreli else "tüm"
        else:
            kapsam = "gösterilenler içindeki"

        # 1) LİSTE — gerçek satırları çok-boyutlu etiketle sıralı listele.
        # D1: kullanıcı kaç istediyse o kadar göster (limit_n), 8-20 arası sınırla.
        istenen = (profil or {}).get("limit_n") or 8
        n_liste = min(len(sirali), max(int(istenen), 8), 20)
        liste = ", ".join(
            f"{_etiket(sirali.iloc[i])} ({_fmt(sirali.iloc[i][olcu])})" for i in range(n_liste)
        )
        if len(sirali) == 1:
            r0 = sirali.iloc[0]
            bulgular.append({
                "tip": "liste", "onem": 1.0, "gecerli": True, "deger": float(r0[olcu]),
                "olgu": f"{_etiket(r0)}: {_fmt(r0[olcu])} {deg_h}.",
            })
        else:
            bulgular.append({
                "tip": "liste", "onem": 1.0, "gecerli": True,
                "olgu": f"{deg_h.capitalize()} sıralaması ({boyut_h}): {liste}.",
            })

        # ADDITIVITY: pay/yoğunlaşma yalnızca TOPLANABİLİR ölçüde (SUM/COUNT)
        # anlamlıdır. AVG/ham fiyat gibi toplanamaz ölçülerde "pay" SAÇMADIR.
        toplanabilir = sql_kontrol.toplanabilir_mi(profil or {}, olcu)

        # 2) PAY — en yüksek kalemin doğru payda ile payı (metrik_test bunu okur)
        # 2 satırlı kıyasta pay gereksiz/yanıltıcı (kıyas bulgusu yeterli) → atla
        if toplanabilir and payda > 0 and len(sirali) != 2:
            ust = sirali.iloc[0]
            pay = ust[olcu] / payda * 100
            bulgular.append({
                "tip": "pay", "onem": 0.7 if pay >= 25 else 0.5,
                "gecerli": True, "payda_kaynagi": kaynak, "cekince": cekince,
                "deger": round(pay, 1), "payda": float(payda),
                "olgu": f"{_etiket(ust)}, {kapsam} {deg_h} ({_fmt(payda)}) içinde %{pay:.1f} pay tutuyor.",
            })

        # D5) KIYAS — 2 satırlı sonuçta YÖNÜ kod söyler (LLM'in ters yorumunu önler)
        if toplanabilir and len(sirali) == 2:
            a, b = sirali.iloc[0], sirali.iloc[1]
            if float(b[olcu]) > 0:
                oran = float(a[olcu]) / float(b[olcu])
                bulgular.append({
                    "tip": "kiyas", "onem": 0.85, "gecerli": True,
                    "olgu": (f"{_etiket(a)} ({_fmt(a[olcu])}), {_etiket(b)} "
                             f"({_fmt(b[olcu])})'den daha yüksek (≈{oran:.1f}x)."),
                })

        # 3) YOĞUNLAŞMA — toplanabilir ölçü + tam evren + yeterince satır
        if toplanabilir and not kesik and len(sirali) >= 5 and payda > 0:
            ilk3 = float(sirali.head(3)[olcu].sum())
            pareto = ilk3 / payda * 100
            bulgular.append({
                "tip": "yogunlasma", "onem": 0.55 if pareto >= 60 else 0.3,
                "gecerli": True, "payda_kaynagi": kaynak, "deger": round(pareto, 1),
                "olgu": f"İlk 3 {boyut_h}, {kapsam} {deg_h}in %{pareto:.1f}'ini oluşturuyor.",
            })

        # 4) ANOMALİ — toplanabilir ölçü + tam evren (IQR aykırı değer)
        if toplanabilir and not kesik and len(sirali) >= 5:
            q1, q3 = sirali[olcu].quantile(0.25), sirali[olcu].quantile(0.75)
            iqr = q3 - q1
            if iqr > 0:
                aykiri = sirali[sirali[olcu] > q3 + 1.5 * iqr]
                if not aykiri.empty:
                    adlar = ", ".join(_etiket(r) for _, r in aykiri.head(3).iterrows())
                    bulgular.append({
                        "tip": "anomali", "onem": 0.6, "gecerli": True,
                        "olgu": f"Olağandışı yüksek: {adlar} (diğerlerinden belirgin yüksek).",
                    })

    # --- Boyut yok ama ölçü var: tek değer (toplam/ortalama) ---
    elif olcu:
        m = ozet["metrikler"].get(olcu, {})
        if m:
            deg_h = _human(olcu)
            if len(df) == 1:
                olgu = f"{deg_h.capitalize()}: {_fmt(df.iloc[0][olcu])}."
            else:
                olgu = f"{deg_h.capitalize()} toplamı {_fmt(m['toplam'])}, ortalaması {_fmt(m['ortalama'])}."
            bulgular.append({
                "tip": "toplam", "onem": 0.9, "gecerli": True, "deger": float(m["toplam"]),
                "olgu": olgu,
            })

    # Hiçbir özel bulgu üretilemediyse en azından satır sayısını bildir (fallback)
    if not bulgular:
        bulgular.append({
            "tip": "satir", "onem": 0.2, "gecerli": True,
            "olgu": f"Sonuçta {_fmt(len(df))} kayıt bulundu.",
        })

    return ozet


# ---------- AŞAMA 2: İçgörü seçimi (kural tabanlı) ----------

def icgoru_sec(ozet: dict, k: int = 4) -> list[dict]:
    """En dikkat çekici k bulguyu önem skoruna göre seçer (LLM yok)."""
    bulgular = sorted(ozet.get("bulgular", []), key=lambda b: b["onem"], reverse=True)
    return bulgular[:k]


# ---------- AŞAMA 3: LLM anlatım ----------

def deterministik_ozet(secili_bulgular: list[dict]) -> str:
    """LLM'siz, garantili-sadık özet: olgu cümlelerini birleştirir.
    Olgular zaten kod tarafından üretilmiş, sayı/isim açısından %100 doğru."""
    return " ".join(b["olgu"] for b in secili_bulgular)


def anlat(soru: str, secili_bulgular: list[dict], llm) -> str:
    """Seçili olguları akıcı Türkçe özete çevirir.

    SADAKAT KAPISI: LLM anlatımı sayı VEYA isim uydurursa (faithfulness
    başarısız), o anlatım REDDEDİLİR ve garantili-doğru deterministik özete
    düşülür (graceful degradation). Böylece kullanıcı asla uydurma görmez.
    """
    if not secili_bulgular:
        return "Sorgu sonucunda yorumlanacak bir bulgu oluşmadı."
    if len(secili_bulgular) == 1 and secili_bulgular[0]["tip"] == "bos":
        return secili_bulgular[0]["olgu"]

    olgu_metni = "\n".join(f"- {b['olgu']}" for b in secili_bulgular)
    istem = prompt_yukle("rapor_ozet", soru=soru, olgular=olgu_metni)
    # Küçük modelde (3B) tekrar döngüsü + uydurma riskini azalt.
    ham = llm.cagir(
        sistem=istem, kullanici=soru,
        sicaklik=0.0, max_token=220,
        frequency_penalty=0.6, presence_penalty=0.4,
    )
    # Sadakat kapısı: uydurma sayı/isim varsa deterministik özete düş.
    sadik, _ = analiz_kontrol.sadakat_kontrol(ham, secili_bulgular)
    return ham if sadik else deterministik_ozet(secili_bulgular)


# ---------- Geriye dönük uyumluluk + tek-çağrı kolaylığı ----------

def raporla(soru: str, satirlar: list[dict], llm, k: int = 4,
            profil: dict | None = None, gercek_toplam: float | None = None) -> dict:
    """3 katmanı tek seferde çalıştırır; runner için kolaylık fonksiyonu.

    profil/gercek_toplam: Kontrol 3 girdileri (kesik sonuçta doğru pay için).
    Dönüş: { df, satir_sayisi, metrikler, bulgular, icgoruler, cekinceler, ozet_tr }
    """
    ozet = ozetle(satirlar, profil=profil, gercek_toplam=gercek_toplam)
    secili = icgoru_sec(ozet, k=k)
    ozet_tr = anlat(soru, secili, llm)
    cekinceler = [b["cekince"] for b in ozet["bulgular"] if b.get("cekince")]
    return {
        "df": ozet["df"],
        "satir_sayisi": ozet["satir_sayisi"],
        "metrikler": ozet["metrikler"],
        "bulgular": ozet["bulgular"],
        "icgoruler": [b["olgu"] for b in secili],
        "cekinceler": cekinceler,
        "ozet_tr": ozet_tr,
    }
