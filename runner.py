"""
Orkestratör — Text-to-SQL Pipeline
====================================

Tüm akışı sıralar:
  1) Şema linkleme   (sema.ilgili_tablolar)
  2) Few-shot getir  (retrieval.benzer_ornekler)
  3) SQL üret        (llm + prompts/sql_uret)
  4) KONTROL 1       Güvenlik (sql_guvenlik.dogrula_ve_hazirla)
  5) KONTROL 2       Doğruluk: şema grounding + EXPLAIN (sql_kontrol.kontrol2)
  6) Çalıştır        (db_sorgu.calistir_select)
  7) Hata olursa     → self-correction (prompts/sql_duzelt), maks N tur
  8) KONTROL 3       Analiz doğrulama: kesik sonuçta pay için gerçek toplamı çek
  9) Raporla         (rapor.raporla: deterministik özet → içgörü → LLM anlatım)
 10) Sadakat         anlatımdaki sayılar olgularda mı? (numeric faithfulness)
 11) Başarılıysa     → retrieval'a yeni few-shot olarak kaydet (öğrenme)

Faz 1: tek-atış üretim + self-correction. Faz 3'te çoklu aday eklenecek.
"""
import logging
import os

import asyncpg

import analiz_kontrol
import db_sorgu
import on_kontrol
import rapor
import retrieval
import sema
import sql_guvenlik
import sql_kontrol
from araclar import prompt_yukle, sql_temizle
from llm import LLM

log = logging.getLogger("runner")

MAKS_DUZELTME = int(os.environ.get("MAKS_DUZELTME", "2"))


class CalismadiHatasi(Exception):
    """Hiçbir aday geçerli/çalışan SQL üretemediğinde fırlatılır."""


async def _uret_dogrula_calistir(
    soru: str, sema_metni: str, ornek_metni: str, yapi: dict[str, set[str]],
    model: LLM, iz: list[str],
) -> tuple[str, list[dict]]:
    """Bir SQL adayı üretir; KONTROL 1 (güvenlik) + KONTROL 2 (doğruluk) +
    çalıştırma sırasıyla denenir. Herhangi biri başarısızsa hata modele geri
    beslenir (self-correction), maks N tur. Her kontrolün kararı `iz`'e yazılır.

    Dönüş: (guvenli_sql, satirlar). Başaramazsa CalismadiHatasi.
    """
    istem = prompt_yukle("sql_uret", sema=sema_metni, ornekler=ornek_metni, soru=soru)
    aday = sql_temizle(model.cagir(sistem=istem, kullanici=soru, sicaklik=0.0))

    son_hata = "bilinmiyor"
    for tur in range(1, MAKS_DUZELTME + 2):  # 1 üretim + MAKS_DUZELTME düzeltme
        hata: str | None = None
        guvenli: str | None = None

        # Precision guard: substring `%X%` filtrelerini kelime-başına normalize et
        aday = analiz_kontrol.normalle_substring(aday)

        # KONTROL 1 — Güvenlik (sadece-SELECT)
        try:
            guvenli = sql_guvenlik.dogrula_ve_hazirla(aday)
            iz.append(f"K1 güvenlik[tur {tur}]: GEÇTİ")
        except sql_guvenlik.GuvenlikHatasi as e:
            hata = f"Güvenlik: {e}"
            iz.append(f"K1 güvenlik[tur {tur}]: REDDETTİ — {e}")

        # KONTROL 2 — Doğruluk (şema grounding + EXPLAIN dry-run)
        if guvenli is not None:
            k2_ok, k2_hata = await sql_kontrol.kontrol2(guvenli, yapi)
            if k2_ok:
                iz.append(f"K2 doğruluk[tur {tur}]: GEÇTİ (grounding+EXPLAIN)")
            else:
                hata = f"Doğruluk: {k2_hata}"
                iz.append(f"K2 doğruluk[tur {tur}]: REDDETTİ — {k2_hata}")

        # Çalıştır (iki kontrol de geçtiyse)
        if hata is None:
            try:
                satirlar = await db_sorgu.calistir_select(guvenli)
                iz.append(f"Çalıştırma[tur {tur}]: {len(satirlar)} satır")
                return guvenli, satirlar
            except asyncpg.PostgresError as e:
                hata = f"Çalıştırma: {e}"
                iz.append(f"Çalıştırma[tur {tur}]: HATA — {e}")

        # Buraya geldiyse bir kontrol/çalıştırma başarısız → self-correction
        son_hata = hata
        log.warning("[tur %d] %s", tur, son_hata)
        if tur > MAKS_DUZELTME:
            break
        iz.append(f"Self-correction[tur {tur}→{tur+1}]: hata modele geri besleniyor")
        duzelt_istem = prompt_yukle(
            "sql_duzelt", sema=sema_metni, soru=soru, hatali_sql=aday, hata=son_hata
        )
        aday = sql_temizle(
            model.cagir(sistem=duzelt_istem, kullanici=soru, sicaklik=0.0)
        )

    raise CalismadiHatasi(f"Geçerli SQL üretilemedi. Son hata: {son_hata}")


async def sor(soru: str, model: LLM | None = None) -> dict:
    """Bir Türkçe soruyu uçtan uca yanıtlar.

    Dönüş: { soru, sql, satir_sayisi, satirlar, metrikler, icgoruler,
             cekinceler, ozet_tr, sadik, iz }  — `iz` = kontrol katmanı denetim izi.
    """
    model = model or LLM()
    iz: list[str] = []  # audit izi: hangi kontrol ne karar verdi

    # Kontrol 2/0 için yapısal şema (tablo→kolon)
    yapi = await sema.sema_yapisi()

    # KONTROL 0 — Eksik-kavram guard'ı (müşteri/kâr/maliyet/stok yoksa uydurma)
    eksik = on_kontrol.eksik_kavram(soru, yapi)
    if eksik:
        iz.append(f"K0 eksik-kavram: ENGELLENDİ — {eksik[:60]}...")
        log.info("K0 engelledi: %s", soru)
        return {
            "soru": soru, "sql": None, "satir_sayisi": 0, "satirlar": [],
            "metrikler": {}, "icgoruler": [eksik], "cekinceler": [eksik],
            "ozet_tr": eksik, "sadik": True, "iz": iz,
        }
    iz.append("K0 eksik-kavram: GEÇTİ")

    # 1) Şema linkleme
    tum_ddl = await sema.sema_ddl_getir()
    ornekler = retrieval.benzer_ornekler(soru, k=5)
    ipucu_tablolar = [t for o in ornekler for t in o.get("tablolar", [])]
    tablolar = await sema.ilgili_tablolar(soru, tum_ddl, ornek_tablolar=ipucu_tablolar)
    sema_metni = sema.ddl_metni(tablolar, tum_ddl)
    # Value linking: kategori/şehir/marka gibi düşük-kardinaliteli değerleri ekle
    # → model 'Temizlik'in kategoriler.ad değeri olduğunu bilir, doğru join'ler.
    deger_metni = await sema.deger_ipuclari()
    if deger_metni:
        sema_metni = f"{sema_metni}\n\n{deger_metni}"
    ornek_metni = retrieval.few_shot_metni(ornekler)

    # 2-7) Üret + KONTROL 1 (güvenlik) + KONTROL 2 (doğruluk) + çalıştır + self-correction
    guvenli_sql, satirlar = await _uret_dogrula_calistir(
        soru, sema_metni, ornek_metni, yapi, model, iz
    )

    # D2 — Boş-sonuç kurtarma: metin filtresi 0 döndürdüyse ILIKE %...% ile yeniden dene
    if not satirlar:
        alt = analiz_kontrol.gevset_metin_filtreleri(guvenli_sql)
        if alt:
            try:
                alt_g = sql_guvenlik.dogrula_ve_hazirla(alt)
                ok, _ = await sql_kontrol.kontrol2(alt_g, yapi)
                if ok:
                    alt_satir = await db_sorgu.calistir_select(alt_g)
                    if alt_satir:
                        guvenli_sql, satirlar = alt_g, alt_satir
                        iz.append(f"D2 boş-sonuç kurtarma: ILIKE %...% → {len(alt_satir)} satır")
            except Exception as e:  # noqa: BLE001
                log.warning("D2 kurtarma hatası: %s", e)

    # 8) KONTROL 3 — Analiz doğrulama: sonuç kesikse pay için gerçek toplamı çek
    profil = sql_kontrol.sorgu_profili(guvenli_sql)
    gercek_toplam = await _gercek_toplam_getir(guvenli_sql, satirlar, profil, yapi)
    if gercek_toplam is not None:
        iz.append(f"K3 analiz: kesik sonuç → gerçek toplam ({gercek_toplam:.0f}) çekildi")
    else:
        iz.append("K3 analiz: pay paydası doğrudan (tam evren veya toplanamaz ölçü)")

    # 9) Rapor (3 katman: deterministik özet → içgörü seçimi → LLM anlatım)
    sonuc = rapor.raporla(soru, satirlar, model, profil=profil, gercek_toplam=gercek_toplam)

    # 10) Sayısal+isim sadakati: anlatım uydurursa deterministik özete düşülür (anlat içinde)
    sadik, uydurma = analiz_kontrol.sadakat_kontrol(sonuc["ozet_tr"], sonuc["bulgular"])
    iz.append("K-sadakat: GEÇTİ" if sadik else f"K-sadakat: anlatım reddedildi — {uydurma}")
    if not sadik:
        log.warning("Sadakat uyarısı — olgularda olmayan: %s", uydurma)

    # 11) Öğrenme — VARSAYILAN KAPALI. Auto-learning, çalışan-ama-yanlış veya
    #     normalize-edilmiş ara SQL'i (örn. bare `~*`) few-shot'a kaydedip
    #     modeli kirletiyordu. Yalnızca gold-doğrulanmış örneklerle beslenmeli.
    #     Açmak için: export OGRENME=1
    if os.environ.get("OGRENME") == "1":
        try:
            retrieval.ogret(soru, guvenli_sql, tablolar)
        except Exception as e:  # noqa: BLE001 — öğrenme hatası ana akışı bozmamalı
            log.warning("Few-shot kaydı başarısız: %s", e)

    return {
        "soru": soru,
        "sql": guvenli_sql,
        "satir_sayisi": sonuc["satir_sayisi"],
        "satirlar": sonuc["df"].to_dict("records"),
        "metrikler": sonuc["metrikler"],
        "icgoruler": sonuc["icgoruler"],
        "cekinceler": sonuc["cekinceler"],
        "ozet_tr": sonuc["ozet_tr"],
        "sadik": sadik,
        "iz": iz,
    }


async def _gercek_toplam_getir(
    guvenli_sql: str, satirlar: list[dict], profil: dict, yapi: dict[str, set[str]]
) -> float | None:
    """KONTROL 3 yardımcısı: sonuç kesikse (LIMIT ve satır=limit) ölçü kolonunun
    GERÇEK toplamını ayrı bir agregat sorgusuyla çeker. Sorgu Kontrol 1+2'den
    geçirilir. Üretilemez/geçemezse None (→ pay 'gösterilenler içinde' olur).
    """
    kesik = bool(
        profil.get("limit_var")
        and profil.get("limit_n") is not None
        and len(satirlar) >= profil["limit_n"]
    )
    if not kesik:
        return None
    olcu = rapor.olcu_kolonu(satirlar, profil)
    if not olcu:
        return None
    # Toplanamaz ölçüde (AVG/ham fiyat) grand total anlamsız → çekme
    if not sql_kontrol.toplanabilir_mi(profil, olcu):
        return None
    gt_sql = analiz_kontrol.grand_total_sql(guvenli_sql, olcu)
    if not gt_sql:
        return None
    try:
        gt_guvenli = sql_guvenlik.dogrula_ve_hazirla(gt_sql)
        ok, _ = await sql_kontrol.kontrol2(gt_guvenli, yapi)
        if not ok:
            return None
        rows = await db_sorgu.calistir_select(gt_guvenli)
        if rows and rows[0].get("gercek_toplam") is not None:
            return float(rows[0]["gercek_toplam"])
    except Exception as e:  # noqa: BLE001 — grand total alınamazsa pay bastırılır
        log.warning("Grand total alınamadı: %s", e)
    return None
