"""
KONTROL 3 — Analiz Doğrulama (türetilmiş metrik güvenliği)
==========================================================

SQL doğru çalışsa bile, sonuçtan TÜRETİLEN metrikler (pay/yüzde, oran) semantik
yanlış olabilir. Klasik hata: LIMIT'li (top-N) sonuçta 'toplam içinde pay'
hesaplarken paydayı yalnızca dönen satırların toplamı almak.

Bu modül iki deterministik araç sunar:
  A) grand_total_sql  → Kesik sonuçta DOĞRU paydayı (grand total) ayrı, güvenli
                        bir agregat sorgusuyla çekmek için SQL üretir.
  B) sadakat_kontrol  → Üretilen Türkçe anlatımdaki sayıların yapılandırılmış
                        olgulardan geldiğini doğrular (numeric faithfulness).
"""
import re

import sqlglot
from sqlglot import expressions as exp


def _str_literal(node) -> bool:
    return isinstance(node, exp.Literal) and node.is_string


def _norm_kol(kol_sql: str) -> str:
    """Kolonu Türkçe-güvenli normalize eder: lower(unaccent(col)).
    DİKKAT sıra: önce unaccent (Ç→C), sonra lower (C→c). lower(Ç) Türkçe-dışı
    locale'de Ç'yi küçültmez; bu yüzden unaccent ÖNCE gelir."""
    return f"lower(unaccent({kol_sql}))"


def _norm_lit(deger: str) -> str:
    d = str(deger).replace("'", "''")
    return f"lower(unaccent('{d}'))"


def _kelime_basi_kosul(kol_sql: str, deger: str):
    """TAM-KELİME + Türkçe-güvenli eşleşme:
        lower(unaccent(col)) ~ ('\\m' || lower(unaccent('<deger>')) || '\\M')
    Tam-kelime sınırı (\\m..\\M) over-match'i önler:
      'su'  → 'Su 5L' tutar, 'Maden Suyu'/'Portakal Suyu' TUTMAZ (suyu=meyve suyu)
      'süt' → 'Süt 1L' tutar, 'Sütaş' (marka) TUTMAZ
      'kola'→ 'Kola 1L' tutar, 'Çikolata' TUTMAZ
      'çay' → 'Çay 1kg' ve 'Soğuk Çay 1L' (her ikisi de tam kelime)."""
    return sqlglot.condition(
        rf"{_norm_kol(kol_sql)} ~ ('\m' || {_norm_lit(deger.strip())} || '\M')",
        dialect="postgres",
    )


def _esit_kosul(kol_sql: str, deger: str):
    """Türkçe-güvenli EŞİTLİK: lower(unaccent(col)) = lower(unaccent('<deger>')).
    'Istanbul' (ascii) = 'İstanbul' (Türkçe) eşleşir."""
    return sqlglot.condition(
        f"{_norm_kol(kol_sql)} = {_norm_lit(deger.strip())}",
        dialect="postgres",
    )


def normalle_substring(sql: str) -> str:
    """HER sorguda uygulanan TÜRKÇE-GÜVENLİ + over-match önleyen normalizasyon:

      col LIKE/ILIKE '%X%'  →  lower(unaccent(col)) ~ '\\m'||lower(unaccent('X'))
                               (kelime-başı: 'kola'≠'çikolata'; Türkçe katlama: 'çay'='Çay')
      col = 'X' (metin)     →  lower(unaccent(col)) = lower(unaccent('X'))
                               ('Istanbul'='İstanbul'; ç/ş/ğ/ı/ö/ü harf-duyarsız)

    Sayı/tarih karşılaştırmalarına ve kolon=kolon JOIN'lerine dokunmaz.
    """
    try:
        agac = sqlglot.parse_one(sql, read="postgres")
    except Exception:  # noqa: BLE001
        return sql
    if agac is None:
        return sql
    degisti = False

    # 1) substring LIKE/ILIKE '%X%' → kelime-başı Türkçe-güvenli
    for lk in list(agac.find_all(exp.Like, exp.ILike)):
        kol = lk.this if isinstance(lk.this, exp.Column) else None
        lit = lk.expression if _str_literal(lk.expression) else None
        if kol is None or lit is None:
            continue
        v = str(lit.this)
        ic = v.strip("%")
        if v.startswith("%") and v.endswith("%") and "%" not in ic and ic:
            lk.replace(_kelime_basi_kosul(kol.sql(dialect="postgres"), ic))
            degisti = True

    # 2) metin eşitliği col = 'X' → Türkçe-güvenli eşitlik
    for eq in list(agac.find_all(exp.EQ)):
        kol = eq.this if isinstance(eq.this, exp.Column) else (
            eq.expression if isinstance(eq.expression, exp.Column) else None)
        lit = eq.expression if _str_literal(eq.expression) else (
            eq.this if _str_literal(eq.this) else None)
        if kol is not None and lit is not None:
            eq.replace(_esit_kosul(kol.sql(dialect="postgres"), str(lit.this)))
            degisti = True

    return agac.sql(dialect="postgres") if degisti else sql


def gevset_metin_filtreleri(sql: str) -> str | None:
    """D2 — Boş-sonuç kurtarma: metin eşitlik/LIKE filtrelerini gevşetir.

    col = 'Kola'  →  col ~* '\\mKola'  (kelime başı, harf-duyarsız)
    col LIKE 'X'  →  col ~* '\\mX'

    Substring (%X%) DEĞİL kelime-başı kullanılır; böylece 'kola' → 'çikolata'
    gibi yanlış eşleşmeler önlenir. Yalnızca STRING literal'lere dokunur.
    Değişiklik olmazsa None döner.
    """
    try:
        agac = sqlglot.parse_one(sql, read="postgres")
    except Exception:  # noqa: BLE001
        return None
    if agac is None:
        return None

    degisti = False

    # (a) Normalize edilmiş eşitlik: lower(unaccent(col)) = lower(unaccent('x'))
    #     → kelime-başı içerir: ... ~ ('\m' || lower(unaccent('x')))
    for eq in list(agac.find_all(exp.EQ)):
        sol, sag = eq.this, eq.expression
        if isinstance(sol, exp.Lower) and isinstance(sag, exp.Lower):
            yeni = sqlglot.condition(
                rf"{sol.sql('postgres')} ~ ('\m' || {sag.sql('postgres')})",
                dialect="postgres")
            eq.replace(yeni)
            degisti = True
            continue
        # (b) Ham eşitlik col = 'x' (normalize edilmemişse)
        kol = sol if isinstance(sol, exp.Column) else (sag if isinstance(sag, exp.Column) else None)
        lit = sag if _str_literal(sag) else (sol if _str_literal(sol) else None)
        if kol is not None and lit is not None:
            eq.replace(_kelime_basi_kosul(kol.sql(dialect="postgres"), str(lit.this)))
            degisti = True

    # (c) Joker'siz LIKE col LIKE 'x' → kelime-başı
    for lk in list(agac.find_all(exp.Like, exp.ILike)):
        kol = lk.this if isinstance(lk.this, exp.Column) else None
        lit = lk.expression if _str_literal(lk.expression) else None
        if kol is not None and lit is not None and "%" not in str(lit.this):
            lk.replace(_kelime_basi_kosul(kol.sql(dialect="postgres"), str(lit.this)))
            degisti = True

    return agac.sql(dialect="postgres") if degisti else None


def grand_total_sql(orijinal_sql: str, olcu_kolon: str) -> str | None:
    """Orijinal SELECT'ten ORDER BY + LIMIT çıkarıp grand total sorgusu üretir:
        SELECT SUM(t."<olcu>") AS gercek_toplam FROM ( <orijinal, limit/order yok> ) t

    Bu türetilmiş sorgu da SELECT'tir → Kontrol 1 + Kontrol 2'den geçer.
    Üretilemezse None döner (pay bastırılır).
    """
    try:
        agac = sqlglot.parse_one(orijinal_sql, read="postgres")
        agac.set("limit", None)
        agac.set("order", None)
        ic = agac.sql(dialect="postgres")
    except Exception:  # noqa: BLE001
        return None
    # Kolon adını güvenli biçimde tırnakla (alias'lar basit ama garanti olsun)
    kol = olcu_kolon.replace('"', '')
    return f'SELECT SUM(t."{kol}") AS gercek_toplam FROM ({ic}) t'


# --- Sayısal sadakat (faithfulness) ---

# "Önemli" sayı: ayraç (. ,) veya % içeren ya da 3+ basamaklı.
# Küçük tamsayılar (1-2 basamak) yok sayılır (false-positive azaltır).
_SAYI = re.compile(r"%?\s?\d[\d.,]*")


def _normalize(tok: str) -> str | None:
    """Sayı token'ını karşılaştırılabilir saf rakam dizisine indirger."""
    cekirdek = tok.replace("%", "").replace(" ", "")
    rakam = re.sub(r"[.,]", "", cekirdek)
    if not rakam.isdigit():
        return None
    # Önemlilik filtresi: ayraç/%/3+ basamak
    onemli = ("." in cekirdek) or ("," in cekirdek) or ("%" in tok) or (len(rakam) >= 3)
    return rakam if onemli else None


def _sayilar(metin: str) -> set[str]:
    out = set()
    for m in _SAYI.findall(metin or ""):
        n = _normalize(m)
        if n:
            out.add(n)
    return out


# Cümle başı/bağlaç gibi büyük harfle başlayabilen ama isim olmayan kelimeler
_DURAK = {
    "bunlar", "ayrıca", "ancak", "fakat", "sonuç", "ayrica",
    "buna", "böylece", "boylece", "ilki", "ikinci", "üçüncü", "ucuncu",
    "diğer", "diger", "diğerleri", "digerleri", "yüksek", "yuksek", "düşük",
    "dusuk", "toplam", "ortalama", "kayıt", "kayit", "değer", "deger",
}
# Büyük harfle başlayan (özel-isim benzeri) 4+ harfli kelime
_OZELISIM = re.compile(r"[A-ZÇĞİÖŞÜ][\wçğıöşüİ]{3,}")


def _uydurma_isimler(ozet_metni: str, olgu_metni: str) -> list[str]:
    """Anlatımda geçen, olgularda OLMAYAN özel-isim benzeri kelimeler.
    (İsim halüsinasyonu: 'İspanya Şekerli Su' gibi uydurma ürün adları.)"""
    olgu_l = olgu_metni.lower()
    bulunan = []
    for k in _OZELISIM.findall(ozet_metni):
        kl = k.lower()
        if kl in _DURAK:
            continue
        if kl not in olgu_l:  # olgularda hiç geçmiyorsa → uydurma şüphesi
            bulunan.append(k)
    return bulunan


def sadakat_kontrol(ozet_metni: str, olgular: list[dict]) -> tuple[bool, list[str]]:
    """Anlatımın olgulara sadakatini denetler (numeric + entity faithfulness).

    İki kontrol:
      1) Sayılar: anlatımdaki her önemli sayı olgularda var mı?
      2) İsimler: anlatımda olgularda olmayan özel-isim (ürün/marka/şehir) var mı?

    Dönüş: (sadik_mi, sorunlar). sorunlar = uydurma sayı + uydurma isim listesi.
    """
    olgu_metni = " ".join(o.get("olgu", "") for o in olgular)
    uydurma_sayi = sorted(_sayilar(ozet_metni) - _sayilar(olgu_metni))
    uydurma_isim = _uydurma_isimler(ozet_metni, olgu_metni)
    sorunlar = uydurma_sayi + uydurma_isim
    return (len(sorunlar) == 0, sorunlar)
