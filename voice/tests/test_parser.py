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


# ---------- Story 6.1 — multi-transaction parsing ----------


@pytest.mark.django_db
def test_three_transactions_in_one_phrase_all_normalize() -> None:
    """'Bugun 15k taxi, 30k qahva ichdim, 200k oylik tushdi' → 3 drafts."""
    user = UserFactory()
    Category.objects.create(user=None, type="expense", slug="transport", name="Yo'l", emoji="🚕")
    Category.objects.create(user=None, type="expense", slug="food", name="Ovqat", emoji="🍔")
    Category.objects.create(user=None, type="income", slug="salary", name="Oylik", emoji="💰")
    payload = _envelope(
        _raw(amount="15000", category_slug="transport", note="taxi"),
        _raw(amount="30000", category_slug="food", note="qahva"),
        _raw(type="income", amount="200000", category_slug="salary", note="oylik"),
    )
    result = normalize(payload, user)
    assert len(result.transactions) == 3
    assert result.transactions[0].amount == Decimal("15000.00")
    assert result.transactions[1].amount == Decimal("30000.00")
    assert result.transactions[2].type == "income"
    assert result.transactions[2].amount == Decimal("200000.00")


@pytest.mark.django_db
def test_mixed_debt_and_expense_in_one_phrase_normalizes_both() -> None:
    """'Akramga 1 mln qarz berdim va do'kondan 50k oziq-ovqat' → 2 drafts."""
    user = UserFactory()
    Category.objects.create(user=None, type="expense", slug="food", name="Ovqat", emoji="🍔")
    payload = _envelope(
        _raw(type="debt_lent", amount="1000000", counterparty="Akram", category_slug=""),
        _raw(amount="50000", category_slug="food", note="oziq-ovqat"),
    )
    result = normalize(payload, user)
    assert len(result.transactions) == 2
    assert result.transactions[0].type == "debt_lent"
    assert result.transactions[0].counterparty == "Akram"
    assert result.transactions[1].type == "expense"
    assert result.transactions[1].amount == Decimal("50000.00")


@pytest.mark.django_db
def test_single_transaction_still_returns_one_element_list() -> None:
    """'15 ming taxida yurdim' → 1 draft, list of length 1."""
    user = UserFactory()
    payload = _envelope(_raw(amount="15 ming", category_slug="transport"))
    result = normalize(payload, user)
    assert len(result.transactions) == 1
    assert result.transactions[0].amount == Decimal("15000.00")


@pytest.mark.django_db
def test_mixed_clear_and_ambiguous_drafts_preserve_per_card_flags() -> None:
    """One ambiguous, one clear — both remain in the batch with independent flags."""
    user = UserFactory()
    Category.objects.create(user=None, type="expense", slug="food", name="Ovqat", emoji="🍔")
    payload = _envelope(
        _raw(amount="15000", confidence=0.95),
        _raw(amount="30000", confidence=0.4),
    )
    result = normalize(payload, user)
    assert len(result.transactions) == 2
    assert not result.transactions[0].is_uncertain
    assert result.transactions[1].is_uncertain


@pytest.mark.django_db
def test_mixed_amount_units_in_one_phrase_all_normalize() -> None:
    """k + ming + mln in the same batch — each draft uses its own unit."""
    user = UserFactory()
    payload = _envelope(
        _raw(amount="15k"),
        _raw(amount="30 ming"),
        _raw(amount="1 mln"),
    )
    result = normalize(payload, user)
    assert [d.amount for d in result.transactions] == [
        Decimal("15000.00"),
        Decimal("30000.00"),
        Decimal("1000000.00"),
    ]


@pytest.mark.django_db
def test_more_than_max_drafts_capped() -> None:
    """Runaway model output is capped at MAX_DRAFTS_PER_UTTERANCE."""
    from voice.parser import MAX_DRAFTS_PER_UTTERANCE

    user = UserFactory()
    payload = _envelope(
        *[_raw(amount=str(1000 * (i + 1))) for i in range(MAX_DRAFTS_PER_UTTERANCE + 2)]
    )
    result = normalize(payload, user)
    assert len(result.transactions) == MAX_DRAFTS_PER_UTTERANCE
    assert result.transactions[0].amount == Decimal("1000.00")
    expected_last = Decimal(str(1000 * MAX_DRAFTS_PER_UTTERANCE)) + Decimal("0")
    assert result.transactions[-1].amount == expected_last.quantize(Decimal("0.01"))


@pytest.mark.django_db
def test_one_malformed_draft_dropped_others_kept() -> None:
    """A bad row in the middle of a batch doesn't poison the others."""
    user = UserFactory()
    payload = _envelope(
        _raw(amount="15000"),
        _raw(type="not_a_real_type"),  # dropped
        _raw(amount="30000"),
    )
    result = normalize(payload, user)
    assert len(result.transactions) == 2
    assert result.transactions[0].amount == Decimal("15000.00")
    assert result.transactions[1].amount == Decimal("30000.00")


# ---------- Story 6.3 — recurring schedule_hint normalization ----------


@pytest.mark.django_db
def test_recurring_intent_with_monthly_schedule_hint_string_shorthand() -> None:
    user = UserFactory()
    rec = _raw(note="har oy ijara")
    rec["schedule_hint"] = "monthly:day=1"
    payload = _envelope(_raw(), recurring=rec)
    result = normalize(payload, user)
    hint = result.recurring_intent.recurring_hint
    assert hint is not None
    assert hint.schedule_kind == "monthly"
    assert hint.day_of_month == 1


@pytest.mark.django_db
def test_recurring_intent_with_weekly_schedule_hint_dict_form() -> None:
    user = UserFactory()
    rec = _raw(note="har dushanba")
    rec["schedule_hint"] = {"kind": "weekly", "day_of_week": 0}
    payload = _envelope(_raw(), recurring=rec)
    result = normalize(payload, user)
    hint = result.recurring_intent.recurring_hint
    assert hint is not None
    assert hint.schedule_kind == "weekly"
    assert hint.day_of_week == 0
    assert hint.day_of_month is None


@pytest.mark.django_db
def test_recurring_intent_with_every_n_days_schedule_hint() -> None:
    user = UserFactory()
    rec = _raw(note="har 3 kunda")
    rec["schedule_hint"] = {"kind": "every_n_days", "every_n_days": 3}
    payload = _envelope(_raw(), recurring=rec)
    result = normalize(payload, user)
    hint = result.recurring_intent.recurring_hint
    assert hint is not None
    assert hint.schedule_kind == "every_n_days"
    assert hint.every_n_days == 3


@pytest.mark.django_db
def test_recurring_intent_without_schedule_hint_still_normalizes() -> None:
    user = UserFactory()
    payload = _envelope(_raw(), recurring=_raw(amount="100000"))
    result = normalize(payload, user)
    assert result.recurring_intent is not None
    assert result.recurring_intent.recurring_hint is None


@pytest.mark.django_db
def test_recurring_intent_with_invalid_schedule_hint_drops_hint_keeps_draft() -> None:
    """An unparseable schedule_hint leaves the draft intact but with no hint."""
    user = UserFactory()
    rec = _raw()
    rec["schedule_hint"] = {"kind": "lunar"}  # not a known cadence
    payload = _envelope(_raw(), recurring=rec)
    result = normalize(payload, user)
    assert result.recurring_intent is not None
    assert result.recurring_intent.recurring_hint is None


@pytest.mark.django_db
def test_recurring_intent_with_monthly_but_no_day_drops_hint() -> None:
    user = UserFactory()
    rec = _raw()
    rec["schedule_hint"] = {"kind": "monthly"}  # invalid — needs day_of_month
    payload = _envelope(_raw(), recurring=rec)
    result = normalize(payload, user)
    assert result.recurring_intent is not None
    assert result.recurring_intent.recurring_hint is None


@pytest.mark.django_db
def test_recurring_intent_with_weekly_day_out_of_range_drops_hint() -> None:
    user = UserFactory()
    rec = _raw()
    rec["schedule_hint"] = {"kind": "weekly", "day_of_week": 9}
    payload = _envelope(_raw(), recurring=rec)
    result = normalize(payload, user)
    assert result.recurring_intent.recurring_hint is None
