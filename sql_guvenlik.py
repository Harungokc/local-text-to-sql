"""
SQL Güvenlik Katmanı (Uygulama düzeyi — Katman 2)
==================================================

LLM'in ürettiği SQL'i ÇALIŞTIRMADAN ÖNCE doğrular. Amaç: yalnızca tek bir
salt-okunur SELECT sorgusunun geçmesini sağlamak. String/regex yerine sqlglot
ile gerçek AST parse yapılır — "DROP TABLE", gizli "; DELETE", CTE içine
saklanmış INSERT gibi saldırılar AST düzeyinde yakalanır.

Bu katman tek başına yeterli DEĞİLDİR; veritabanı düzeyinde salt-okunur
kullanıcı (Katman 1) + pool zaman aşımı (Katman 3) ile birlikte çalışır.
"""
import sqlglot
from sqlglot import expressions as exp

# Çalıştırılmasına ASLA izin verilmeyen ifade türleri (yazma + DDL + komut)
YASAK_IFADELER = (
    exp.Insert, exp.Update, exp.Delete, exp.Merge,
    exp.Drop, exp.Create, exp.Alter, exp.TruncateTable,
    exp.Command,        # GRANT/REVOKE/SET/VACUUM gibi ham komutlar
)

# Kök ifade olarak kabul edilen güvenli türler (salt okuma)
GUVENLI_KOK = (exp.Select, exp.Union, exp.With, exp.Subquery)

# Read-only kullanıcıda bile istenmeyen tehlikeli fonksiyonlar
# (DoS, dosya okuma, ağ üzerinden veri kaçırma)
YASAK_FONKSIYONLAR = {
    "pg_sleep", "pg_read_file", "pg_read_binary_file", "pg_ls_dir",
    "lo_import", "lo_export", "dblink", "dblink_exec",
    "copy", "pg_terminate_backend", "pg_cancel_backend", "current_setting",
    "set_config", "query_to_xml",
}


class GuvenlikHatasi(Exception):
    """SQL güvenlik doğrulamasından geçemediğinde fırlatılır."""


def dogrula_ve_hazirla(ham_sql: str, satir_limiti: int = 1000) -> str:
    """Ham SQL'i doğrular ve güvenli, LIMIT'li tek SELECT metnine dönüştürür.

    Adımlar:
      1) Parse edilebilir mi + tek statement mı? (çoklu/;-birleştirme engeli)
      2) Kök ifade SELECT / WITH / UNION mı?
      3) Ağaçta yazma veya DDL alt-ifadesi var mı? (CTE içi gizli yazma)
      4) Tehlikeli fonksiyon çağrısı var mı?
      5) LIMIT yoksa otomatik ekle.

    Dönüş: güvenli, normalize edilmiş PostgreSQL SELECT metni.
    Hata: GuvenlikHatasi.
    """
    if not ham_sql or not ham_sql.strip():
        raise GuvenlikHatasi("Boş SQL.")

    # --- 1) Parse + tek statement ---
    try:
        ifadeler = sqlglot.parse(ham_sql, read="postgres")
    except Exception as e:  # noqa: BLE001 — parse hatası = güvensiz say
        raise GuvenlikHatasi(f"SQL parse edilemedi: {e}") from e

    ifadeler = [i for i in ifadeler if i is not None]
    if len(ifadeler) != 1:
        raise GuvenlikHatasi(
            f"Yalnızca tek SELECT ifadesine izin var (bulunan: {len(ifadeler)})."
        )
    agac = ifadeler[0]

    # --- 2) Kök ifade salt-okuma türünde mi? ---
    if not isinstance(agac, GUVENLI_KOK):
        raise GuvenlikHatasi(
            f"Yalnızca SELECT sorgularına izin var (kök: {type(agac).__name__})."
        )

    # WITH ise nihai gövdesi SELECT/UNION olmalı (WITH ... INSERT engeli)
    if isinstance(agac, exp.With):
        govde = agac.this
        if not isinstance(govde, (exp.Select, exp.Union)):
            raise GuvenlikHatasi("WITH ifadesinin gövdesi SELECT olmalı.")

    # --- 3) Ağaçta yazma/DDL alt-ifade taraması ---
    for dugum in agac.walk():
        if isinstance(dugum, YASAK_IFADELER):
            raise GuvenlikHatasi(
                f"Yasak ifade tespit edildi: {type(dugum).__name__}"
            )

    # --- 4) Tehlikeli fonksiyon taraması ---
    for fonk in agac.find_all(exp.Anonymous, exp.Func):
        ad = (fonk.name or "").lower()
        if ad in YASAK_FONKSIYONLAR:
            raise GuvenlikHatasi(f"Yasak fonksiyon: {ad}")

    # --- 5) LIMIT zorla (yalnızca düz SELECT'te; UNION/WITH'i sarmalarız) ---
    if isinstance(agac, exp.Select):
        if not agac.args.get("limit"):
            agac = agac.limit(satir_limiti)
    else:
        # UNION veya WITH: dış SELECT ile sarmalayıp LIMIT uygula
        agac = exp.select("*").from_(agac.subquery("alt")).limit(satir_limiti)

    return agac.sql(dialect="postgres")
