"""Gemini 2.0 Flash HTTP client (Story 2.3).

Uses `httpx.AsyncClient` directly against the public generativelanguage API
rather than the google-genai SDK so we can:
  - Inject an `httpx.MockTransport` from tests with zero monkey-patching.
  - Keep retry semantics explicit and unit-testable (no hidden SDK retries).
  - Stay drop-in compatible with the gemini-2.0-flash endpoint URL Eric will
    set on the droplet.

Audio bytes are streamed as base64 inline_data. We never log the audio nor the
raw request body — only counts and status codes (NFR9 audio-not-stored).
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
from datetime import date as _date_type
from typing import Any

import httpx

from .exceptions import GeminiUnavailableError
from .prompts import build_voice_parse_prompt

logger = logging.getLogger(__name__)

GEMINI_BASE_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
)
DEFAULT_TIMEOUT = httpx.Timeout(30.0, connect=10.0)
MAX_ATTEMPTS = 3
BACKOFF_SECONDS: tuple[float, ...] = (0.5, 1.0, 2.0)

_RESPONSE_MIME = "application/json"


class GeminiClient:
    """Thin async wrapper around the generativelanguage.googleapis.com endpoint."""

    def __init__(
        self,
        *,
        api_key: str,
        endpoint: str = GEMINI_BASE_URL,
        client: httpx.AsyncClient | None = None,
        timeout: httpx.Timeout = DEFAULT_TIMEOUT,
        max_attempts: int = MAX_ATTEMPTS,
        backoff: tuple[float, ...] = BACKOFF_SECONDS,
    ) -> None:
        self._api_key = api_key
        self._endpoint = endpoint
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(timeout=timeout)
        self._max_attempts = max_attempts
        self._backoff = backoff

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> GeminiClient:
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.aclose()

    async def transcribe_and_parse(
        self,
        audio_bytes: bytes,
        *,
        user_currency_default: str = "UZS",
        today: _date_type | None = None,
        audio_mime: str = "audio/webm",
        sleep: Any = None,
    ) -> dict[str, Any]:
        """Call Gemini and return the parsed JSON payload (a plain dict).

        Retries up to `max_attempts` on transient HTTP errors with the configured
        backoff. Raises :class:`GeminiUnavailableError` on terminal failure.
        """
        today = today or _date_type.today()
        prompt = build_voice_parse_prompt(
            default_currency=user_currency_default,
            today_iso=today.isoformat(),
        )
        request_body = _build_request_body(prompt, audio_bytes, audio_mime)
        sleep_fn = sleep or asyncio.sleep

        last_error: Exception | None = None
        for attempt in range(1, self._max_attempts + 1):
            try:
                response = await self._client.post(
                    self._endpoint,
                    params={"key": self._api_key},
                    json=request_body,
                )
                response.raise_for_status()
                payload = response.json()
            except (httpx.HTTPError, ValueError) as exc:
                last_error = exc
                wait = self._backoff[min(attempt - 1, len(self._backoff) - 1)]
                logger.warning(
                    "voice.gemini: attempt=%d failed (%s) — sleep=%.2fs",
                    attempt,
                    type(exc).__name__,
                    wait,
                )
                if attempt < self._max_attempts:
                    await sleep_fn(wait)
                continue
            return _extract_json(payload)

        msg = f"Gemini unreachable after {self._max_attempts} attempts"
        raise GeminiUnavailableError(msg) from last_error


def _build_request_body(prompt: str, audio_bytes: bytes, mime: str) -> dict[str, Any]:
    """Compose the generateContent payload with text + inline audio."""
    inline_data_b64 = base64.b64encode(audio_bytes).decode("ascii")
    return {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": mime, "data": inline_data_b64}},
                ],
            }
        ],
        "generationConfig": {
            "responseMimeType": _RESPONSE_MIME,
            "temperature": 0.0,
        },
    }


def _extract_json(payload: dict[str, Any]) -> dict[str, Any]:
    """Pull the model's JSON-text part out of the generateContent response.

    Tolerates the SDK's `candidates[].content.parts[].text` shape as well as a
    direct dict payload (some mock servers return the parsed JSON directly).
    """
    if not isinstance(payload, dict):
        raise GeminiUnavailableError("Gemini returned non-dict payload")

    candidates = payload.get("candidates") or []
    if candidates:
        try:
            parts = candidates[0]["content"]["parts"]
            text_block = next((p.get("text") for p in parts if "text" in p), None)
        except (KeyError, IndexError, TypeError) as exc:
            raise GeminiUnavailableError("Gemini response missing candidates.parts") from exc
        if not text_block:
            raise GeminiUnavailableError("Gemini response had no text part")
        try:
            return json.loads(text_block)
        except json.JSONDecodeError as exc:
            raise GeminiUnavailableError("Gemini returned non-JSON text") from exc

    # Some mock paths short-circuit straight to the parsed payload.
    if {"transactions"} <= payload.keys():
        return payload

    raise GeminiUnavailableError("Gemini response had no candidates")
