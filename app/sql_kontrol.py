"""
KONTROL 2 — Doğruluk Denetimi (çalıştırmadan ÖNCE, deterministik)
=================================================================

Güvenlik kontrolünden (Kontrol 1) geçmiş bir SELECT'i, ÇALIŞTIRMADAN önce iki
deterministik adımla denetler:

  A) statik_dogrula  → Şema grounding: SQL'deki tablo/kolonlar gerçekten var mı?
                       (LLM'in en yaygın hatası: olmayan kolon uydurmak.)
                       sqlglot AST ile tablo/kolon referansları çıkarılır,
                       sema.sema_yapisi() ile karşılaştırılır. LLM yok, ~ms.

  B) explain_dogrula → PostgreSQL EXPLAIN (ANALYZE'sız) ile dry-run: sorgu
                       ÇALIŞTIRILMADAN plan üretilebiliyor mu? Tablo/kolon/tip
                       uyumunu %100 garanti eder (statik'in kaçırdığı ince tip
                       hatalarını da yakalar), gerçek veriye dokunmaz.

İş bölümü: (A) ucuz ön-filtre + net hata mesajı (self-correction'a yem),
(B) veritabanı-kesin nihai kapı. İkisi de geçerse SQL çalıştırılır.
"""
import sqlglot
from sqlglot import expressions as exp

# Not: db_sorgu (asyncpg) yalnızca EXPLAIN için gerekir; statik_dogrula DB'siz
# çalışsın diye import explain_dogrula içinde tembel yapılır.


class KontrolHatasi(Exception):
    """Kontrol 2 denetiminden geçemeyen SQL için."""


# ---------- A) Şema grounding (deterministik, DB'siz) ----------

def statik_dogrula(sql: str, yapi: dict[str, set[str]]) -> tuple[bool, str]:
    """SQL'deki tablo/kolonların gerçekten şemada var olduğunu denetler.

    yapi: { tablo(küçük): {kolon(küçük), ...} }  (sema.sema_yapisi çıktısı)
    Dönüş: (gecti, hata_mesaji). gecti=True ise hata boş.

    Yaklaşım (yanlış-pozitifi düşük tutmak için bilinçli olarak hoşgörülü):
      - Tablolar: CTE adları hariç, kullanılan her tablo şemada olmalı.
      - Kolonlar: tüm şemadaki kolonların birleşimi + sorguda tanımlı
        takma adlar (AS) + CTE adları geçerli sayılır. Hiçbirinde olmayan
        kolon = uydurma. (Yanlış-tabloda-ama-var olan durumları EXPLAIN yakalar.)
    """
    try:
        agac = sqlglot.parse_one(sql, read="postgres")
    except Exception as e:  # noqa: BLE001
        return False, f"SQL ayrıştırılamadı: {e}"
    if agac is None:
        return False, "SQL boş/ayrıştırılamadı."

    gecerli_tablolar = set(yapi.keys())
    tum_kolonlar = {k for kolonlar in yapi.values() for k in kolonlar}

    # Sorguda tanımlı takma adlar (AS) ve CTE adları geçerli isim sayılır
    cte_adlari = {c.alias_or_name.lower() for c in agac.find_all(exp.CTE) if c.alias_or_name}
    takma_adlar = {a.alias.lower() for a in agac.find_all(exp.Alias) if a.alias}
    # Tablo takma adları (FROM satislar s → "s") kolon niteleyicisi olabilir
    tablo_takma = {
        t.alias.lower() for t in agac.find_all(exp.Table) if t.alias
    }

    # --- Tablo kontrolü ---
    for t in agac.find_all(exp.Table):
        ad = (t.name or "").lower()
        if not ad or ad in cte_adlari:
            continue
        if ad not in gecerli_tablolar:
            return False, f"Şemada olmayan tablo: '{t.name}'"

    # --- Kolon kontrolü ---
    gecerli_kolon_isimleri = tum_kolonlar | takma_adlar | cte_adlari
    for c in agac.find_all(exp.Column):
        ad = (c.name or "").lower()
        if not ad:
            continue
        if ad not in gecerli_kolon_isimleri:
            niteleyici = f"{c.table}." if c.table else ""
            return False, f"Şemada olmayan kolon: '{niteleyici}{c.name}'"

    return True, ""


# ---------- Sorgu profili (Kontrol 3 için: kesik/tam evren tespiti) ----------

def sorgu_profili(sql: str) -> dict:
    """SQL'in türetilmiş metrik açısından profilini çıkarır (AST, DB'siz).

    Pay/oran gibi metriklerin geçerliliği için sonucun TAM evren mi yoksa
    kesik (top-N/LIMIT) mi olduğunu anlamak gerekir.

    Dönüş: {
      "limit_var": bool, "limit_n": int|None,
      "where_var": bool, "group_by_var": bool, "order_var": bool,
    }
    """
    bos = {"limit_var": False, "limit_n": None, "where_var": False,
           "group_by_var": False, "order_var": False}
    try:
        agac = sqlglot.parse_one(sql, read="postgres")
    except Exception:  # noqa: BLE001
        return bos
    if agac is None:
        return bos

    limit = agac.args.get("limit")
    limit_n = None
    if limit is not None:
        try:
            limit_n = int(limit.expression.name)
        except (AttributeError, ValueError):
            limit_n = None

    # Ölçü kolonlarının toplanabilirlik tipini çıkar (additivity):
    #   SUM/COUNT → toplanabilir (pay/yoğunlaşma anlamlı)
    #   AVG/MIN/MAX → toplanamaz; ham kolon → toplanamaz (pay anlamsız)
    olculer: dict[str, str] = {}
    for sel in (agac.selects or []):
        alias = (sel.alias_or_name or "").lower()
        if not alias:
            continue
        ic = sel.this if isinstance(sel, exp.Alias) else sel
        if isinstance(ic, exp.Sum):
            olculer[alias] = "sum"
        elif isinstance(ic, exp.Count):
            olculer[alias] = "count"
        elif isinstance(ic, exp.Avg):
            olculer[alias] = "avg"
        elif isinstance(ic, (exp.Min, exp.Max)):
            olculer[alias] = "minmax"
        elif isinstance(ic, exp.Column):
            olculer[alias] = "raw"
        else:
            olculer[alias] = "other"

    return {
        "limit_var": limit is not None,
        "limit_n": limit_n,
        "where_var": agac.find(exp.Where) is not None,
        "group_by_var": agac.find(exp.Group) is not None,
        "order_var": agac.args.get("order") is not None,
        "olculer": olculer,
    }


def toplanabilir_mi(profil: dict, olcu_kolon: str) -> bool:
    """Ölçü kolonu pay/yoğunlaşma için toplanabilir mi? (SUM/COUNT → evet)."""
    tip = (profil.get("olculer") or {}).get((olcu_kolon or "").lower())
    return tip in ("sum", "count")


# ---------- B) EXPLAIN dry-run (veritabanı-kesin) ----------

async def explain_dogrula(sql: str) -> tuple[bool, str]:
    """PostgreSQL EXPLAIN ile sorguyu ÇALIŞTIRMADAN doğrular.

    EXPLAIN (ANALYZE olmadan) sorguyu yürütmez, yalnızca plan üretir; var
    olmayan tablo/kolon veya tip uyumsuzluğunda plan-zamanında hata fırlatır.
    Dönüş: (gecti, hata_mesaji).
    """
    import db_sorgu  # tembel import: statik katmanı asyncpg'den bağımsız tutar
    try:
        async with db_sorgu.baglanti() as conn:
            async with conn.transaction(readonly=True):
                await conn.execute(f"EXPLAIN {sql}")
        return True, ""
    except Exception as e:  # noqa: BLE001 — her plan hatası = doğrulama başarısız
        return False, f"EXPLAIN başarısız: {e}"


# ---------- Birleştirici ----------

async def kontrol2(sql: str, yapi: dict[str, set[str]]) -> tuple[bool, str]:
    """Kontrol 2'nin tamamı: önce statik grounding, sonra EXPLAIN dry-run.

    Statik kontrol DB'siz ve ucuz olduğu için önce çalışır (hızlı eleme +
    net hata mesajı). Geçerse EXPLAIN ile veritabanı-kesin doğrulama yapılır.
    Dönüş: (gecti, hata_mesaji).
    """
    gecti, hata = statik_dogrula(sql, yapi)
    if not gecti:
        return False, hata
    return await explain_dogrula(sql)
