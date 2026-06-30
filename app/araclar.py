"""Ortak küçük yardımcılar (prompt yükleme, SQL temizleme)."""
import os
import re

_PROMPT_DIZIN = os.path.join(os.path.dirname(__file__), "prompts")


def prompt_yukle(ad: str, **degiskenler) -> str:
    """prompts/<ad>.md dosyasını okur ve {degisken} alanlarını doldurur.

    str.format yerine basit replace kullanılır — şema/SQL içindeki süslü
    parantezlerin format'ı bozmaması için.
    """
    yol = os.path.join(_PROMPT_DIZIN, f"{ad}.md")
    with open(yol, encoding="utf-8") as f:
        metin = f.read()
    for anahtar, deger in degiskenler.items():
        metin = metin.replace("{" + anahtar + "}", str(deger))
    return metin


def sql_temizle(ham: str) -> str:
    """Model çıktısından SQL'i ayıklar: markdown kod bloğu, ön/son metin temizliği."""
    metin = ham.strip()
    # ```sql ... ``` veya ``` ... ``` bloğunu çıkar
    blok = re.search(r"```(?:sql)?\s*(.+?)```", metin, re.DOTALL | re.IGNORECASE)
    if blok:
        metin = blok.group(1).strip()
    # Bazı modeller "SQL:" ön eki koyar
    metin = re.sub(r"^\s*sql\s*:\s*", "", metin, flags=re.IGNORECASE)
    return metin.strip().rstrip(";").strip()
