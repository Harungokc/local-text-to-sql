"""
Türetilmiş Metrik Doğruluk Testi (Kontrol 3'ün kanıtı)
=======================================================

gold_set.py SQL'in doğruluğunu ölçer. Bu test ise SQL SONRASI TÜRETİLEN
metriğin (pay/oran) doğruluğunu ölçer — Kontrol 3'ün asıl faydası.

Yöntem: Her soru için (a) tam pipeline'ın deterministik rapor katmanını çalıştır
(LLM gerekmez, metrik koddan gelir), ürettiği 'pay' değerini al; (b) aynı payı
DB'den BAĞIMSIZ bir referans sorguyla hesapla; (c) karşılaştır. Ayrıca Kontrol 3
OLMASAYDI üretilecek naif (yanlış) payı da gösterir.

Çalıştırma:
  export SORGU_DATABASE_URL="postgresql://harungokce@localhost:5432/sirket_demo"
  .venv/bin/python metrik_test.py
"""
import asyncio

import db_sorgu
import rapor
import sql_guvenlik
import sql_kontrol
from runner import _gercek_toplam_getir
import sema

# Her durum: ad, çalıştırılacak SQL, gerçek pay'ı veren referans SQL, beklenen payda_kaynagi
DURUMLAR = [
    {
        "ad": "Top-5 ürün cirosu → en yüksek ürünün payı (KESİK)",
        "sql": "SELECT u.ad AS urun, SUM(s.toplam_tutar) AS ciro FROM satislar s "
               "JOIN urunler u ON u.id=s.urun_id GROUP BY u.ad ORDER BY ciro DESC LIMIT 5",
        "beklenen_sql": "SELECT ROUND(MAX(c)/SUM(c)*100, 1) FROM "
                        "(SELECT SUM(toplam_tutar) c FROM satislar GROUP BY urun_id) q",
        "beklenen_kaynak": "grand_total",
    },
    {
        "ad": "Şehir cirosu → en yüksek şehrin payı (TAM EVREN, LIMIT yok)",
        "sql": "SELECT m.sehir, SUM(s.toplam_tutar) AS toplam_ciro FROM satislar s "
               "JOIN magazalar m ON m.id=s.magaza_id GROUP BY m.sehir ORDER BY toplam_ciro DESC",
        "beklenen_sql": "SELECT ROUND(MAX(c)/SUM(c)*100, 1) FROM "
                        "(SELECT SUM(s.toplam_tutar) c FROM satislar s "
                        "JOIN magazalar m ON m.id=s.magaza_id GROUP BY m.sehir) q",
        "beklenen_kaynak": "tam",
    },
    {
        "ad": "Top-3 ürün adedi → en yüksek ürünün payı (KESİK)",
        "sql": "SELECT u.ad AS urun, SUM(s.adet) AS toplam_adet FROM satislar s "
               "JOIN urunler u ON u.id=s.urun_id GROUP BY u.ad ORDER BY toplam_adet DESC LIMIT 3",
        "beklenen_sql": "SELECT ROUND(MAX(c)*100.0/SUM(c), 1) FROM "
                        "(SELECT SUM(adet) c FROM satislar GROUP BY urun_id) q",
        "beklenen_kaynak": "grand_total",
    },
]


def _pay_bulgusu(ozet: dict) -> dict | None:
    for b in ozet["bulgular"]:
        if b["tip"] == "pay":
            return b
    return None


async def main() -> None:
    yapi = await sema.sema_yapisi()
    basari = 0
    for d in DURUMLAR:
        guvenli = sql_guvenlik.dogrula_ve_hazirla(d["sql"])
        satirlar = await db_sorgu.calistir_select(guvenli)
        profil = sql_kontrol.sorgu_profili(guvenli)
        gercek_toplam = await _gercek_toplam_getir(guvenli, satirlar, profil, yapi)

        ozet = rapor.ozetle(satirlar, profil=profil, gercek_toplam=gercek_toplam)
        pay = _pay_bulgusu(ozet)

        # Beklenen (DB'den bağımsız)
        beklenen = float((await db_sorgu.calistir_select(d["beklenen_sql"]))[0]["round"])

        # Naif (Kontrol 3 olmasaydı): top / dönen satırların toplamı
        deg = rapor.olcu_kolonu(satirlar)
        donen = [r[deg] for r in satirlar]
        naif = round(max(donen) / sum(donen) * 100, 1)

        uretilen = pay["deger"] if pay else None
        kaynak = pay.get("payda_kaynagi") if pay else None
        dogru = uretilen is not None and abs(uretilen - beklenen) < 0.15 and kaynak == d["beklenen_kaynak"]
        basari += dogru

        isaret = "✓" if dogru else "✗ BAŞARISIZ"
        print(f"  {isaret}  {d['ad']}")
        print(f"       beklenen=%{beklenen} | üretilen=%{uretilen} (kaynak={kaynak})")
        if abs(naif - beklenen) >= 0.15:
            print(f"       (Kontrol 3 olmasaydı naif/yanlış: %{naif})")

    print(f"\n=== Metrik doğruluk: {basari}/{len(DURUMLAR)} ===")
    await db_sorgu.kapat()


if __name__ == "__main__":
    asyncio.run(main())
