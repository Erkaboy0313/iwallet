"""Story 9.2 — TelegramBotClient httpx mock tests (retry + transient errors)."""

from __future__ import annotations

import httpx
import pytest

from notifications.bot.telegram_client import TelegramAPIError, TelegramBotClient


async def _no_sleep(_seconds: float) -> None:
    return None


def _client(handler, *, max_attempts: int = 3) -> TelegramBotClient:
    transport = httpx.MockTransport(handler)
    http = httpx.AsyncClient(transport=transport)
    return TelegramBotClient(
        bot_token="fake-token",
        client=http,
        max_attempts=max_attempts,
        backoff=(0.0, 0.0, 0.0),
    )


@pytest.mark.asyncio
async def test_send_message_happy_path_returns_ok_payload() -> None:
    seen: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append({"url": str(request.url), "json": _json_body(request)})
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 9}})

    client = _client(handler)
    try:
        result = await client.send_message(chat_id=123, text="Hello")
    finally:
        await client.aclose()

    assert result["ok"] is True
    assert seen[0]["url"].endswith("/botfake-token/sendMessage")
    assert seen[0]["json"]["chat_id"] == 123
    assert seen[0]["json"]["text"] == "Hello"


@pytest.mark.asyncio
async def test_call_retries_on_5xx_then_succeeds() -> None:
    state = {"n": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        state["n"] += 1
        if state["n"] < 3:
            return httpx.Response(503, text="overloaded")
        return httpx.Response(200, json={"ok": True, "result": {}})

    client = _client(handler)
    try:
        result = await client.send_message(chat_id=1, text="x", sleep=_no_sleep)
    finally:
        await client.aclose()
    assert result["ok"] is True
    assert state["n"] == 3


@pytest.mark.asyncio
async def test_call_retries_on_429_rate_limit() -> None:
    state = {"n": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        state["n"] += 1
        if state["n"] < 2:
            return httpx.Response(429, json={"ok": False, "description": "slow down"})
        return httpx.Response(200, json={"ok": True})

    client = _client(handler)
    try:
        await client.send_message(chat_id=1, text="x", sleep=_no_sleep)
    finally:
        await client.aclose()
    assert state["n"] == 2


@pytest.mark.asyncio
async def test_call_raises_after_max_attempts_on_persistent_5xx() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    client = _client(handler, max_attempts=3)
    try:
        with pytest.raises(TelegramAPIError):
            await client.send_message(chat_id=1, text="x", sleep=_no_sleep)
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_call_raises_immediately_on_4xx_terminal() -> None:
    """400 BAD_REQUEST → terminal; bot tokens and chat_ids don't recover."""
    calls = {"n": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(400, json={"ok": False, "description": "chat not found"})

    client = _client(handler, max_attempts=3)
    try:
        with pytest.raises(TelegramAPIError):
            await client.send_message(chat_id=1, text="x", sleep=_no_sleep)
    finally:
        await client.aclose()
    assert calls["n"] == 1  # no retry on terminal 4xx


@pytest.mark.asyncio
async def test_call_raises_on_ok_false_payload() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": False, "description": "denied"})

    client = _client(handler)
    try:
        with pytest.raises(TelegramAPIError):
            await client.send_message(chat_id=1, text="x", sleep=_no_sleep)
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_set_webhook_passes_secret_token() -> None:
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(_json_body(request))
        return httpx.Response(200, json={"ok": True, "result": True})

    client = _client(handler)
    try:
        await client.set_webhook(
            url="https://example.com/bot/webhook/xyz/",
            secret_token="xyz",
            allowed_updates=["message", "callback_query"],
        )
    finally:
        await client.aclose()
    assert seen["url"] == "https://example.com/bot/webhook/xyz/"
    assert seen["secret_token"] == "xyz"
    assert seen["allowed_updates"] == ["message", "callback_query"]


@pytest.mark.asyncio
async def test_set_my_commands_sends_command_list() -> None:
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(_json_body(request))
        return httpx.Response(200, json={"ok": True, "result": True})

    client = _client(handler)
    try:
        await client.set_my_commands(
            commands=[{"command": "start", "description": "Boshlash"}],
        )
    finally:
        await client.aclose()
    assert seen["commands"][0]["command"] == "start"


def _json_body(request: httpx.Request) -> dict:
    import json

    return json.loads(request.content.decode("utf-8"))
