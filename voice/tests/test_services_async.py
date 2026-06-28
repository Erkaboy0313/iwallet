"""Story 2.3 — pipeline integration: GeminiClient + parser via services_async."""

from __future__ import annotations

import json

import httpx
import pytest

from transactions.tests.factories import UserFactory
from voice.exceptions import GeminiConfigError, NoTransactionsParsedError
from voice.gemini_client import GeminiClient
from voice.services_async import transcribe_and_parse_async


def _gemini_response_body(parsed: dict) -> dict:
    return {
        "candidates": [
            {
                "content": {"parts": [{"text": json.dumps(parsed)}]},
                "finishReason": "STOP",
            }
        ]
    }


def _mock_client(payload: dict) -> GeminiClient:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_gemini_response_body(payload))

    transport = httpx.MockTransport(handler)
    http = httpx.AsyncClient(transport=transport)
    return GeminiClient(api_key="test", client=http, max_attempts=1, backoff=(0.0,))


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_pipeline_returns_parsed_response_with_one_draft() -> None:
    user = await UserFactory._meta.model.objects.acreate(telegram_id=88, first_name="X")
    payload = {
        "transactions": [
            {
                "type": "expense",
                "amount": "12500.00",
                "currency": "UZS",
                "category_slug": "boshqa",
                "counterparty": "",
                "date": "2026-06-28",
                "note": "qahva",
                "confidence": 0.92,
                "ambiguous_fields": [],
            }
        ],
        "recurring_intent": None,
    }
    client = _mock_client(payload)
    try:
        result = await transcribe_and_parse_async(b"\x00" * 64, user, client=client)
    finally:
        await client.aclose()
    assert len(result.transactions) == 1
    assert str(result.transactions[0].amount) == "12500.00"


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_pipeline_raises_no_transactions_when_response_is_empty() -> None:
    user = await UserFactory._meta.model.objects.acreate(telegram_id=89, first_name="X")
    client = _mock_client({"transactions": [], "recurring_intent": None})
    try:
        with pytest.raises(NoTransactionsParsedError):
            await transcribe_and_parse_async(b"\x00" * 64, user, client=client)
    finally:
        await client.aclose()


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_pipeline_raises_config_error_when_key_missing(settings) -> None:
    """Without GEMINI_API_KEY and no injected client, services_async refuses to call out."""
    user = await UserFactory._meta.model.objects.acreate(telegram_id=90, first_name="X")
    settings.GEMINI_API_KEY = ""
    with pytest.raises(GeminiConfigError):
        await transcribe_and_parse_async(b"\x00" * 64, user)
