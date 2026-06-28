"""Story 6.3 — voice recurring intent detection + co-create flow tests.

Covers the recurring card template render, the dual-action UI gating, and the
save-multi endpoint's recurring co-create path (including the every_n_days
mapping rules and atomic rollback on hint validation failure).
"""

from __future__ import annotations

import json
from datetime import date as _date_type
from decimal import Decimal

import pytest
from django.template.loader import render_to_string
from django.test import Client, RequestFactory, override_settings
from django.urls import reverse

from accounts.tests.test_services import BOT_TOKEN, _make_init_data
from categories.models import Category
from recurring.models import RecurringSchedule
from transactions.models import Transaction
from transactions.tests.factories import UserFactory
from voice.schemas import RecurringHint, VoiceDraft


def _draft(**overrides) -> VoiceDraft:
    base = {
        "type": "expense",
        "amount": Decimal("12500.00"),
        "currency": "UZS",
        "category_slug": "food",
        "counterparty": None,
        "date": _date_type(2026, 6, 28),
        "note": "qahva",
        "confidence": 0.92,
        "ambiguous_fields": [],
    }
    base.update(overrides)
    return VoiceDraft(**base)


def _payload_draft(**overrides) -> dict:
    base = {
        "type": "expense",
        "amount": "12500.00",
        "currency": "UZS",
        "category_slug": "food",
        "counterparty": "",
        "date": "2026-06-28",
        "note": "qahva",
    }
    base.update(overrides)
    return base


def _post_save_multi(client: Client, user_id: int, payload: dict):
    init_data = _make_init_data(user_id=user_id)
    return client.post(
        reverse("voice:save_multi"),
        data={"payload": json.dumps(payload)},
        headers={"X-Telegram-InitData": init_data},
    )


def _render_partial(user, drafts, recurring=None) -> str:
    factory = RequestFactory()
    request = factory.get("/app/voice/transcribe/")
    request.user = user
    return render_to_string(
        "voice/_confirm_partial.html",
        {"drafts": drafts, "recurring": recurring},
        request=request,
    )


# ---------- Template — recurring amber card ----------


@pytest.mark.django_db
def test_partial_shows_recurring_card_when_recurring_intent_present() -> None:
    user = UserFactory()
    Category.objects.create(user=None, type="expense", slug="food", name="Ovqat", emoji="🍔")
    recurring = _draft(note="har oy ijara")
    recurring.recurring_hint = RecurringHint(schedule_kind="monthly", day_of_month=1)
    html = _render_partial(user, [_draft()], recurring=recurring)
    assert "Bu xarajat takrorlanadimi?" in html
    assert "har oy 1-sanasida" in html


@pytest.mark.django_db
def test_partial_recurring_card_falls_back_to_deep_link_when_no_hint() -> None:
    user = UserFactory()
    Category.objects.create(user=None, type="expense", slug="food", name="Ovqat", emoji="🍔")
    recurring = _draft(note="har oy ijara")
    # recurring_hint is None — UI shows manual sozlash button instead.
    html = _render_partial(user, [_draft()], recurring=recurring)
    assert "Bu xarajat takrorlanadimi?" in html
    assert "Ha — qo'lda sozlash" in html
    assert reverse("recurring:create") in html


@pytest.mark.django_db
def test_partial_recurring_card_renders_weekly_hint_label() -> None:
    user = UserFactory()
    Category.objects.create(user=None, type="expense", slug="food", name="Ovqat", emoji="🍔")
    recurring = _draft(note="har dushanba")
    recurring.recurring_hint = RecurringHint(schedule_kind="weekly", day_of_week=0)
    html = _render_partial(user, [_draft()], recurring=recurring)
    assert "har dushanba" in html


@pytest.mark.django_db
def test_partial_no_recurring_card_when_intent_absent() -> None:
    user = UserFactory()
    Category.objects.create(user=None, type="expense", slug="food", name="Ovqat", emoji="🍔")
    html = _render_partial(user, [_draft()], recurring=None)
    assert "Bu xarajat takrorlanadimi?" not in html


# ---------- Endpoint — recurring co-create ----------


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_save_multi_with_recurring_creates_schedule_and_transaction() -> None:
    client = Client()
    Category.objects.create(user=None, type="expense", slug="rent", name="Ijara", emoji="🏠")
    payload = {
        "drafts": [
            _payload_draft(amount="2000000", category_slug="rent", note="har oy ijara"),
        ],
        "recurring": {
            **_payload_draft(amount="2000000", category_slug="rent", note="har oy ijara"),
            "recurring_hint": {"schedule_kind": "monthly", "day_of_month": 1},
        },
    }
    response = _post_save_multi(client, 510, payload)
    assert response.status_code == 200
    assert Transaction.objects.filter(user__telegram_id=510).count() == 1
    schedule = RecurringSchedule.objects.get(user__telegram_id=510)
    assert schedule.amount == Decimal("2000000.00")
    assert schedule.schedule_kind == "monthly"
    assert schedule.day_of_month == 1
    assert schedule.category is not None
    assert schedule.category.slug == "rent"
    trig = json.loads(response.headers["HX-Trigger"])
    assert "takror sozlandi" in trig["toast"]["message"]


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_save_multi_with_recurring_weekly_hint_persists() -> None:
    client = Client()
    Category.objects.create(user=None, type="expense", slug="food", name="Ovqat", emoji="🍔")
    payload = {
        "drafts": [_payload_draft(category_slug="food")],
        "recurring": {
            **_payload_draft(category_slug="food"),
            "recurring_hint": {"schedule_kind": "weekly", "day_of_week": 0},
        },
    }
    response = _post_save_multi(client, 511, payload)
    assert response.status_code == 200
    schedule = RecurringSchedule.objects.get(user__telegram_id=511)
    assert schedule.schedule_kind == "weekly"
    assert schedule.day_of_week == 0


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_save_multi_with_recurring_invalid_hint_rolls_back_entire_batch() -> None:
    client = Client()
    Category.objects.create(user=None, type="expense", slug="food", name="Ovqat", emoji="🍔")
    payload = {
        "drafts": [_payload_draft(category_slug="food")],
        "recurring": {
            **_payload_draft(category_slug="food"),
            "recurring_hint": {"schedule_kind": "lunar"},
        },
    }
    response = _post_save_multi(client, 512, payload)
    assert response.status_code == 422
    assert Transaction.objects.count() == 0
    assert RecurringSchedule.objects.count() == 0


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_save_multi_with_recurring_every_n_days_rejects_unless_seven() -> None:
    """Epic 7's RecurringSchedule only supports monthly/weekly — every_3_days bounces."""
    client = Client()
    Category.objects.create(user=None, type="expense", slug="food", name="Ovqat", emoji="🍔")
    payload = {
        "drafts": [_payload_draft(category_slug="food")],
        "recurring": {
            **_payload_draft(category_slug="food"),
            "recurring_hint": {"schedule_kind": "every_n_days", "every_n_days": 3},
        },
    }
    response = _post_save_multi(client, 513, payload)
    assert response.status_code == 422
    assert RecurringSchedule.objects.count() == 0


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_save_multi_with_every_seven_days_maps_to_weekly_and_persists() -> None:
    """every_7_days is shorthand for weekly — auto-mapped to today's weekday."""
    client = Client()
    Category.objects.create(user=None, type="expense", slug="food", name="Ovqat", emoji="🍔")
    payload = {
        "drafts": [_payload_draft(category_slug="food")],
        "recurring": {
            **_payload_draft(category_slug="food"),
            "recurring_hint": {"schedule_kind": "every_n_days", "every_n_days": 7},
        },
    }
    response = _post_save_multi(client, 514, payload)
    assert response.status_code == 200
    schedule = RecurringSchedule.objects.get(user__telegram_id=514)
    assert schedule.schedule_kind == "weekly"
    assert schedule.day_of_week is not None


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_save_multi_recurring_default_name_from_note_truncated() -> None:
    """The note becomes the schedule's display name, truncated to 64 chars."""
    client = Client()
    Category.objects.create(user=None, type="expense", slug="food", name="Ovqat", emoji="🍔")
    long_note = "a" * 80
    payload = {
        "drafts": [_payload_draft(category_slug="food", note=long_note)],
        "recurring": {
            **_payload_draft(category_slug="food", note=long_note),
            "recurring_hint": {"schedule_kind": "monthly", "day_of_month": 5},
        },
    }
    response = _post_save_multi(client, 515, payload)
    assert response.status_code == 200
    schedule = RecurringSchedule.objects.get(user__telegram_id=515)
    assert len(schedule.name) == 64


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_save_multi_recurring_default_name_falls_back_when_note_empty() -> None:
    client = Client()
    Category.objects.create(user=None, type="expense", slug="food", name="Ovqat", emoji="🍔")
    payload = {
        "drafts": [_payload_draft(category_slug="food", note="")],
        "recurring": {
            **_payload_draft(category_slug="food", note=""),
            "recurring_hint": {"schedule_kind": "monthly", "day_of_month": 5},
        },
    }
    response = _post_save_multi(client, 516, payload)
    assert response.status_code == 200
    schedule = RecurringSchedule.objects.get(user__telegram_id=516)
    assert schedule.name == "Ovozli takror"


# ---------- Deep-link fallback ----------


@pytest.mark.django_db
def test_recurring_card_deep_link_carries_prefilled_query_params() -> None:
    user = UserFactory()
    Category.objects.create(user=None, type="expense", slug="rent", name="Ijara", emoji="🏠")
    recurring = _draft(
        type="expense",
        amount=Decimal("2000000.00"),
        category_slug="rent",
        note="har oy ijara",
    )
    # recurring_hint left as None → template should render a deep-link with
    # prefilled query params so the user can finish setup on /app/settings/recurring/.
    html = _render_partial(user, [_draft()], recurring=recurring)
    assert "type=expense" in html
    assert "category_slug=rent" in html
    assert "currency=UZS" in html
    # The dotted amount survives the URL encoding (Decimal → str).
    assert "amount=2000000.00" in html
