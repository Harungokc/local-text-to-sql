"""
KONTROL 0 — Giriş / Eksik-Kavram Denetimi (deterministik)
==========================================================

Soru, veritabanında KARŞILIĞI OLMAYAN bir kavram istiyorsa (müşteri, kâr,
maliyet, stok...) sistem uydurma cevap üretmek yerine "bu veri yok" der.

Örnek: "ortalama bir müşteri ne kadar harcıyor" → müşteri tablosu yok →
model rastgele bir AVG uydurur. Bu guard onu çalıştırmadan durdurur.

Şema-farkında: bir kavram ancak şemada onu karşılayan kolon YOKSA engellenir.
Gerçek bir DB'de 'maliyet' kolonu varsa, kâr sorusu engellenmez.
"""
import re

# kavram → (soru'da aranan KÖKLER, şemada karşılığı sayılan kolon ipuçları, açıklama)
# NOT: Kökler kelime-BAŞINDAN eşleşir ve Türkçe ekleri yutar
# ("müşteri" → müşterimiz/müşteriler/müşteriye). Bu yüzden çakışmaya açık
# kısa kökler (bare "kar" → karşılaştır/karar/kara) listede YOK; yalnızca
# net kökler kullanılır.
_KAVRAMLAR = [
    (
        ["müşteri", "musteri", "customer", "abone", "cari"],
        ["musteri", "customer", "cari", "abone"],
        "müşteri",
    ),
    (
        ["kâr", "kârlı", "karlı", "kârlılık", "karlılık", "profit", "marj", "kazanç", "kazanc"],
        ["kar", "profit", "marj", "kazanc", "maliyet", "cost"],
        "kâr/kârlılık",
    ),
    (
        ["maliyet", "masraf", "cost"],
        ["maliyet", "cost", "gider", "masraf"],
        "maliyet/gider",
    ),
    (
        ["stok", "stock", "envanter", "depo"],
        ["stok", "stock", "envanter", "depo", "miktar"],
        "stok/envanter",
    ),
    (
        ["indirim", "iskonto", "discount", "kampanya"],
        ["indirim", "iskonto", "discount", "kampanya"],
        "indirim/kampanya",
    ),
]


def eksik_kavram(soru: str, yapi: dict[str, set[str]]) -> str | None:
    """Soru, şemada olmayan bir kavram istiyorsa açıklayıcı mesaj döndürür.
    Aksi halde None (sorgu normal akışa devam eder)."""
    soru_l = (soru or "").lower()
    # Şemadaki tüm tablo+kolon adlarını tek metinde topla (küçük harf)
    sema_metni = " ".join(yapi.keys()) + " " + " ".join(k for kols in yapi.values() for k in kols)

    for kelimeler, kolon_ipuclari, etiket in _KAVRAMLAR:
        # Kelime BAŞINDAN eşle + Türkçe ekleri yut: 'müşterimiz' → 'müşteri' tetikler.
        # Kök sadece kelime başında aranır → 'karşılaştır' içindeki 'kar' tetiklemez
        # (zaten bare 'kar' listede yok). Ekler: Türkçe küçük harf sonekleri.
        desen = (
            r"\b(" + "|".join(re.escape(k) for k in kelimeler) + r")[a-zçğıöşü]*\b"
        )
        if re.search(desen, soru_l):
            # Şemada bu kavramı karşılayan kolon var mı?
            varmi = any(ip in sema_metni for ip in kolon_ipuclari)
            if not varmi:
                mevcut = ", ".join(sorted(yapi.keys()))
                return (
                    f"Bu soru '{etiket}' verisini gerektiriyor ancak veritabanında "
                    f"böyle bir alan yok. Yanlış/uydurma cevap vermemek için "
                    f"yanıtlamıyorum. Mevcut tablolar: {mevcut}."
                )
    return None
