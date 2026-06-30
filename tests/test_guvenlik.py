"""
SQL Güvenlik Katmanı — Birim Testi
===================================

Bağımsız çalışır (DB/model gerektirmez). Kötü niyetli girdilerin reddedildiğini,
geçerli SELECT'lerin geçtiğini ve LIMIT'in zorlandığını doğrular.

Çalıştırma:  python test_guvenlik.py
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from sql_guvenlik import GuvenlikHatasi, dogrula_ve_hazirla

# (sql, gecmeli_mi) çiftleri
DURUMLAR = [
    # --- Geçmesi gerekenler ---
    ("SELECT * FROM satislar", True),
    ("SELECT u.ad, SUM(s.adet) FROM satislar s JOIN urunler u ON u.id=s.urun_id GROUP BY u.ad", True),
    ("WITH t AS (SELECT * FROM satislar) SELECT * FROM t", True),
    ("SELECT * FROM a UNION SELECT * FROM b", True),
    # --- Reddedilmesi gerekenler ---
    ("DROP TABLE satislar", False),
    ("DELETE FROM satislar", False),
    ("UPDATE satislar SET adet=0", False),
    ("INSERT INTO satislar VALUES (1)", False),
    ("SELECT 1; DELETE FROM satislar", False),               # çoklu statement
    ("TRUNCATE satislar", False),
    ("ALTER TABLE satislar ADD COLUMN x int", False),
    ("WITH x AS (INSERT INTO a VALUES(1) RETURNING *) SELECT * FROM x", False),  # CTE içi yazma
    ("SELECT pg_sleep(10)", False),                          # DoS fonksiyonu
    ("SELECT * FROM pg_read_file('/etc/passwd')", False),     # dosya okuma
    ("GRANT SELECT ON satislar TO public", False),
]


def main() -> None:
    basari = 0
    for sql, beklenen in DURUMLAR:
        try:
            sonuc = dogrula_ve_hazirla(sql, satir_limiti=100)
            gecti = True
        except GuvenlikHatasi:
            gecti = False
        dogru = gecti == beklenen
        basari += dogru
        isaret = "✓" if dogru else "✗ BAŞARISIZ"
        durum = "geçti" if gecti else "reddedildi"
        print(f"  {isaret}  [{durum:10}] {sql[:60]}")

    # LIMIT zorlama kontrolü
    limitli = dogrula_ve_hazirla("SELECT * FROM satislar", satir_limiti=50)
    limit_ok = "LIMIT 50" in limitli.upper().replace("  ", " ")
    print(f"\n  {'✓' if limit_ok else '✗'}  LIMIT otomatik eklendi: {limitli}")

    print(f"\n=== {basari}/{len(DURUMLAR)} test geçti (+ LIMIT: {limit_ok}) ===")


if __name__ == "__main__":
    main()
