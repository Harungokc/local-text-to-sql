"""
İlk Kurulum Scripti — Şema Keşfi + Few-shot Yükleme
====================================================

İki iş yapar:
  1) Veritabanı şemasını keşfedip ekrana yazar (bağlantı + introspection testi).
  2) gold/few_shot.json içindeki örnek "soru → SQL" çiftlerini ChromaDB
     few-shot deposuna yükler.

Çalıştırma:
  export SORGU_DATABASE_URL="postgresql://readonly_user:...@localhost:5432/sirket"
  python seed_sema.py

few_shot.json biçimi:
  [
    {"soru": "bugün en çok satan ürün?", "sql": "SELECT ...", "tablolar": ["satislar","urunler"]},
    ...
  ]
"""
import asyncio
import json
import os

import retrieval
import sema

FEW_SHOT_YOLU = os.environ.get("FEW_SHOT_YOLU", "gold/few_shot.json")


async def main() -> None:
    # 1) Şema keşfi
    print("=== Veritabanı Şeması Keşfediliyor ===")
    ddl = await sema.sema_ddl_getir()
    if not ddl:
        print("UYARI: public şemasında tablo bulunamadı. Bağlantıyı kontrol et.")
    for tablo, metin in ddl.items():
        kolon_sayisi = metin.count("\n") - 1
        print(f"  • {tablo}  ({kolon_sayisi} kolon)")
    print(f"Toplam {len(ddl)} tablo keşfedildi.\n")

    # 2) Few-shot yükleme
    if os.path.exists(FEW_SHOT_YOLU):
        with open(FEW_SHOT_YOLU, encoding="utf-8") as f:
            ornekler = json.load(f)
        for o in ornekler:
            retrieval.ogret(o["soru"], o["sql"], o.get("tablolar"))
        print(f"=== {len(ornekler)} few-shot örneği yüklendi ===")
    else:
        print(f"UYARI: {FEW_SHOT_YOLU} bulunamadı. Few-shot örneği yüklenmedi.")
        print("       (Örnek şablon için gold/few_shot.ornek.json'a bak.)")

    print(f"Depodaki toplam örnek sayısı: {retrieval.ornek_sayisi()}")


if __name__ == "__main__":
    asyncio.run(main())
