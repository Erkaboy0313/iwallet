"""Story 5.2 — CBU.uz HTTP client tests with mocked transport."""

from datetime import date
from decimal import Decimal

import httpx
import pytest

from currencies.cbu_client import fetch_cbu_rates
from currencies.exceptions import CbuUnavailableError

SAMPLE_PAYLOAD = [
    {
        "id": 21,
        "Code": "840",
        "Ccy": "USD",
        "CcyNm_RU": "Доллар США",
        "Nominal": "1",
        "Rate": "12345.67",
        "Diff": "-12.34",
        "Date": "25.06.2026",
    },
    {
        "id": 57,
        "Code": "643",
        "Ccy": "RUB",
        "Nominal": "1",
        "Rate": "134.56",
        "Diff": "0.12",
        "Date": "25.06.2026",
    },
    {
        "id": 99,
        "Code": "978",
        "Ccy": "EUR",
        "Nominal": "1",
        "Rate": "13456.78",
        "Date": "25.06.2026",
    },
]


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_happy_path_returns_usd_rub_and_date() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=SAMPLE_PAYLOAD)

    with _client(handler) as client:
        result = fetch_cbu_rates(client=client)

    assert result["USD"] == Decimal("12345.67")
    assert result["RUB"] == Decimal("134.56")
    assert result["date"] == date(2026, 6, 25)
    # Filters: EUR not in supported list.
    assert "EUR" not in result


def test_retries_on_http_error_then_succeeds() -> None:
    calls = {"n": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(503, text="boom")
        return httpx.Response(200, json=SAMPLE_PAYLOAD)

    sleeps: list[float] = []
    with _client(handler) as client:
        result = fetch_cbu_rates(client=client, sleep=sleeps.append)
    assert result["USD"] == Decimal("12345.67")
    assert calls["n"] == 3
    # Two sleeps before the successful third attempt.
    assert len(sleeps) == 2


def test_raises_cbu_unavailable_after_max_attempts() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="boom")

    with _client(handler) as client, pytest.raises(CbuUnavailableError):
        fetch_cbu_rates(client=client, max_attempts=2, sleep=lambda _s: None)


def test_invalid_json_triggers_retry_and_then_fails() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="not json")

    with _client(handler) as client, pytest.raises(CbuUnavailableError):
        fetch_cbu_rates(client=client, max_attempts=2, sleep=lambda _s: None)


def test_payload_without_supported_currencies_raises() -> None:
    payload = [{"Ccy": "EUR", "Rate": "1.0", "Date": "25.06.2026"}]

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    with _client(handler) as client, pytest.raises(CbuUnavailableError):
        fetch_cbu_rates(client=client, max_attempts=1, sleep=lambda _s: None)


def test_malformed_rows_are_skipped_but_good_rows_kept() -> None:
    payload = [
        {"Ccy": "USD", "Rate": "12345.67", "Date": "25.06.2026"},
        {"Ccy": "RUB", "Rate": None, "Date": "25.06.2026"},  # skip — missing Rate
        "not-a-dict",  # skip
        {"Ccy": "RUB", "Rate": "not-a-number", "Date": "25.06.2026"},  # skip
    ]

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    with _client(handler) as client:
        result = fetch_cbu_rates(client=client, sleep=lambda _s: None)

    assert result["USD"] == Decimal("12345.67")
    assert "RUB" not in result
