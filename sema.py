"""
Şema Modülü — Introspection + Şema Linkleme
============================================

İki iş yapar:
  1) Veritabanı şemasını information_schema'dan okuyup her tablo için
     LLM'e verilecek okunaklı bir DDL metni üretir (kolon adı + tip + yorum).
  2) Şema linkleme: bir soruya göre YALNIZCA ilgili tabloları seçer. Tüm
     şemayı prompt'a basmak yerine ilgili tabloları vermek, küçük modelin
     context'ini boğmaz ve doğruluğu artırır (raporun ana tezi).

Faz 1'de linkleme hafif (anahtar kelime + few-shot ipuçları). Faz 3'te
LLM-tabanlı daraltma eklenebilir.
"""
import re
from db_sorgu import baglanti

# Şema önbelleği (introspection görece pahalı; süreç boyunca sabit kabul edilir)
_ddl_onbellek: dict[str, str] | None = None
# Yapısal şema önbelleği: { tablo_adi(küçük): {kolon_adı(küçük), ...} }
_yapi_onbellek: dict[str, set[str]] | None = None
# Değer ipuçları önbelleği (value linking: düşük-kardinaliteli metin kolonları)
_deger_onbellek: str | None = None


async def sema_ddl_getir(yenile: bool = False) -> dict[str, str]:
    """Her tablo için { tablo_adi: "CREATE TABLE ... (kolonlar)" } döndürür.

    Yorum (COMMENT) varsa kolonun yanına eklenir — model için bağlam.
    """
    global _ddl_onbellek, _yapi_onbellek
    if _ddl_onbellek is not None and not yenile:
        return _ddl_onbellek

    sorgu = """
        SELECT
            c.table_name,
            c.column_name,
            c.data_type,
            c.is_nullable,
            col_description(
                format('%I.%I', c.table_schema, c.table_name)::regclass::oid,
                c.ordinal_position
            ) AS yorum
        FROM information_schema.columns c
        WHERE c.table_schema = 'public'
        ORDER BY c.table_name, c.ordinal_position
    """
    tablolar: dict[str, list[str]] = {}
    yapi: dict[str, set[str]] = {}
    async with baglanti() as conn:
        async with conn.transaction(readonly=True):
            satirlar = await conn.fetch(sorgu)

    for s in satirlar:
        tablo = s["table_name"]
        satir = f"  {s['column_name']} {s['data_type']}"
        if s["is_nullable"] == "NO":
            satir += " NOT NULL"
        if s["yorum"]:
            satir += f"  -- {s['yorum']}"
        tablolar.setdefault(tablo, []).append(satir)
        # Yapısal şema (grounding için): küçük harfle tablo→kolon kümesi
        yapi.setdefault(tablo.lower(), set()).add(s["column_name"].lower())

    _ddl_onbellek = {
        ad: f"CREATE TABLE {ad} (\n" + ",\n".join(kolonlar) + "\n);"
        for ad, kolonlar in tablolar.items()
    }
    _yapi_onbellek = yapi
    return _ddl_onbellek


async def sema_yapisi(yenile: bool = False) -> dict[str, set[str]]:
    """Yapısal şemayı döndürür: { tablo_adi(küçük): {kolon(küçük), ...} }.

    sql_kontrol.py'deki şema grounding (uydurma tablo/kolon tespiti) için.
    Önbellek doluysa onu kullanır; değilse introspection'ı tetikler.
    """
    if _yapi_onbellek is None or yenile:
        await sema_ddl_getir(yenile=yenile)
    return _yapi_onbellek or {}


async def deger_ipuclari(maks_essiz: int = 40, yenile: bool = False) -> str:
    """Value linking: düşük-kardinaliteli metin kolonlarının GERÇEK değerlerini
    listeler. Böylece model 'Temizlik'in kategoriler.ad, 'İzmir'in magazalar.sehir
    değeri olduğunu bilir ve doğru tabloyu join'leyip doğru filtreyi kurar.

    Sadece essiz_sayisi <= maks_essiz olan text/varchar kolonları dahil edilir
    (büyük tablolarda dökülme olmaz). Süreç boyunca önbelleklenir.

    Dönüş örn.:
        ## Bilinen Sütun Değerleri (filtrelerde bunları birebir kullan)
        - kategoriler.ad: İçecek, Atıştırmalık, Süt Ürünleri, Kahvaltılık, Temizlik
        - magazalar.sehir: Ankara, Antalya, Bursa, İstanbul, İzmir
    """
    global _deger_onbellek
    if _deger_onbellek is not None and not yenile:
        return _deger_onbellek

    # public şemadaki metin kolonlarını bul
    kolon_sorgu = """
        SELECT table_name, column_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND data_type IN ('text', 'character varying', 'character')
        ORDER BY table_name, ordinal_position
    """
    satirlar_meta: list[str] = []
    async with baglanti() as conn:
        async with conn.transaction(readonly=True):
            kolonlar = await conn.fetch(kolon_sorgu)
            for k in kolonlar:
                t, c = k["table_name"], k["column_name"]
                # Essiz değer sayısı eşiği aşmıyorsa değerleri çek (tablo/kolon adları
                # introspection'dan geldi, enjeksiyon riski yok ama yine de %I ile kotala)
                say = await conn.fetchval(
                    f'SELECT COUNT(DISTINCT "{c}") FROM "{t}"'
                )
                if say is None or say == 0 or say > maks_essiz:
                    continue
                degerler = await conn.fetch(
                    f'SELECT DISTINCT "{c}" AS v FROM "{t}" '
                    f'WHERE "{c}" IS NOT NULL ORDER BY 1'
                )
                vlist = ", ".join(str(d["v"]) for d in degerler)
                satirlar_meta.append(f"- {t}.{c}: {vlist}")

    if satirlar_meta:
        _deger_onbellek = (
            "## Bilinen Sütun Değerleri (filtrelerde bunları birebir kullan; "
            "bir değer hangi kolonda ise O tabloyu join'le)\n"
            + "\n".join(satirlar_meta)
        )
    else:
        _deger_onbellek = ""
    return _deger_onbellek


def _kelimeler(metin: str) -> set[str]:
    """Türkçe + İngilizce kaba tokenizasyon (küçük harf, 3+ karakter)."""
    return {k for k in re.findall(r"\w+", metin.lower()) if len(k) >= 3}


async def ilgili_tablolar(
    soru: str,
    tum_ddl: dict[str, str] | None = None,
    ornek_tablolar: list[str] | None = None,
    maks_tablo: int = 8,
) -> list[str]:
    """Soruyla ilgili tabloları seçer (şema linkleme).

    Strateji (Faz 1, LLM'siz, hızlı):
      1) Few-shot örneklerinden gelen tablo ipuçlarını öncele (ornek_tablolar).
      2) Soru kelimeleriyle tablo adı/kolon adı eşleşmesine göre puanla.
      3) Hiç eşleşme yoksa tüm tabloları döndür (küçük şemada güvenli varsayılan).

    Dönüş: ilgili tablo adları (en çok maks_tablo).
    """
    if tum_ddl is None:
        tum_ddl = await sema_ddl_getir()

    soru_kelime = _kelimeler(soru)
    puan: dict[str, int] = {}

    for tablo, ddl in tum_ddl.items():
        p = 0
        # Tablo adı eşleşmesi güçlü sinyal
        if _kelimeler(tablo) & soru_kelime:
            p += 5
        # Kolon adı eşleşmeleri
        p += len(_kelimeler(ddl) & soru_kelime)
        if p:
            puan[tablo] = p

    # Few-shot örneklerinden gelen tablolar öncelikli
    for t in (ornek_tablolar or []):
        if t in tum_ddl:
            puan[t] = puan.get(t, 0) + 3

    if not puan:
        # Eşleşme yok → küçük şemada tümünü ver (büyük şemada Faz3 LLM-linkleme)
        return list(tum_ddl.keys())[:maks_tablo]

    siralanmis = sorted(puan, key=puan.get, reverse=True)
    return siralanmis[:maks_tablo]


def ddl_metni(tablolar: list[str], tum_ddl: dict[str, str]) -> str:
    """Seçili tabloların DDL'ini tek bir metin bloğunda birleştirir."""
    return "\n\n".join(tum_ddl[t] for t in tablolar if t in tum_ddl)
