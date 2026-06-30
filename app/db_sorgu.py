"""
Read-only Sorgu Katmanı (asyncpg)
==================================

Şirket veritabanına YALNIZCA SELECT için bağlanır. fabrika/db.py deseninin
salt-okunur sürümü. İki ayrı bağlantı kullanılır:

  * SORGU_DATABASE_URL  → readonly_user (yalnızca SELECT GRANT'i olan),
                          tercihen read replica. Asıl analitik sorgular burada.

Güvenlik (Katman 3): pool seviyesinde her oturuma salt-okunur transaction +
statement_timeout + idle_in_transaction_session_timeout zorlanır. Böylece
uygulama hatası olsa bile DB tarafında yazma fiziksel olarak engellenir.
"""
import os
from decimal import Decimal
import asyncpg
from contextlib import asynccontextmanager

_havuz: asyncpg.Pool | None = None

# Salt-okunur sorgu bağlantısı (readonly_user). Faz1 yerel geliştirmede
# normal DATABASE_URL'e düşülebilir ama PROD'da mutlaka readonly olmalı.
SORGU_DSN = os.environ.get("SORGU_DATABASE_URL") or os.environ.get("DATABASE_URL", "")
ZAMAN_ASIMI_MS = int(os.environ.get("SORGU_TIMEOUT_MS", "8000"))
SATIR_LIMITI = int(os.environ.get("SORGU_SATIR_LIMITI", "1000"))


async def havuz() -> asyncpg.Pool:
    """Salt-okunur bağlantı havuzunu (lazy) döndürür."""
    global _havuz
    if _havuz is None:
        if not SORGU_DSN:
            raise RuntimeError(
                "SORGU_DATABASE_URL (veya DATABASE_URL) tanımlı değil."
            )
        _havuz = await asyncpg.create_pool(
            SORGU_DSN,
            min_size=1,
            max_size=5,
            # Oturum düzeyinde güvenlik: salt-okuma + zaman aşımı
            server_settings={
                "statement_timeout": str(ZAMAN_ASIMI_MS),
                "default_transaction_read_only": "on",
                "idle_in_transaction_session_timeout": "10000",
            },
        )
    return _havuz


@asynccontextmanager
async def baglanti():
    h = await havuz()
    async with h.acquire() as c:
        yield c


async def calistir_select(sql: str) -> list[dict]:
    """Doğrulanmış bir SELECT'i salt-okunur transaction içinde çalıştırır.

    DİKKAT: Buraya gelen SQL'in sql_guvenlik.dogrula_ve_hazirla()'dan
    GEÇMİŞ olması beklenir. Bu fonksiyon ek güvenlik için read-only
    transaction kullanır ama doğrulamayı kendisi yapmaz.
    """
    async with baglanti() as c:
        async with c.transaction(readonly=True):
            satirlar = await c.fetch(sql)
            return [_satir_donustur(s) for s in satirlar[:SATIR_LIMITI]]


def _satir_donustur(satir) -> dict:
    """asyncpg Record'u dict'e çevirir; PostgreSQL NUMERIC (Decimal) değerlerini
    float'a indirger. Aksi halde pandas Decimal'i 'object' sayar (metrikler
    hesaplanmaz) ve JSON serileştirme bozulur.
    """
    d = {}
    for k, v in dict(satir).items():
        d[k] = float(v) if isinstance(v, Decimal) else v
    return d


async def kapat() -> None:
    """Havuzu kapatır (uygulama kapanışında)."""
    global _havuz
    if _havuz is not None:
        await _havuz.close()
        _havuz = None
