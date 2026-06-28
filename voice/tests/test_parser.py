"""Story 2.3 — `voice.parser.normalize` unit tests."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

from categories.models import Category
from transactions.tests.factories import UserFactory
from voice.parser import normalize
from voice.schemas import ParsedResponse, VoiceDraft

# ---------- helpers ----------


def _raw(**overrides):
    base = {
        "type": "expense",
        "amount": "15000",
        "currency": "UZS",
        "category_slug": "food",
        "counterparty": "",
        "date": "2026-06-28",
        "note": "qahva",
        "confidence": 0.9,
        "ambiguous_fields": [],
    }
    base.update(overrides)
    return base


def _envelope(*transactions, recurring=None):
    return {"transactions": list(transactions), "recurring_intent": recurring}


# ---------- amount coercion ----------


@pytest.mark.django_db
def test_amount_as_plain_string_normalizes_to_decimal() -> None:
    user = UserFactory()
    result = normalize(_envelope(_raw(amount="15000.00")), user)
    assert result.transactions[0].amount == Decimal("15000.00")


@pytest.mark.django_db
def test_amount_as_15k_normalizes_to_15000() -> None:
    user = UserFactory()
    result = normalize(_envelope(_raw(amount="15k")), user)
    assert result.transactions[0].amount == Decimal("15000.00")


@pytest.mark.django_db
def test_amount_as_15_ming_normalizes_to_15000() -> None:
    user = UserFactory()
    result = normalize(_envelope(_raw(amount="15 ming")), user)
    assert result.transactions[0].amount == Decimal("15000.00")


@pytest.mark.django_db
def test_amount_as_yarim_mln_normalizes_to_500000() -> None:
    user = UserFactory()
    result = normalize(_envelope(_raw(amount="yarim mln")), user)
    assert result.transactions[0].amount == Decimal("500000.00")


@pytest.mark.django_db
def test_amount_as_number_normalizes_to_decimal() -> None:
    user = UserFactory()
    result = normalize(_envelope(_raw(amount=25000)), user)
    assert result.transactions[0].amount == Decimal("25000.00")


@pytest.mark.django_db
def test_amount_zero_drops_the_draft() -> None:
    user = UserFactory()
    result = normalize(_envelope(_raw(amount="0")), user)
    assert result.transactions == []


@pytest.mark.django_db
def test_amount_negative_drops_the_draft() -> None:
    user = UserFactory()
    result = normalize(_envelope(_raw(amount=-100)), user)
    assert result.transactions == []


# ---------- date coercion ----------


@pytest.mark.django_db
def test_date_bugun_maps_to_today() -> None:
    user = UserFactory()
    today = date(2026, 6, 28)
    result = normalize(_envelope(_raw(date="bugun")), user, today=today)
    assert result.transactions[0].date == today


@pytest.mark.django_db
def test_date_kecha_maps_to_yesterday() -> None:
    user = UserFactory()
    today = date(2026, 6, 28)
    result = normalize(_envelope(_raw(date="kecha")), user, today=today)
    assert result.transactions[0].date == today - timedelta(days=1)


@pytest.mark.django_db
def test_future_date_clamped_to_today_and_flagged_ambiguous() -> None:
    user = UserFactory()
    today = date(2026, 6, 28)
    future = (today + timedelta(days=5)).isoformat()
    result = normalize(_envelope(_raw(date=future)), user, today=today)
    assert result.transactions[0].date == today
    assert "date" in result.transactions[0].ambiguous_fields


@pytest.mark.django_db
def test_invalid_date_defaults_to_today_and_flagged() -> None:
    user = UserFactory()
    today = date(2026, 6, 28)
    result = normalize(_envelope(_raw(date="kechalik")), user, today=today)
    assert result.transactions[0].date == today
    assert "date" in result.transactions[0].ambiguous_fields


# ---------- category match ----------


@pytest.mark.django_db
def test_category_with_known_preset_slug_kept() -> None:
    user = UserFactory()
    Category.objects.create(user=None, type="expense", slug="food", name="Ovqat", emoji="🍔")
    result = normalize(_envelope(_raw(category_slug="food", type="expense")), user)
    assert result.transactions[0].category_slug == "food"
    assert "category_slug" not in result.transactions[0].ambiguous_fields


@pytest.mark.django_db
def test_category_with_unknown_slug_falls_back_to_boshqa_and_flags() -> None:
    user = UserFactory()
    result = normalize(_envelope(_raw(category_slug="nope")), user)
    draft = result.transactions[0]
    assert draft.category_slug == "boshqa"
    assert "category_slug" in draft.ambiguous_fields


@pytest.mark.django_db
def test_category_not_required_for_debt_types() -> None:
    user = UserFactory()
    result = normalize(
        _envelope(_raw(type="debt_lent", category_slug="", counterparty="Akram")),
        user,
    )
    assert result.transactions[0].category_slug == ""
    assert "category_slug" not in result.transactions[0].ambiguous_fields


# ---------- confidence ----------


@pytest.mark.django_db
def test_low_confidence_marks_draft_uncertain() -> None:
    user = UserFactory()
    result = normalize(_envelope(_raw(confidence=0.4)), user)
    draft = result.transactions[0]
    assert draft.is_uncertain
    assert "confidence" in draft.ambiguous_fields or draft.ambiguous_fields


@pytest.mark.django_db
def test_explicit_ambiguous_fields_preserved() -> None:
    user = UserFactory()
    result = normalize(_envelope(_raw(ambiguous_fields=["amount"])), user)
    assert "amount" in result.transactions[0].ambiguous_fields


# ---------- currency ----------


@pytest.mark.django_db
def test_unsupported_currency_defaults_to_uzs_and_flags() -> None:
    user = UserFactory()
    result = normalize(_envelope(_raw(currency="GBP")), user)
    assert result.transactions[0].currency == "UZS"
    assert "currency" in result.transactions[0].ambiguous_fields


# ---------- malformed payloads ----------


@pytest.mark.django_db
def test_unknown_type_dropped() -> None:
    user = UserFactory()
    result = normalize(_envelope(_raw(type="loan")), user)
    assert result.transactions == []


@pytest.mark.django_db
def test_debt_without_counterparty_flagged() -> None:
    user = UserFactory()
    result = normalize(
        _envelope(_raw(type="debt_lent", counterparty="", category_slug="")),
        user,
    )
    assert "counterparty" in result.transactions[0].ambiguous_fields


@pytest.mark.django_db
def test_empty_payload_returns_empty_response() -> None:
    user = UserFactory()
    result = normalize({}, user)
    assert isinstance(result, ParsedResponse)
    assert result.transactions == []


@pytest.mark.django_db
def test_recurring_intent_normalized_when_present() -> None:
    user = UserFactory()
    payload = _envelope(_raw(), recurring=_raw(amount="100000"))
    result = normalize(payload, user)
    assert isinstance(result.recurring_intent, VoiceDraft)
    assert result.recurring_intent.amount == Decimal("100000.00")
