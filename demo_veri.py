"""
Faz 0 — Sentetik Demo Veri Seti (perakende, BÜYÜK ÖLÇEK)
========================================================

Vitrin/demo için GERÇEK şirket verisi yerine kullanılan, tutarlı ve gerçekçi
bir sentetik perakende şeması üretir:

  kategoriler → urunler → satislar ← magazalar

Ölçek (ciddi/gerçekçi bir zincir görünümü):
  - 10 kategori · 20 mağaza (13 şehir) · ~108 ürün · ~50 marka
  - 2 yıllık (730 gün) satış geçmişi, ~280.000 satış kaydı

Veri deseni bilinçli olarak "ilginç" sorulara izin verecek şekilde üretilir:
  - Mağaza/şehir hacim farkı (İstanbul şubeleri en yüksek)
  - Şehir-ürün ilişkisi (sahil şehirlerinde içecek satışı yüksek)
  - Mevsimsellik (yaz aylarında içecek patlaması)
  - Hafta sonu yoğunluğu + son güne doğru hafif artış (→ "bugün en çok satan?" çalışır)

Çalıştırma:
  createdb sirket_demo        # yoksa
  export DATABASE_URL="postgresql://kullanici:parola@localhost:5432/sirket_demo"
  python demo_veri.py

DİKKAT: Yalnızca şu 4 tabloyu DROP/CREATE eder: satislar, urunler,
kategoriler, magazalar. DATABASE_URL'i mutlaka bir DEMO veritabanına ayarla.
"""
import asyncio
import math
import os
import random
from datetime import date, timedelta
from decimal import Decimal
from itertools import accumulate

import asyncpg

random.seed(42)  # tekrar üretilebilirlik

GUN_SAYISI = 730          # son kaç gün (2 yıl)
TOPLAM_SATIS = 280_000    # yaklaşık satış kaydı

# --- Sabit referans veriler ---
KATEGORILER = [
    "İçecek", "Atıştırmalık", "Süt Ürünleri", "Kahvaltılık", "Temizlik",
    "Et & Tavuk", "Meyve & Sebze", "Donuk Gıda", "Unlu Mamüller", "Kişisel Bakım",
]

# Kategori taban popülerliği (satış olasılığı ağırlığı)
KATEGORI_TABAN = {
    "İçecek": 1.4, "Atıştırmalık": 1.2, "Süt Ürünleri": 1.5, "Kahvaltılık": 1.2,
    "Temizlik": 1.0, "Et & Tavuk": 1.1, "Meyve & Sebze": 1.6, "Donuk Gıda": 0.8,
    "Unlu Mamüller": 1.5, "Kişisel Bakım": 0.9,
}

MAGAZALAR = [
    # (ad, sehir, hacim_agirligi, sahil_mi)
    ("Kadıköy Şube", "İstanbul", 0.090, True),
    ("Beşiktaş Şube", "İstanbul", 0.080, True),
    ("Bakırköy Şube", "İstanbul", 0.075, True),
    ("Ümraniye Şube", "İstanbul", 0.070, True),
    ("Çankaya Şube", "Ankara", 0.075, False),
    ("Keçiören Şube", "Ankara", 0.055, False),
    ("Konak Şube", "İzmir", 0.065, True),
    ("Bornova Şube", "İzmir", 0.050, True),
    ("Nilüfer Şube", "Bursa", 0.050, False),
    ("Osmangazi Şube", "Bursa", 0.040, False),
    ("Muratpaşa Şube", "Antalya", 0.050, True),
    ("Konyaaltı Şube", "Antalya", 0.040, True),
    ("Seyhan Şube", "Adana", 0.040, False),
    ("Selçuklu Şube", "Konya", 0.035, False),
    ("Şahinbey Şube", "Gaziantep", 0.035, False),
    ("Yenişehir Şube", "Mersin", 0.030, True),
    ("Tepebaşı Şube", "Eskişehir", 0.025, False),
    ("Atakum Şube", "Samsun", 0.025, True),
    ("Melikgazi Şube", "Kayseri", 0.020, False),
    ("Ortahisar Şube", "Trabzon", 0.020, True),
]

# (ad, kategori, birim_fiyat, marka)  — marka None = markasız (manav/kasap vb.)
URUNLER = [
    # İçecek
    ("Ayran 1L", "İçecek", 28.0, "Sütaş"), ("Kola 1L", "İçecek", 42.0, "CocaCola"),
    ("Kola 2.5L", "İçecek", 75.0, "CocaCola"), ("Maden Suyu", "İçecek", 18.0, "Beypazarı"),
    ("Portakal Suyu 1L", "İçecek", 55.0, "Dimes"), ("Soğuk Çay 1L", "İçecek", 38.0, "Lipton"),
    ("Su 5L", "İçecek", 32.0, "Erikli"), ("Su 0.5L", "İçecek", 8.0, "Erikli"),
    ("Gazoz 1L", "İçecek", 30.0, "Uludağ"), ("Enerji İçeceği", "İçecek", 55.0, "RedBull"),
    ("Limonata 1L", "İçecek", 40.0, "Dimes"),
    # Atıştırmalık
    ("Cips 150g", "Atıştırmalık", 45.0, "Lays"), ("Çikolata 80g", "Atıştırmalık", 35.0, "Ülker"),
    ("Bisküvi", "Atıştırmalık", 22.0, "Eti"), ("Kuruyemiş 200g", "Atıştırmalık", 95.0, "Tadım"),
    ("Kraker", "Atıştırmalık", 19.0, "Ülker"), ("Gofret", "Atıştırmalık", 12.0, "Ülker"),
    ("Çikolatalı Bar", "Atıştırmalık", 15.0, "Eti"), ("Mısır Cipsi 100g", "Atıştırmalık", 40.0, "Doritos"),
    ("Sakız", "Atıştırmalık", 8.0, "Falım"), ("Lokum 250g", "Atıştırmalık", 120.0, "Hacı Bekir"),
    # Süt Ürünleri
    ("Süt 1L", "Süt Ürünleri", 36.0, "Pınar"), ("Yoğurt 1kg", "Süt Ürünleri", 68.0, "Sütaş"),
    ("Peynir 500g", "Süt Ürünleri", 145.0, "Pınar"), ("Tereyağı 250g", "Süt Ürünleri", 110.0, "Sütaş"),
    ("Kaşar 400g", "Süt Ürünleri", 165.0, "Pınar"), ("Beyaz Peynir 1kg", "Süt Ürünleri", 220.0, "İçim"),
    ("Labne 200g", "Süt Ürünleri", 65.0, "President"), ("Krema 200ml", "Süt Ürünleri", 45.0, "İçim"),
    ("Laktozsuz Süt 1L", "Süt Ürünleri", 48.0, "Pınar"), ("Kefir 1L", "Süt Ürünleri", 55.0, "Altınkılıç"),
    # Kahvaltılık
    ("Yumurta 30'lu", "Kahvaltılık", 130.0, "Çiftlik"), ("Bal 460g", "Kahvaltılık", 240.0, "Balparmak"),
    ("Reçel 380g", "Kahvaltılık", 58.0, "Tamek"), ("Zeytin 400g", "Kahvaltılık", 120.0, "Marmarabirlik"),
    ("Çay 1kg", "Kahvaltılık", 185.0, "Çaykur"), ("Tahin 300g", "Kahvaltılık", 90.0, "Koska"),
    ("Pekmez 600g", "Kahvaltılık", 110.0, "Koska"), ("Fındık Ezmesi 350g", "Kahvaltılık", 180.0, "Nutella"),
    ("Kahvaltılık Gevrek 500g", "Kahvaltılık", 85.0, "Nestle"), ("Sucuk 250g", "Kahvaltılık", 140.0, "Pınar"),
    ("Kahve 200g", "Kahvaltılık", 160.0, "Nescafe"),
    # Temizlik
    ("Bulaşık Deterjanı", "Temizlik", 75.0, "Fairy"), ("Çamaşır Suyu 1L", "Temizlik", 48.0, "Domestos"),
    ("Kağıt Havlu", "Temizlik", 89.0, "Selpak"), ("Sabun", "Temizlik", 26.0, "Duru"),
    ("Yüzey Temizleyici", "Temizlik", 62.0, "Cif"), ("Çamaşır Deterjanı 3L", "Temizlik", 180.0, "Omo"),
    ("Yumuşatıcı 1.4L", "Temizlik", 95.0, "Yumoş"), ("Tuvalet Kağıdı 32'li", "Temizlik", 130.0, "Solo"),
    ("Cam Temizleyici", "Temizlik", 45.0, "Cif"), ("Çöp Poşeti", "Temizlik", 35.0, "Roll-Up"),
    ("Bulaşık Süngeri", "Temizlik", 20.0, "Scotch"),
    # Et & Tavuk
    ("Tavuk Göğüs 1kg", "Et & Tavuk", 120.0, "Banvit"), ("Kıyma 1kg", "Et & Tavuk", 280.0, None),
    ("Tavuk But 1kg", "Et & Tavuk", 95.0, "Şenpiliç"), ("Sosis 500g", "Et & Tavuk", 85.0, "Pınar"),
    ("Salam 200g", "Et & Tavuk", 60.0, "Apikoğlu"), ("Dana Kuşbaşı 1kg", "Et & Tavuk", 360.0, None),
    ("Hindi Füme 150g", "Et & Tavuk", 70.0, "Banvit"), ("Köfte 500g", "Et & Tavuk", 150.0, None),
    ("Tavuk Kanat 1kg", "Et & Tavuk", 80.0, "Şenpiliç"), ("Pastırma 100g", "Et & Tavuk", 130.0, "Apikoğlu"),
    # Meyve & Sebze
    ("Domates 1kg", "Meyve & Sebze", 25.0, None), ("Salatalık 1kg", "Meyve & Sebze", 22.0, None),
    ("Elma 1kg", "Meyve & Sebze", 30.0, None), ("Muz 1kg", "Meyve & Sebze", 45.0, None),
    ("Patates 1kg", "Meyve & Sebze", 18.0, None), ("Soğan 1kg", "Meyve & Sebze", 15.0, None),
    ("Portakal 1kg", "Meyve & Sebze", 28.0, None), ("Limon 1kg", "Meyve & Sebze", 35.0, None),
    ("Biber 1kg", "Meyve & Sebze", 40.0, None), ("Patlıcan 1kg", "Meyve & Sebze", 30.0, None),
    ("Çilek 500g", "Meyve & Sebze", 60.0, None),
    # Donuk Gıda
    ("Pizza", "Donuk Gıda", 65.0, "Superfresh"), ("Patates Kızartması 1kg", "Donuk Gıda", 70.0, "McCain"),
    ("Donuk Sebze 1kg", "Donuk Gıda", 55.0, "Superfresh"), ("Mantı 1kg", "Donuk Gıda", 90.0, None),
    ("Dondurma 1L", "Donuk Gıda", 85.0, "Algida"), ("Donuk Köfte 500g", "Donuk Gıda", 110.0, None),
    ("Börek 800g", "Donuk Gıda", 75.0, "Superfresh"), ("Donuk Balık 600g", "Donuk Gıda", 130.0, None),
    # Unlu Mamüller
    ("Ekmek", "Unlu Mamüller", 10.0, None), ("Tost Ekmeği", "Unlu Mamüller", 25.0, "Uno"),
    ("Lavaş 4'lü", "Unlu Mamüller", 20.0, None), ("Galeta Unu 500g", "Unlu Mamüller", 22.0, None),
    ("Un 1kg", "Unlu Mamüller", 30.0, "Söke"), ("Makarna 500g", "Unlu Mamüller", 28.0, "Barilla"),
    ("Bulgur 1kg", "Unlu Mamüller", 35.0, "Duru"), ("Pirinç 1kg", "Unlu Mamüller", 65.0, "Duru"),
    ("Kek", "Unlu Mamüller", 30.0, "Eti"), ("Kruvasan 4'lü", "Unlu Mamüller", 40.0, None),
    # Kişisel Bakım
    ("Şampuan 500ml", "Kişisel Bakım", 75.0, "Elidor"), ("Diş Macunu", "Kişisel Bakım", 45.0, "Colgate"),
    ("Duş Jeli 500ml", "Kişisel Bakım", 55.0, "Duru"), ("Deodorant", "Kişisel Bakım", 60.0, "Rexona"),
    ("Tıraş Köpüğü", "Kişisel Bakım", 80.0, "Gillette"), ("Islak Mendil", "Kişisel Bakım", 35.0, "Sleepy"),
    ("Hijyenik Ped", "Kişisel Bakım", 70.0, "Orkid"), ("Bebek Bezi", "Kişisel Bakım", 280.0, "Prima"),
    ("El Kremi", "Kişisel Bakım", 50.0, "Nivea"), ("Saç Kremi 400ml", "Kişisel Bakım", 70.0, "Elidor"),
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


def _urun_cum_agirliklari(sahil: bool, yaz: bool) -> list[float]:
    """Ürün seçimi için kümülatif ağırlıklar (sahil/mevsim duyarlı).
    İçecek: sahilde ve yazın belirgin artar. cum_weights → hızlı bisect seçimi."""
    ws = []
    for _ad, kat, _fiyat, _marka in URUNLER:
        w = KATEGORI_TABAN[kat]
        if kat == "İçecek":
            if sahil:
                w *= 2.2
            if yaz:
                w *= 2.5
        if kat == "Donuk Gıda" and yaz:
            w *= 1.6  # yazın dondurma vb.
        ws.append(w)
    return list(accumulate(ws))


def _satis_uret(urun_idx: dict, magaza_idx: dict) -> list[tuple]:
    """Tutarlı, desenli ~TOPLAM_SATIS satış kaydı üretir (hızlı: toplu seçim)."""
    bugun = date.today()
    gunler = [bugun - timedelta(days=i) for i in range(GUN_SAYISI)]
    # Gün ağırlığı: hafif recency (son güne doğru artış) + hafta sonu yoğunluğu
    gun_agirlik = [
        math.exp(-i / (GUN_SAYISI / 2.0)) * (1.6 if g.weekday() >= 5 else 1.0)
        for i, g in enumerate(gunler)
    ]
    # Tüm tarih ve mağaza seçimlerini tek seferde çek (hızlı)
    secili_gunler = random.choices(gunler, weights=gun_agirlik, k=TOPLAM_SATIS)
    magaza_agirlik = [m[2] for m in MAGAZALAR]
    secili_magaza = random.choices(range(len(MAGAZALAR)), weights=magaza_agirlik, k=TOPLAM_SATIS)

    # Ürün cum-ağırlıklarını 4 kombinasyon için önceden hesapla
    cum = {(s, y): _urun_cum_agirliklari(s, y) for s in (True, False) for y in (True, False)}
    n = len(URUNLER)
    # Ürün başına Decimal fiyat (NUMERIC için)
    fiyat_d = [Decimal(str(u[2])) for u in URUNLER]

    records = []
    for t, mi in zip(secili_gunler, secili_magaza):
        ad_m, _sehir, _w, sahil = MAGAZALAR[mi]
        yaz = t.month in (6, 7, 8)
        ui = random.choices(range(n), cum_weights=cum[(sahil, yaz)])[0]
        urun_ad, _kat, _fiyat, _marka = URUNLER[ui]
        adet = random.randint(1, 6)
        bf = fiyat_d[ui]
        records.append((t, urun_idx[urun_ad], magaza_idx[ad_m], adet, bf, bf * adet))
    return records


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
        for ad, sehir, _w, _s in MAGAZALAR:
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

        # Satışlar (toplu COPY — büyük hacim için hızlı)
        print(f"{TOPLAM_SATIS:,} satış kaydı üretiliyor...")
        satislar = _satis_uret(urun_idx, magaza_idx)
        print("Veritabanına yazılıyor (COPY)...")
        await conn.copy_records_to_table(
            "satislar", records=satislar,
            columns=["tarih", "urun_id", "magaza_id", "adet", "birim_fiyat", "toplam_tutar"],
        )

        # Özet
        n_satis = await conn.fetchval("SELECT COUNT(*) FROM satislar")
        n_bugun = await conn.fetchval("SELECT COUNT(*) FROM satislar WHERE tarih = CURRENT_DATE")
        ciro = await conn.fetchval("SELECT SUM(toplam_tutar) FROM satislar")
        ilk, son = await conn.fetchrow("SELECT MIN(tarih), MAX(tarih) FROM satislar")
        print("\n=== Demo verisi hazır ===")
        print(f"  Kategori: {len(KATEGORILER)} | Mağaza: {len(MAGAZALAR)} | Ürün: {len(URUNLER)}")
        print(f"  Tarih aralığı: {ilk} → {son}")
        print(f"  Satış kaydı: {n_satis:,} (bugün: {n_bugun})")
        print(f"  Toplam ciro: {ciro:,.2f} TL")
        print("\nÖrnek sorular: 'bugün en çok satan ürün?', "
              "'şehir bazında ciro?', 'kategori bazında satış adedi?', "
              "'en çok ciro yapan 5 ürün?'")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
