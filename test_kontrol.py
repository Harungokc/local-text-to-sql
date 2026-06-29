"""
KONTROL 2 — Şema Grounding Birim Testi (statik_dogrula)
========================================================

Bağımsız çalışır (DB/model gerektirmez). EXPLAIN dry-run kısmı veritabanı
gerektirdiği için uçtan uca testte doğrulanır; burada deterministik şema
grounding (uydurma tablo/kolon tespiti) test edilir.

Çalıştırma:  python test_kontrol.py
"""
from sql_kontrol import statik_dogrula

# Örnek şema: { tablo: {kolonlar} }
YAPI = {
    "satislar": {"id", "tarih", "adet", "birim_fiyat", "urun_id", "magaza_id"},
    "urunler": {"id", "ad", "kategori_id"},
    "magazalar": {"id", "ad", "sehir"},
}

# (sql, gecmeli_mi, aciklama)
DURUMLAR = [
    # --- Geçmesi gerekenler ---
    ("SELECT ad FROM urunler", True, "basit geçerli"),
    ("SELECT u.ad, SUM(s.adet) FROM satislar s JOIN urunler u ON u.id=s.urun_id GROUP BY u.ad",
     True, "JOIN + agregasyon, gerçek kolonlar"),
    ("SELECT urun_id, SUM(adet) AS toplam FROM satislar GROUP BY urun_id ORDER BY toplam DESC",
     True, "AS takma adı (toplam) geçerli sayılmalı"),
    ("SELECT m.sehir, COUNT(*) FROM magazalar m GROUP BY m.sehir", True, "COUNT(*) + gerçek kolon"),
    ("WITH t AS (SELECT urun_id, SUM(adet) AS top FROM satislar GROUP BY urun_id) SELECT * FROM t",
     True, "CTE adı ve CTE kolonu geçerli sayılmalı"),
    # --- Reddedilmesi gerekenler ---
    ("SELECT fiyat FROM satislar", False, "uydurma kolon: fiyat (gerçeği birim_fiyat)"),
    ("SELECT ad FROM urun", False, "uydurma tablo: urun (gerçeği urunler)"),
    ("SELECT u.marka FROM urunler u", False, "uydurma kolon: marka"),
    ("SELECT * FROM siparisler", False, "uydurma tablo: siparisler"),
    ("SELECT stok_adedi FROM urunler", False, "uydurma kolon: stok_adedi"),
]


def main() -> None:
    basari = 0
    for sql, beklenen, aciklama in DURUMLAR:
        gecti, hata = statik_dogrula(sql, YAPI)
        dogru = gecti == beklenen
        basari += dogru
        isaret = "✓" if dogru else "✗ BAŞARISIZ"
        durum = "geçti" if gecti else f"reddedildi ({hata})"
        print(f"  {isaret}  [{durum}]  {aciklama}")

    print(f"\n=== {basari}/{len(DURUMLAR)} test geçti ===")


if __name__ == "__main__":
    main()
