"""Story 6.4 — end-to-end pipeline regression tests for Epic 6.

Drives the full `GeminiClient` → `parser.normalize` flow through
`httpx.MockTransport` with realistic multi-transaction and recurring-intent
Gemini responses. Also a small prompt-content regression suite so we notice
if a future edit drops the multi-tx / recurring-intent instructions.
"""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal

import httpx
import pytest

from accounts.models import User
from voice.gemini_client import GeminiClient
from voice.prompts import build_voice_parse_prompt
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


# ---------- Pipeline — multi-tx end-to-end ----------


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_pipeline_returns_three_drafts_when_gemini_returns_three() -> None:
    user = await User.objects.acreate(telegram_id=601, first_name="X")
    payload = {
        "transactions": [
            {
                "type": "expense",
                "amount": "15000.00",
                "currency": "UZS",
                "category_slug": "boshqa",
                "counterparty": "",
                "date": "2026-06-28",
                "note": "taxi",
                "confidence": 0.91,
                "ambiguous_fields": [],
            },
            {
                "type": "expense",
                "amount": "30000.00",
                "currency": "UZS",
                "category_slug": "boshqa",
                "counterparty": "",
                "date": "2026-06-28",
                "note": "qahva",
                "confidence": 0.94,
                "ambiguous_fields": [],
            },
            {
                "type": "income",
                "amount": "200000.00",
                "currency": "UZS",
                "category_slug": "boshqa",
                "counterparty": "",
                "date": "2026-06-28",
                "note": "oylik",
                "confidence": 0.97,
                "ambiguous_fields": [],
            },
        ],
        "recurring_intent": None,
    }
    client = _mock_client(payload)
    try:
        result = await transcribe_and_parse_async(b"\x00" * 64, user, client=client)
    finally:
        await client.aclose()
    assert len(result.transactions) == 3
    assert result.transactions[0].amount == Decimal("15000.00")
    assert result.transactions[2].type == "income"
    assert result.recurring_intent is None


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_pipeline_caps_runaway_response_at_max() -> None:
    from voice.parser import MAX_DRAFTS_PER_UTTERANCE

    user = await User.objects.acreate(telegram_id=602, first_name="X")
    overflow = MAX_DRAFTS_PER_UTTERANCE + 3
    payload = {
        "transactions": [
            {
                "type": "expense",
                "amount": str(1000 * (i + 1)),
                "currency": "UZS",
                "category_slug": "boshqa",
                "counterparty": "",
                "date": "2026-06-28",
                "note": f"item{i}",
                "confidence": 0.9,
                "ambiguous_fields": [],
            }
            for i in range(overflow)
        ],
        "recurring_intent": None,
    }
    client = _mock_client(payload)
    try:
        result = await transcribe_and_parse_async(b"\x00" * 64, user, client=client)
    finally:
        await client.aclose()
    assert len(result.transactions) == MAX_DRAFTS_PER_UTTERANCE
    assert result.transactions[0].amount == Decimal("1000.00")
    expected_last = Decimal(str(1000 * MAX_DRAFTS_PER_UTTERANCE)).quantize(Decimal("0.01"))
    assert result.transactions[-1].amount == expected_last


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_pipeline_returns_recurring_intent_with_schedule_hint() -> None:
    user = await User.objects.acreate(telegram_id=603, first_name="X")
    payload = {
        "transactions": [
            {
                "type": "expense",
                "amount": "2000000.00",
                "currency": "UZS",
                "category_slug": "boshqa",
                "counterparty": "",
                "date": "2026-06-28",
                "note": "har oy ijara",
                "confidence": 0.95,
                "ambiguous_fields": [],
            }
        ],
        "recurring_intent": {
            "type": "expense",
            "amount": "2000000.00",
            "currency": "UZS",
            "category_slug": "boshqa",
            "counterparty": "",
            "date": "2026-06-28",
            "note": "har oy ijara",
            "confidence": 0.95,
            "ambiguous_fields": [],
            "schedule_hint": {"kind": "monthly", "day_of_month": 1},
        },
    }
    client = _mock_client(payload)
    try:
        result = await transcribe_and_parse_async(b"\x00" * 64, user, client=client)
    finally:
        await client.aclose()
    assert result.recurring_intent is not None
    assert result.recurring_intent.amount == Decimal("2000000.00")
    hint = result.recurring_intent.recurring_hint
    assert hint is not None
    assert hint.schedule_kind == "monthly"
    assert hint.day_of_month == 1


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_pipeline_mixed_clear_and_ambiguous_drafts() -> None:
    """A 2-draft response with one ambiguous + one clear — both come through."""
    user = await User.objects.acreate(telegram_id=604, first_name="X")
    payload = {
        "transactions": [
            {
                "type": "expense",
                "amount": "15000.00",
                "currency": "UZS",
                "category_slug": "boshqa",
                "counterparty": "",
                "date": "2026-06-28",
                "note": "clear",
                "confidence": 0.95,
                "ambiguous_fields": [],
            },
            {
                "type": "expense",
                "amount": "30000.00",
                "currency": "UZS",
                "category_slug": "boshqa",
                "counterparty": "",
                "date": "2026-06-28",
                "note": "fuzzy",
                "confidence": 0.45,
                "ambiguous_fields": ["amount"],
            },
        ],
        "recurring_intent": None,
    }
    client = _mock_client(payload)
    try:
        result = await transcribe_and_parse_async(b"\x00" * 64, user, client=client)
    finally:
        await client.aclose()
    assert len(result.transactions) == 2
    assert not result.transactions[0].is_uncertain
    assert result.transactions[1].is_uncertain
    assert "amount" in result.transactions[1].ambiguous_fields


# ---------- Prompt regression ----------


def test_prompt_contains_multi_transaction_instruction() -> None:
    prompt = build_voice_parse_prompt(default_currency="UZS", today_iso="2026-06-28")
    assert "between 1 and 10 separate" in prompt
    assert "Cap your response at 10 transactions" in prompt


def test_prompt_contains_recurring_intent_instruction() -> None:
    prompt = build_voice_parse_prompt(default_currency="UZS", today_iso="2026-06-28")
    assert "recurring_intent" in prompt
    assert "schedule_hint" in prompt
    assert "monthly" in prompt
    assert "weekly" in prompt
    assert "every_n_days" in prompt


def test_prompt_includes_uzbek_weekday_mapping() -> None:
    prompt = build_voice_parse_prompt(default_currency="UZS", today_iso="2026-06-28")
    assert "dushanba=0" in prompt
    assert "yakshanba=6" in prompt


def test_prompt_examples_include_three_tx_har_oy_pattern() -> None:
    """The 'Bugun 15k taxi, 30k qahva, 200k oylik' example must stay in the prompt."""
    prompt = build_voice_parse_prompt(default_currency="UZS", today_iso="2026-06-28")
    assert "15k taxi" in prompt
    assert "30k qahva" in prompt
    assert "200k oylik" in prompt


def test_prompt_carries_user_currency_and_today() -> None:
    prompt = build_voice_parse_prompt(default_currency="RUB", today_iso="2027-01-15")
    assert "RUB" in prompt
    assert "2027-01-15" in prompt


# ---------- Default currency selection ----------


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_pipeline_pulls_user_default_currency_for_prompt() -> None:
    """Smoke: when the user's default_currency is non-UZS the prompt picks it up."""
    user = await User.objects.acreate(telegram_id=605, first_name="X", default_currency="USD")
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        captured["prompt"] = body["contents"][0]["parts"][0]["text"]
        return httpx.Response(
            200,
            json=_gemini_response_body(
                {
                    "transactions": [
                        {
                            "type": "expense",
                            "amount": "100.00",
                            "currency": "USD",
                            "category_slug": "boshqa",
                            "counterparty": "",
                            "date": "2026-06-28",
                            "note": "",
                            "confidence": 0.9,
                            "ambiguous_fields": [],
                        }
                    ],
                    "recurring_intent": None,
                }
            ),
        )

    transport = httpx.MockTransport(handler)
    http = httpx.AsyncClient(transport=transport)
    client = GeminiClient(api_key="test", client=http, max_attempts=1, backoff=(0.0,))
    try:
        result = await transcribe_and_parse_async(b"\x00" * 64, user, client=client)
    finally:
        await client.aclose()
    assert "USD" in captured["prompt"]
    assert result.transactions[0].currency == "USD"


def test_prompt_today_iso_is_iso_format() -> None:
    """Defensive: build_voice_parse_prompt accepts a plain ISO date string."""
    today_iso = date(2026, 6, 28).isoformat()
    prompt = build_voice_parse_prompt(default_currency="UZS", today_iso=today_iso)
    assert today_iso in prompt
