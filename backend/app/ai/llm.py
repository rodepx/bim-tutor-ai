"""Configuración y cliente HTTP mínimo para OpenRouter (API compatible con OpenAI).

Nunca lanza excepciones hacia afuera: cualquier error devuelve None y el llamador
usa el modo mock determinista.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

import httpx

log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[3]
TIMEOUT_S = 20.0
DEFAULT_MODEL = "anthropic/claude-sonnet-5.5"
DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"

try:  # .env en la raíz del repo, si existe (no pisa variables ya definidas)
    from dotenv import load_dotenv

    _env = REPO_ROOT / ".env"
    if _env.is_file():
        load_dotenv(_env, override=False)
except Exception:  # pragma: no cover
    pass


def llm_mode() -> str:
    """'openrouter' si hay API key y el proveedor no es mock; si no, 'mock'."""
    provider = (os.getenv("LLM_PROVIDER") or "openrouter").strip().lower()
    key = (os.getenv("LLM_API_KEY") or "").strip()
    if provider == "mock" or not key:
        return "mock"
    return "openrouter"


def chat(messages: list[dict], max_tokens: int = 400, temperature: float = 0.2) -> str | None:
    """Llama a /chat/completions. Devuelve el contenido o None ante cualquier fallo."""
    if llm_mode() != "openrouter":
        return None
    base = (os.getenv("LLM_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
    model = os.getenv("LLM_MODEL") or DEFAULT_MODEL
    try:
        resp = httpx.post(
            f"{base}/chat/completions",
            headers={
                "Authorization": f"Bearer {os.getenv('LLM_API_KEY', '').strip()}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            },
            timeout=TIMEOUT_S,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        if not isinstance(content, str) or not content.strip():
            return None
        return content.strip()
    except Exception as exc:  # red, HTTP, JSON, estructura inesperada
        log.warning("LLM no disponible, se usa modo mock: %s", type(exc).__name__)
        return None
