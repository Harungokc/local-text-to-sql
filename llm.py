"""
Yerel LLM Wrapper (OpenAI-uyumlu)
==================================

fabrika/llm.py deseninin yerel sürümü. Anthropic yerine OpenAI istemcisini
YEREL bir endpoint'e yönlendirir — böylece veri/sorgu hiçbir bulut servisine
gitmez:

  * Faz 1 (geliştirme, M1 8GB):  Ollama   → http://127.0.0.1:11434/v1
  * Faz 2 (kiralık sunucu):      vLLM     → http://127.0.0.1:8000/v1  (SSH tüneli/iç ağ)

Fazlar arası geçişte SADECE VLLM_BASE_URL ve YEREL_MODEL env'leri değişir;
kod aynı kalır. api_key alanı dolu olmalı ama yerelde anlamsızdır.
"""
import os
from dataclasses import dataclass, field
from openai import OpenAI

# Model adı: Faz1'de Ollama etiketi (örn. "qwen2.5-coder:3b"),
# Faz2'de HF repo adı (örn. "Qwen/Qwen2.5-Coder-32B-Instruct-AWQ").
# NOT: Yerel fallback bilerek 3B. M1 8GB'de 7B yüklemek makineyi çökertiyor
# (RAM > 8GB → swap → kilitlenme). 7B/32B'yi YEREL_MODEL env'i ile yalnızca
# kiralık GPU'da (Faz 2) seç. Bu makinede 7B'yi yerel çalıştırma.
MODEL = os.environ.get("YEREL_MODEL", "qwen2.5-coder:3b")
BASE_URL = os.environ.get("VLLM_BASE_URL", "http://127.0.0.1:11434/v1")
API_KEY = os.environ.get("YEREL_API_KEY", "yerel")  # yerelde anlamsız ama gerekli


@dataclass
class Kullanim:
    """Yerel modelde para maliyeti yok; yalnızca izleme/log için sayaç."""
    girdi_token: int = 0
    cikti_token: int = 0
    cagri: int = 0


@dataclass
class LLM:
    client: OpenAI = field(
        default_factory=lambda: OpenAI(base_url=BASE_URL, api_key=API_KEY)
    )
    kullanim: Kullanim = field(default_factory=Kullanim)

    def cagir(
        self,
        sistem: str,
        kullanici: str,
        max_token: int = 2048,
        sicaklik: float = 0.0,
        frequency_penalty: float = 0.0,
        presence_penalty: float = 0.0,
    ) -> str:
        """Sistem + kullanıcı mesajıyla modeli çağırır, metin döndürür.

        sicaklik=0.0 → determinizm (SQL üretiminde varsayılan).
        frequency_penalty/presence_penalty → küçük modellerde (3B) tekrar
        döngüsünü ("bu bu bu...") engellemek için anlatımda kullanılır.
        """
        yanit = self.client.chat.completions.create(
            model=MODEL,
            temperature=sicaklik,
            max_tokens=max_token,
            frequency_penalty=frequency_penalty,
            presence_penalty=presence_penalty,
            messages=[
                {"role": "system", "content": sistem},
                {"role": "user", "content": kullanici},
            ],
        )
        u = getattr(yanit, "usage", None)
        if u is not None:
            self.kullanim.girdi_token += getattr(u, "prompt_tokens", 0) or 0
            self.kullanim.cikti_token += getattr(u, "completion_tokens", 0) or 0
        self.kullanim.cagri += 1
        return (yanit.choices[0].message.content or "").strip()
