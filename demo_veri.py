"""
Faz 0 — Sentetik Demo Veri Seti (perakende)
=============================================

Vitrin/demo için GERÇEK şirket verisi yerine kullanılan, tutarlı ve gerçekçi
bir sentetik perakende şeması üretir:

  kategoriler → urunler → satislar ← magazalar

Veri deseni bilinçli olarak "ilginç" sorulara izin verecek şekilde üretilir:
  - Mağaza hacim farkı (İstanbul en yüksek)
  - Şehir-ürün ilişkisi (sahil şehirlerinde içecek satışı yüksek)
  - Hafta sonu yoğunluğu
  - BUGÜN dahil son 90 gün (→ "bugün en çok satan ürün?" çalışır)

Çalıştırma:
  createdb sirket_demo        # yoksa
  export DATABASE_URL="postgresql://kullanici:parola@localhost:5432/sirket_demo"
  python demo_veri.py

DİKKAT: Yalnızca şu 4 tabloyu DROP/CREATE eder: satislar, urunler,
kategoriler, magazalar. DATABASE_URL'i mutlaka bir DEMO veritabanına ayarla.
"""
import asyncio
import os
import random
from datetime import date, timedelta

import asyncpg

random.seed(42)  # tekrar üretilebilirlik

GUN_SAYISI = 90          # son kaç gün
TOPLAM_SATIS = 6000      # yaklaşık satış kaydı

# --- Sabit referans veriler ---
KATEGORILER = ["İçecek", "Atıştırmalık", "Süt Ürünleri", "Kahvaltılık", "Temizlik"]

MAGAZALAR = [
    # (ad, sehir, hacim_agirligi, sahil_mi)
    ("Kadıköy Şube", "İstanbul", 0.32, True),
    ("Çankaya Şube", "Ankara", 0.24, False),
    ("Konak Şube", "İzmir", 0.20, True),
    ("Nilüfer Şube", "Bursa", 0.14, False),
    ("Muratpaşa Şube", "Antalya", 0.10, True),
]

# (ad, kategori, birim_fiyat, marka)
URUNLER = [
    ("Ayran 1L", "İçecek", 28.0, "Sütaş"),
    ("Kola 1L", "İçecek", 42.0, "CocaCola"),
    ("Maden Suyu", "İçecek", 18.0, "Beypazarı"),
    ("Portakal Suyu 1L", "İçecek", 55.0, "Dimes"),
    ("Soğuk Çay 1L", "İçecek", 38.0, "Lipton"),
    ("Su 5L", "İçecek", 32.0, "Erikli"),
    ("Cips 150g", "Atıştırmalık", 45.0, "Lays"),
    ("Çikolata 80g", "Atıştırmalık", 35.0, "Ülker"),
    ("Bisküvi", "Atıştırmalık", 22.0, "Eti"),
    ("Kuruyemiş 200g", "Atıştırmalık", 95.0, "Tadım"),
    ("Kraker", "Atıştırmalık", 19.0, "Ülker"),
    ("Süt 1L", "Süt Ürünleri", 36.0, "Pınar"),
    ("Yoğurt 1kg", "Süt Ürünleri", 68.0, "Sütaş"),
    ("Peynir 500g", "Süt Ürünleri", 145.0, "Pınar"),
    ("Tereyağı 250g", "Süt Ürünleri", 110.0, "Sütaş"),
    ("Kaşar 400g", "Süt Ürünleri", 165.0, "Pınar"),
    ("Yumurta 30'lu", "Kahvaltılık", 130.0, "Çiftlik"),
    ("Bal 460g", "Kahvaltılık", 240.0, "Balparmak"),
    ("Reçel 380g", "Kahvaltılık", 58.0, "Tamek"),
    ("Zeytin 400g", "Kahvaltılık", 120.0, "Marmarabirlik"),
    ("Çay 1kg", "Kahvaltılık", 185.0, "Çaykur"),
    ("Bulaşık Deterjanı", "Temizlik", 75.0, "Fairy"),
    ("Çamaşır Suyu 1L", "Temizlik", 48.0, "Domestos"),
    ("Kağıt Havlu", "Temizlik", 89.0, "Selpak"),
    ("Sabun", "Temizlik", 26.0, "Duru"),
    ("Yüzey Temizleyici", "Temizlik", 62.0, "Cif"),
]

DDL = """
-- Türkçe-güvenli metin eşleştirme için (lower(unaccent(...)) — bkz. analiz_kontrol)
CREATE EXTENSION IF NOT EXISTS unaccent;

DROP TABLE IF EXISTS satislar CASCADE;
DROP TABLE IF EXISTS urunler CASCADE;
DROP TABLE IF EXISTS kategoriler CASCADE;
DROP TABLE IF EXISTS magazalar CASCADE;

CREATE TABLE kategoriler (
    id   SERIAL PRIMARY KEY,
    ad   TEXT NOT NULL
);
COMMENT ON TABLE kategoriler IS 'Ürün kategorileri';
COMMENT ON COLUMN kategoriler.ad IS 'Kategori adı (İçecek, Süt Ürünleri vb.)';

CREATE TABLE magazalar (
    id            SERIAL PRIMARY KEY,
    ad            TEXT NOT NULL,
    sehir         TEXT NOT NULL
);
COMMENT ON TABLE magazalar IS 'Mağaza/şube bilgileri';
COMMENT ON COLUMN magazalar.ad IS 'Şube adı';
COMMENT ON COLUMN magazalar.sehir IS 'Şubenin bulunduğu şehir';

CREATE TABLE urunler (
    id           SERIAL PRIMARY KEY,
    ad           TEXT NOT NULL,
    kategori_id  INTEGER NOT NULL REFERENCES kategoriler(id),
    birim_fiyat  NUMERIC(10,2) NOT NULL,
    marka        TEXT
);
COMMENT ON TABLE urunler IS 'Satılan ürünler';
COMMENT ON COLUMN urunler.ad IS 'Ürün adı';
COMMENT ON COLUMN urunler.kategori_id IS 'kategoriler tablosuna referans';
COMMENT ON COLUMN urunler.birim_fiyat IS 'Güncel birim satış fiyatı (TL)';
COMMENT ON COLUMN urunler.marka IS 'Ürün markası';

CREATE TABLE satislar (
    id           SERIAL PRIMARY KEY,
    tarih        DATE NOT NULL,
    urun_id      INTEGER NOT NULL REFERENCES urunler(id),
    magaza_id    INTEGER NOT NULL REFERENCES magazalar(id),
    adet         INTEGER NOT NULL,
    birim_fiyat  NUMERIC(10,2) NOT NULL,
    toplam_tutar NUMERIC(12,2) NOT NULL
);
COMMENT ON TABLE satislar IS 'Satış kayıtları (her satır bir satış kalemi)';
COMMENT ON COLUMN satislar.tarih IS 'Satışın yapıldığı tarih';
COMMENT ON COLUMN satislar.urun_id IS 'urunler tablosuna referans';
COMMENT ON COLUMN satislar.magaza_id IS 'magazalar tablosuna referans';
COMMENT ON COLUMN satislar.adet IS 'Satılan adet';
COMMENT ON COLUMN satislar.birim_fiyat IS 'Satış anındaki birim fiyat (TL)';
COMMENT ON COLUMN satislar.toplam_tutar IS 'adet * birim_fiyat (TL)';

CREATE INDEX ix_satislar_tarih ON satislar(tarih);
CREATE INDEX ix_satislar_urun ON satislar(urun_id);
CREATE INDEX ix_satislar_magaza ON satislar(magaza_id);
"""


def _satis_uret(urun_idx: dict, magaza_idx: dict) -> list[tuple]:
    """Tutarlı, desenli satış kayıtları üretir."""
    bugun = date.today()
    magaza_agirlik = [m[2] for m in MAGAZALAR]
    satislar = []

    for _ in range(TOPLAM_SATIS):
        # Tarih: son GUN_SAYISI gün; daha yeni tarihlere hafif eğilim
        gun_once = int(abs(random.gauss(0, GUN_SAYISI / 2.5))) % GUN_SAYISI
        t = bugun - timedelta(days=gun_once)
        # Hafta sonu yoğunluğu: cumartesi/pazar ek kayıt şansı
        if t.weekday() >= 5 and random.random() < 0.3:
            satislar.append(None)  # işaretle, aşağıda çoğaltılacak

        # Mağaza seçimi (hacim ağırlıklı)
        mi = random.choices(range(len(MAGAZALAR)), weights=magaza_agirlik)[0]
        magaza_ad, sehir, _, sahil = MAGAZALAR[mi]

        # Ürün seçimi: sahil şehirlerinde içecek ağırlığı artar
        agirliklar = []
        for ad, kat, fiyat, marka in URUNLER:
            w = 1.0
            if kat == "İçecek":
                w = 2.2 if sahil else 1.0
            if kat == "Süt Ürünleri":
                w = 1.4
            agirliklar.append(w)
        ui = random.choices(range(len(URUNLER)), weights=agirliklar)[0]
        urun_ad, kat, fiyat, marka = URUNLER[ui]

        adet = random.randint(1, 6)
        toplam = round(adet * fiyat, 2)
        satislar.append((t, urun_idx[urun_ad], magaza_idx[magaza_ad], adet, fiyat, toplam))

    # None işaretlerini (hafta sonu ekstra) gerçek kayda çevir (rastgele kopya)
    temiz = [s for s in satislar if s is not None]
    ekstra = [random.choice(temiz) for s in satislar if s is None]
    return temiz + ekstra


async def main() -> None:
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("HATA: DATABASE_URL tanımlı değil. Örnek:")
        print('  export DATABASE_URL="postgresql://kullanici:parola@localhost:5432/sirket_demo"')
        return

    conn = await asyncpg.connect(dsn)
    try:
        veritabani = await conn.fetchval("SELECT current_database()")
        print(f"Bağlanılan veritabanı: {veritabani}")
        print("Şema oluşturuluyor (satislar/urunler/kategoriler/magazalar DROP+CREATE)...")
        await conn.execute(DDL)

        # Kategoriler
        kat_idx = {}
        for ad in KATEGORILER:
            kid = await conn.fetchval("INSERT INTO kategoriler(ad) VALUES($1) RETURNING id", ad)
            kat_idx[ad] = kid

        # Mağazalar
        magaza_idx = {}
        for ad, sehir, _, _ in MAGAZALAR:
            mid = await conn.fetchval(
                "INSERT INTO magazalar(ad, sehir) VALUES($1,$2) RETURNING id", ad, sehir
            )
            magaza_idx[ad] = mid

        # Ürünler
        urun_idx = {}
        for ad, kat, fiyat, marka in URUNLER:
            uid = await conn.fetchval(
                "INSERT INTO urunler(ad, kategori_id, birim_fiyat, marka) "
                "VALUES($1,$2,$3,$4) RETURNING id",
                ad, kat_idx[kat], fiyat, marka,
            )
            urun_idx[ad] = uid

        # Satışlar (toplu)
        satislar = _satis_uret(urun_idx, magaza_idx)
        await conn.executemany(
            "INSERT INTO satislar(tarih, urun_id, magaza_id, adet, birim_fiyat, toplam_tutar) "
            "VALUES($1,$2,$3,$4,$5,$6)",
            satislar,
        )

        # Özet
        n_satis = await conn.fetchval("SELECT COUNT(*) FROM satislar")
        n_bugun = await conn.fetchval("SELECT COUNT(*) FROM satislar WHERE tarih = CURRENT_DATE")
        ciro = await conn.fetchval("SELECT SUM(toplam_tutar) FROM satislar")
        print("\n=== Demo verisi hazır ===")
        print(f"  Kategori: {len(KATEGORILER)} | Mağaza: {len(MAGAZALAR)} | Ürün: {len(URUNLER)}")
        print(f"  Satış kaydı: {n_satis} (bugün: {n_bugun})")
        print(f"  Toplam ciro: {ciro:,.2f} TL")
        print("\nÖrnek sorular için hazır: 'bugün en çok satan ürün?', "
              "'hangi mağazada hangi ürün en çok satıyor?', 'bu ay şehir bazında ciro?'")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
