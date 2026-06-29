"""
Few-shot Örnek Deposu (ChromaDB — yerel)
=========================================

Geçmiş "soru → SQL" çiftlerini yerel bir vektör veritabanında saklar ve yeni
bir soruya en benzer örnekleri getirir (RAG few-shot). Embedding'ler ChromaDB
içinde YERELDE üretilir/saklanır → veri dışarı çıkmaz.

Vanna'nın retrieval kavramını saf ChromaDB ile uygularız (bağımlılık az,
asyncpg/FastAPI yapımıza oturur). Doğruluğun anahtarı: modele örnek göstermek.

İki yetenek:
  * ogret(soru, sql, tablolar)  → örneği depoya ekle (seed + çalışma anında öğrenme)
  * benzer_ornekler(soru, k)     → en benzer k örneği getir
"""
import os
import chromadb

KOLEKSIYON_ADI = "few_shot_sorgular"
DEPO_YOLU = os.environ.get("CHROMA_YOLU", "./chroma_db")

_istemci: chromadb.ClientAPI | None = None
_koleksiyon = None


def _koleksiyon_al():
    """ChromaDB kalıcı istemcisini ve koleksiyonu (lazy) döndürür."""
    global _istemci, _koleksiyon
    if _koleksiyon is None:
        _istemci = chromadb.PersistentClient(path=DEPO_YOLU)
        # Varsayılan embedding fonksiyonu yereldir (all-MiniLM, ilk kullanımda iner).
        _koleksiyon = _istemci.get_or_create_collection(
            name=KOLEKSIYON_ADI,
            metadata={"hnsw:space": "cosine"},
        )
    return _koleksiyon


def ogret(soru: str, sql: str, tablolar: list[str] | None = None) -> None:
    """Bir soru→SQL örneğini depoya ekler/günceller.

    id olarak sorunun kendisini kullanırız → aynı soru tekrar gelirse üzerine yazar.
    tablolar: bu sorguda kullanılan tablo adları (şema linklemeye ipucu).
    """
    kol = _koleksiyon_al()
    kol.upsert(
        ids=[soru.strip().lower()[:256]],
        documents=[soru.strip()],
        metadatas=[{"sql": sql.strip(), "tablolar": ",".join(tablolar or [])}],
    )


def benzer_ornekler(soru: str, k: int = 5) -> list[dict]:
    """Soruya en benzer k örneği döndürür: [{soru, sql, tablolar}].

    Depo boşsa boş liste döner (Faz1 başlangıcında normal).
    """
    kol = _koleksiyon_al()
    if kol.count() == 0:
        return []
    sonuc = kol.query(
        query_texts=[soru.strip()],
        n_results=min(k, kol.count()),
    )
    ornekler = []
    belgeler = sonuc.get("documents", [[]])[0]
    metalar = sonuc.get("metadatas", [[]])[0]
    for belge, meta in zip(belgeler, metalar):
        tablolar = [t for t in (meta.get("tablolar") or "").split(",") if t]
        ornekler.append({"soru": belge, "sql": meta.get("sql", ""), "tablolar": tablolar})
    return ornekler


def ornek_sayisi() -> int:
    """Depodaki örnek sayısı (kurulum doğrulaması için)."""
    return _koleksiyon_al().count()


def few_shot_metni(ornekler: list[dict]) -> str:
    """Örnekleri prompt'a gömmek için biçimlendirir."""
    if not ornekler:
        return "(Henüz örnek yok.)"
    parcalar = []
    for o in ornekler:
        parcalar.append(f"Soru: {o['soru']}\nSQL: {o['sql']}")
    return "\n\n".join(parcalar)
