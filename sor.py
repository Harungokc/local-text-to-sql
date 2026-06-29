"""
Sohbet Betiği — Terminalden soru sor
=====================================

Kullanım:
  .venv/bin/python sor.py "bugün en çok satan ürün ne?"   # tek soru
  .venv/bin/python sor.py                                  # etkileşimli (çık: q)

Demo ortam değişkenleri yoksa otomatik ayarlanır (sirket_demo + qwen2.5-coder:3b).
"""
import asyncio
import os
import sys
import time

# Demo varsayılanları (zaten export edilmişse dokunmaz)
os.environ.setdefault("SORGU_DATABASE_URL", "postgresql://harungokce@localhost:5432/sirket_demo")
os.environ.setdefault("YEREL_MODEL", "qwen2.5-coder:3b")
os.environ.setdefault("VLLM_BASE_URL", "http://127.0.0.1:11434/v1")

import runner  # noqa: E402  (env'den sonra import)
import db_sorgu  # noqa: E402


def _tablo(satirlar: list[dict], maks: int = 10) -> str:
    """Sonuç satırlarını basit bir hizalı tablo olarak biçimlendirir."""
    if not satirlar:
        return "   (sonuç yok)"
    kolonlar = list(satirlar[0].keys())
    gosterilen = satirlar[:maks]
    # Kolon genişlikleri
    gen = {k: max(len(str(k)), *(len(str(s.get(k, ""))) for s in gosterilen)) for k in kolonlar}
    baslik = "   " + " | ".join(str(k).ljust(gen[k]) for k in kolonlar)
    ayrac = "   " + "-+-".join("-" * gen[k] for k in kolonlar)
    govde = [
        "   " + " | ".join(str(s.get(k, "")).ljust(gen[k]) for k in kolonlar)
        for s in gosterilen
    ]
    fazla = f"\n   … (+{len(satirlar) - maks} satır daha)" if len(satirlar) > maks else ""
    return "\n".join([baslik, ayrac, *govde]) + fazla


def _yazdir(r: dict, sure: float) -> None:
    print("\n" + "═" * 64)
    if r.get("sql"):
        print(f"📊 ÜRETİLEN SQL:\n   {r['sql']}")
        print(f"\n🔢 SONUÇ ({r['satir_sayisi']} satır):")
        print(_tablo(r.get("satirlar", [])))
    else:
        print("🚫 Sorgu çalıştırılmadı (kapsam-dışı/guard tarafından engellendi).")
    if r.get("icgoruler"):
        print("\n💡 BULGULAR:")
        for i in r["icgoruler"]:
            print(f"   • {i}")
    print(f"\n📝 ÖZET:\n   {r['ozet_tr']}")
    if r.get("cekinceler"):
        print("\n⚠️  ÇEKİNCELER:")
        for c in r["cekinceler"]:
            print(f"   • {c}")
    sadik = "✓ sadık" if r.get("sadik", True) else "✗ anlatım reddedildi (deterministik özete düşüldü)"
    print(f"\n🔎 KONTROL İZİ ({sadik}):")
    for adim in r.get("iz", []):
        print(f"   › {adim}")
    print(f"\n(⏱  {sure:.1f}s)")
    print("═" * 64)


async def tek_soru(soru: str) -> None:
    t = time.time()
    try:
        r = await runner.sor(soru)
        _yazdir(r, time.time() - t)
    except Exception as e:  # noqa: BLE001
        print(f"❌ Yanıtlanamadı: {e}")
    finally:
        await db_sorgu.kapat()


async def etkilesimli() -> None:
    print("═" * 64)
    print(f"🏪 Şirket Sorgu — yerel text-to-SQL  (model: {os.environ['YEREL_MODEL']})")
    print("═" * 64)
    print("Türkçe soru yaz, Enter'a bas. Çıkış: 'q' + Enter.")
    print("\nÖrnek sorular:")
    for ornek in (
        "en çok ciro yapan 5 ürün hangisi?",
        "Antalya şubesinde en çok satılan içecek nedir?",
        "kategori bazında satış adedi dağılımı nedir?",
        "Pınar markasının toplam cirosu ne kadar?",
        "en kârlı ürün hangisi?   (← guard'ı dener)",
    ):
        print(f"   - {ornek}")
    try:
        while True:
            try:
                soru = input("\n❓ ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if soru.lower() in {"q", "quit", "exit", "çık"}:
                break
            if not soru:
                continue
            t = time.time()
            try:
                r = await runner.sor(soru)
                _yazdir(r, time.time() - t)
            except Exception as e:  # noqa: BLE001
                print(f"❌ Yanıtlanamadı: {e}")
    finally:
        await db_sorgu.kapat()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        asyncio.run(tek_soru(" ".join(sys.argv[1:])))
    else:
        asyncio.run(etkilesimli())
