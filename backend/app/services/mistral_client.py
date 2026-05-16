"""
Client HTTP pour l'API Mistral (chat completions).
Clé : variable d'environnement MISTRAL_API_KEY (ne jamais committer la clé).
"""

from __future__ import annotations

import base64
import logging
import os
from typing import Any, Dict, List

import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger("autograde")


def _chat_url() -> str:
    return os.environ.get(
        "MISTRAL_API_URL", "https://api.mistral.ai/v1/chat/completions"
    ).rstrip("/")


def _headers() -> Dict[str, str]:
    key = (os.environ.get("MISTRAL_API_KEY") or "").strip()
    if not key:
        raise ValueError("MISTRAL_API_KEY manquante dans l'environnement (.env du backend).")
    return {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


def _post_chat(payload: Dict[str, Any], timeout: int = 300) -> str:
    url = _chat_url()
    r = requests.post(url, headers=_headers(), json=payload, timeout=timeout)
    if r.status_code >= 400:
        detail = r.text[:2000]
        try:
            err = r.json()
            detail = str(err.get("message", err.get("detail", detail)))
        except Exception:
            pass
        raise RuntimeError(f"Mistral API {r.status_code}: {detail}")
    data = r.json()
    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError(f"Réponse Mistral sans choices : {data}")
    msg = choices[0].get("message") or {}
    content = msg.get("content")
    if content is None or (isinstance(content, str) and not content.strip()):
        raise RuntimeError("Réponse Mistral vide.")
    if isinstance(content, str):
        return content.strip()
    return str(content).strip()


@retry(
    wait=wait_exponential(multiplier=1, min=2, max=20),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type((requests.RequestException, RuntimeError)),
    reraise=True,
    before_sleep=lambda rs: logger.warning(
        "Retry Mistral: tentative %s — %s", rs.attempt_number, rs.outcome.exception()
    ),
)
def mistral_chat_text(
    user_prompt: str,
    *,
    json_mode: bool = False,
    max_tokens: int = 8192,
    model: str | None = None,
) -> str:
    m = (model or os.environ.get("MISTRAL_MODEL", "mistral-small-latest")).strip()
    max_tokens = max(256, min(int(max_tokens), 128_000))
    payload: Dict[str, Any] = {
        "model": m,
        "messages": [{"role": "user", "content": user_prompt}],
        "max_tokens": max_tokens,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    return _post_chat(payload)


@retry(
    wait=wait_exponential(multiplier=1, min=2, max=20),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type((requests.RequestException, RuntimeError)),
    reraise=True,
    before_sleep=lambda rs: logger.warning(
        "Retry Mistral vision: tentative %s — %s", rs.attempt_number, rs.outcome.exception()
    ),
)
def mistral_chat_vision(
    user_prompt: str,
    image_bytes: bytes,
    mime_type: str = "image/jpeg",
    *,
    json_mode: bool = True,
    max_tokens: int = 4096,
    model: str | None = None,
) -> str:
    m = (model or os.environ.get("MISTRAL_VISION_MODEL", "mistral-small-latest")).strip()
    b64 = base64.standard_b64encode(image_bytes).decode("ascii")
    data_url = f"data:{mime_type};base64,{b64}"
    content: List[Dict[str, Any]] = [
        {"type": "text", "text": user_prompt},
        {"type": "image_url", "image_url": data_url},
    ]
    max_tokens = max(256, min(int(max_tokens), 32_768))
    payload: Dict[str, Any] = {
        "model": m,
        "messages": [{"role": "user", "content": content}],
        "max_tokens": max_tokens,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    return _post_chat(payload, timeout=120)
