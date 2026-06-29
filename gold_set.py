"""
Gold Set — Doğruluk Ölçümü (Execution-Match)
=============================================

Üretilen SQL'in doğruluğunu STRING karşılaştırmasıyla değil, ÇALIŞTIRMA-EŞLEŞMESİ
ile ölçer: hem gold SQL hem üretilen SQL salt-okunur çalıştırılır, sonuç kümeleri
sıra-bağımsız karşılaştırılır. Text-to-SQL'de standart ve doğru metrik budur.

Çalıştırma:
  export SORGU_DATABASE_URL="postgresql://readonly_user:...@localhost:5432/sirket"
  python gold_set.py

gold/sorular.json biçimi:
  [
    {"soru": "bugün en çok satan ürün?", "gold_sql": "SELECT ...", "tip": "agregasyon"},
    ...
  ]
"""
import asyncio
import json
import logging
import os

import db_sorgu
import runner
import sql_guvenlik
from llm import LLM

logging.basicConfig(level=logging.WARNING)

GOLD_YOLU = os.environ.get("GOLD_YOLU", "gold/sorular.json")


from collections import Counter


def _kume(satirlar: list[dict]) -> Counter:
    """Sonuç satırlarını karşılaştırma için çoklu-kümeye (Counter) çevirir.

    Execution-match standardı (Spider): kolon ADLARI yok sayılır, yalnızca
    DEĞERLER kolon sırasına göre karşılaştırılır. Böylece aynı sonucu veren
    farklı takma adlı SQL'ler ('ciro' vs 'toplam_ciro') eşit sayılır.
    Satır sırası önemsiz (Counter), tekrar eden satırlar korunur.
    """
    return Counter(tuple(str(v) for v in s.values()) for s in satirlar)


async def _calistir(sql: str) -> list[dict]:
    guvenli = sql_guvenlik.dogrula_ve_hazirla(sql)
    return await db_sorgu.calistir_select(guvenli)


async def main() -> None:
    if not os.path.exists(GOLD_YOLU):
        print(f"HATA: {GOLD_YOLU} bulunamadı. Önce gold soru seti oluştur.")
        return

    with open(GOLD_YOLU, encoding="utf-8") as f:
        gold = json.load(f)

    model = LLM()
    gecen = 0
    tip_istat: dict[str, list[int]] = {}

    for i, ornek in enumerate(gold, 1):
        soru = ornek["soru"]
        tip = ornek.get("tip", "genel")
        tip_istat.setdefault(tip, [0, 0])
        tip_istat[tip][1] += 1
        try:
            uretilen = await runner.sor(soru, model=model)
            uretilen_kume = _kume(uretilen["satirlar"])
            gold_kume = _kume(await _calistir(ornek["gold_sql"]))
            dogru = uretilen_kume == gold_kume
        except Exception as e:  # noqa: BLE001
            dogru = False
            print(f"  [{i}] HATA: {e}")

        if dogru:
            gecen += 1
            tip_istat[tip][0] += 1
        isaret = "✓" if dogru else "✗"
        print(f"  [{i}] {isaret} ({tip}) {soru}")

    toplam = len(gold)
    print(f"\n=== Doğruluk: {gecen}/{toplam} = %{100*gecen/toplam:.1f} ===")
    print("Tip bazında:")
    for tip, (d, t) in sorted(tip_istat.items()):
        print(f"  {tip}: {d}/{t} (%{100*d/t:.0f})")


if __name__ == "__main__":
    asyncio.run(main())
