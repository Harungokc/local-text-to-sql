"""
FastAPI Servisi — Text-to-SQL AI Agent
=======================================

Uç noktalar:
  * GET  /saglik  → sağlık kontrolü (model + DB erişimi)
  * POST /sor     → Türkçe soru → SQL + sonuç + Türkçe özet

Çalıştırma (Faz 1, M1 + Ollama):
  ollama serve &
  ollama pull qwen2.5-coder:7b
  export SORGU_DATABASE_URL="postgresql://readonly_user:...@localhost:5432/sirket"
  uvicorn api:app --host 127.0.0.1 --port 9000
"""
import logging
import os

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

import db_sorgu
import runner
from llm import LLM

_WEB_DIZIN = os.path.join(os.path.dirname(__file__), "..", "web")

# --- Loglama (fabrika konvansiyonu: UTF-8, dosya + konsol) ---
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("logs/api.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("api")

app = FastAPI(title="Şirket Sorgu — Text-to-SQL Agent", version="0.1")

# Tek model örneği (token sayaçları süreç boyunca toplanır)
_model = LLM()


class SoruIstegi(BaseModel):
    soru: str


@app.get("/")
async def arayuz() -> FileResponse:
    """Tek-sayfa web arayüzü (web/index.html)."""
    return FileResponse(os.path.join(_WEB_DIZIN, "index.html"))


@app.get("/saglik")
async def saglik() -> dict:
    """Model ve veritabanı erişimini kontrol eder."""
    durum = {"durum": "ok", "model": _model.client.base_url and str(_model.client.base_url)}
    try:
        async with db_sorgu.baglanti() as c:
            await c.fetchval("SELECT 1")
        durum["veritabani"] = "baglandi"
    except Exception as e:  # noqa: BLE001
        durum["durum"] = "uyari"
        durum["veritabani"] = f"hata: {e}"
    return durum


@app.post("/sor")
async def sor(istek: SoruIstegi) -> dict:
    """Türkçe soruyu yanıtlar: SQL üret → çalıştır → Türkçe rapor."""
    soru = (istek.soru or "").strip()
    if not soru:
        raise HTTPException(status_code=400, detail="Soru boş olamaz.")
    log.info("Soru: %s", soru)
    try:
        sonuc = await runner.sor(soru, model=_model)
        log.info("SQL: %s", sonuc["sql"])
        return sonuc
    except runner.CalismadiHatasi as e:
        log.error("Yanıt üretilemedi: %s", e)
        raise HTTPException(status_code=422, detail=str(e)) from e
    except Exception as e:  # noqa: BLE001
        log.exception("Beklenmeyen hata")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.on_event("shutdown")
async def kapanis() -> None:
    await db_sorgu.kapat()
