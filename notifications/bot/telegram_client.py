"""Async Telegram Bot API client (Story 9.2 backbone).

Thin `httpx.AsyncClient` wrapper around the Bot API. Pattern lifted from
`voice/gemini_client.py` so retries + transport injection (for `MockTransport`
in tests) stay consistent across the codebase.

Why not python-telegram-bot? PTB is already in requirements (we still use it
indirectly via type hints if needed) but its `Application` machinery wants to
own the asyncio loop, polling, and webhook routing. We need exactly two HTTP
methods (`sendMessage`, `editMessageText` + bot setup helpers) and full
control over retries/idempotency, so a plain httpx call is simpler and
trivially mockable.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

TELEGRAM_API_BASE = "https://api.telegram.org"
DEFAULT_TIMEOUT = httpx.Timeout(15.0, connect=5.0)
MAX_ATTEMPTS = 3
BACKOFF_SECONDS: tuple[float, ...] = (0.5, 1.5, 3.0)


class TelegramAPIError(Exception):
    """Terminal failure after all retries (or a 4xx the bot can't recover from)."""


class TelegramBotClient:
    """Thin async wrapper around https://api.telegram.org/bot<token>/."""

    def __init__(
        self,
        *,
        bot_token: str,
        client: httpx.AsyncClient | None = None,
        timeout: httpx.Timeout = DEFAULT_TIMEOUT,
        max_attempts: int = MAX_ATTEMPTS,
        backoff: tuple[float, ...] = BACKOFF_SECONDS,
        base_url: str = TELEGRAM_API_BASE,
    ) -> None:
        if not bot_token:
            raise TelegramAPIError("bot_token not configured")
        self._token = bot_token
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(timeout=timeout)
        self._max_attempts = max_attempts
        self._backoff = backoff
        self._base_url = base_url.rstrip("/")

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> TelegramBotClient:
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.aclose()

    def _url(self, method: str) -> str:
        return f"{self._base_url}/bot{self._token}/{method}"

    async def call(
        self,
        method: str,
        payload: dict[str, Any],
        *,
        sleep: Any = None,
    ) -> dict[str, Any]:
        """POST `payload` to `/bot<token>/<method>` with bounded retries.

        Retries on network errors and HTTP 5xx / 429. Raises
        :class:`TelegramAPIError` on terminal failure (3 consecutive transient
        errors, or a 4xx that isn't 429). 4xx with `{"ok": false}` body is
        surfaced as a terminal error too — bot tokens / chat_ids don't recover
        from being wrong.
        """
        sleep_fn = sleep or asyncio.sleep
        last_error: Exception | None = None

        for attempt in range(1, self._max_attempts + 1):
            try:
                response = await self._client.post(self._url(method), json=payload)
            except httpx.HTTPError as exc:
                last_error = exc
                logger.warning(
                    "telegram.%s attempt=%d network_error=%s",
                    method,
                    attempt,
                    exc.__class__.__name__,
                )
                await self._maybe_sleep(attempt, sleep_fn)
                continue

            if response.status_code >= 500 or response.status_code == 429:
                last_error = TelegramAPIError(
                    f"transient http {response.status_code}: {response.text[:200]}"
                )
                logger.warning(
                    "telegram.%s attempt=%d transient_status=%s",
                    method,
                    attempt,
                    response.status_code,
                )
                await self._maybe_sleep(attempt, sleep_fn)
                continue

            if response.status_code >= 400:
                # 4xx that isn't 429 (rate limit) → terminal. Bad token, bad
                # chat_id, blocked by user, message too long, etc.
                raise TelegramAPIError(
                    f"telegram.{method} terminal http {response.status_code}: {response.text[:200]}"
                )

            data = response.json()
            if not data.get("ok"):
                raise TelegramAPIError(f"telegram.{method} rejected: {data}")
            return data

        raise TelegramAPIError(
            f"telegram.{method} unreachable after {self._max_attempts} attempts"
        ) from last_error

    async def _maybe_sleep(self, attempt: int, sleep_fn) -> None:
        if attempt >= self._max_attempts:
            return
        wait = self._backoff[min(attempt - 1, len(self._backoff) - 1)]
        await sleep_fn(wait)

    # ---------- convenience wrappers ----------

    async def send_message(
        self,
        *,
        chat_id: int,
        text: str,
        reply_markup: dict[str, Any] | None = None,
        parse_mode: str | None = None,
        sleep: Any = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"chat_id": chat_id, "text": text}
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        if parse_mode is not None:
            payload["parse_mode"] = parse_mode
        return await self.call("sendMessage", payload, sleep=sleep)

    async def edit_message_text(
        self,
        *,
        chat_id: int,
        message_id: int,
        text: str,
        reply_markup: dict[str, Any] | None = None,
        parse_mode: str | None = None,
        sleep: Any = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
        }
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        if parse_mode is not None:
            payload["parse_mode"] = parse_mode
        return await self.call("editMessageText", payload, sleep=sleep)

    async def answer_callback_query(
        self,
        *,
        callback_query_id: str,
        text: str | None = None,
        show_alert: bool = False,
        sleep: Any = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"callback_query_id": callback_query_id}
        if text is not None:
            payload["text"] = text
        if show_alert:
            payload["show_alert"] = True
        return await self.call("answerCallbackQuery", payload, sleep=sleep)

    async def set_webhook(
        self,
        *,
        url: str,
        secret_token: str | None = None,
        allowed_updates: list[str] | None = None,
        sleep: Any = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"url": url}
        if secret_token:
            payload["secret_token"] = secret_token
        if allowed_updates is not None:
            payload["allowed_updates"] = allowed_updates
        return await self.call("setWebhook", payload, sleep=sleep)

    async def set_my_commands(
        self,
        *,
        commands: list[dict[str, str]],
        sleep: Any = None,
    ) -> dict[str, Any]:
        return await self.call("setMyCommands", {"commands": commands}, sleep=sleep)
