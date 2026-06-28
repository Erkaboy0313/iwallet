"""Story 2.3 — Gemini client tests with `httpx.MockTransport`.

Pattern lifted from `currencies/tests/test_cbu_client.py`.
"""

from __future__ import annotations

import json
from datetime import date

import httpx
import pytest

from voice.exceptions import GeminiUnavailableError
from voice.gemini_client import GeminiClient

SAMPLE_PARSED = {
    "transactions": [
        {
            "type": "expense",
            "amount": "25000.00",
            "currency": "UZS",
            "category_slug": "food",
            "counterparty": "",
            "date": "2026-06-28",
            "note": "qahva",
            "confidence": 0.94,
            "ambiguous_fields": [],
        }
    ],
    "recurring_intent": None,
}


def _gemini_response_body(parsed: dict) -> dict:
    """Wrap a parsed payload in the candidates.parts.text shape Gemini returns."""
    return {
        "candidates": [
            {
                "content": {"parts": [{"text": json.dumps(parsed)}]},
                "finishReason": "STOP",
            }
        ]
    }


async def _no_sleep(_seconds: float) -> None:
    return None


def _make_client(handler, *, max_attempts: int = 3) -> GeminiClient:
    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport)
    return GeminiClient(
        api_key="test-key",
        client=client,
        max_attempts=max_attempts,
        backoff=(0.0, 0.0, 0.0),
    )


@pytest.mark.asyncio
async def test_happy_path_returns_parsed_payload() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_gemini_response_body(SAMPLE_PARSED))

    client = _make_client(handler)
    try:
        result = await client.transcribe_and_parse(b"\x00" * 256, today=date(2026, 6, 28))
    finally:
        await client.aclose()
    assert result["transactions"][0]["amount"] == "25000.00"


@pytest.mark.asyncio
async def test_retries_on_transient_5xx_then_succeeds() -> None:
    calls = {"n": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(503, text="boom")
        return httpx.Response(200, json=_gemini_response_body(SAMPLE_PARSED))

    client = _make_client(handler)
    try:
        result = await client.transcribe_and_parse(
            b"\x00" * 256, today=date(2026, 6, 28), sleep=_no_sleep
        )
    finally:
        await client.aclose()
    assert result["transactions"][0]["currency"] == "UZS"
    assert calls["n"] == 3


@pytest.mark.asyncio
async def test_raises_unavailable_after_max_attempts() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="boom")

    client = _make_client(handler, max_attempts=3)
    try:
        with pytest.raises(GeminiUnavailableError):
            await client.transcribe_and_parse(
                b"\x00" * 256, today=date(2026, 6, 28), sleep=_no_sleep
            )
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_raises_unavailable_on_invalid_json_text_block() -> None:
    bad_body = {
        "candidates": [{"content": {"parts": [{"text": "not-valid-json"}]}, "finishReason": "STOP"}]
    }

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=bad_body)

    client = _make_client(handler, max_attempts=1)
    try:
        with pytest.raises(GeminiUnavailableError):
            await client.transcribe_and_parse(
                b"\x00" * 256, today=date(2026, 6, 28), sleep=_no_sleep
            )
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_extract_json_handles_direct_payload_shape() -> None:
    """Some test harnesses return the parsed payload directly (no candidates)."""

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=SAMPLE_PARSED)

    client = _make_client(handler)
    try:
        result = await client.transcribe_and_parse(b"\x00" * 256, today=date(2026, 6, 28))
    finally:
        await client.aclose()
    assert result["transactions"][0]["category_slug"] == "food"


@pytest.mark.asyncio
async def test_retries_use_provided_sleep_callable() -> None:
    """Custom sleep gets invoked once per failed attempt before the final one."""
    calls = {"n": 0}
    sleeps: list[float] = []

    def handler(_request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] < 2:
            return httpx.Response(500)
        return httpx.Response(200, json=_gemini_response_body(SAMPLE_PARSED))

    async def sleep(seconds: float) -> None:
        sleeps.append(seconds)

    transport = httpx.MockTransport(handler)
    http = httpx.AsyncClient(transport=transport)
    client = GeminiClient(api_key="x", client=http, max_attempts=3, backoff=(0.5, 1.0, 2.0))
    try:
        await client.transcribe_and_parse(b"\x00" * 256, today=date(2026, 6, 28), sleep=sleep)
    finally:
        await client.aclose()
    assert sleeps == [0.5]
