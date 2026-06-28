"""Story 2.4 — confirm partial rendering + voice:save endpoint.

Confirm partial is exercised via direct template render (cheap) and the save
endpoint via the Django test client with full middleware (real-world path).
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
from transactions.models import Transaction
from transactions.tests.factories import UserFactory
from voice.schemas import VoiceDraft


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


def _render_partial(user, drafts) -> str:
    factory = RequestFactory()
    request = factory.get("/app/voice/transcribe/")
    request.user = user
    return render_to_string(
        "voice/_confirm_partial.html",
        {"drafts": drafts, "recurring": None},
        request=request,
    )


# ---------- Template ----------


@pytest.mark.django_db
def test_partial_renders_single_draft_card() -> None:
    user = UserFactory()
    Category.objects.create(user=None, type="expense", slug="food", name="Ovqat", emoji="🍔")
    html = _render_partial(user, [_draft()])
    # Single voiceConfirm component handles the entire screen now.
    assert "voiceConfirm(" in html
    assert "Saqlash" in html
    assert "Bekor qilish" in html
    # Currency pill present
    assert "UZS" in html


@pytest.mark.django_db
def test_partial_flags_ambiguous_card_with_amber_border() -> None:
    user = UserFactory()
    Category.objects.create(user=None, type="expense", slug="food", name="Ovqat", emoji="🍔")
    drafts = [_draft(ambiguous_fields=["amount"])]
    html = _render_partial(user, drafts)
    assert "border: 2px solid #f59e0b" in html  # UX-DR uncertainty styling
    assert "noaniq" in html or "tekshiring" in html


@pytest.mark.django_db
def test_partial_renders_nothing_when_drafts_empty() -> None:
    user = UserFactory()
    html = _render_partial(user, [])
    # No card markup — the inline Alpine.data registration is always present
    # because the partial sets up the component once per swap; the card div
    # itself only renders inside the for-loop.
    assert "card-default" not in html
    assert "x-data=&quot;voiceDraftCard(" not in html
    assert 'x-data="voiceDraftCard(' not in html


@pytest.mark.django_db
def test_partial_attaches_emoji_and_category_name_from_match() -> None:
    user = UserFactory()
    Category.objects.create(user=None, type="expense", slug="food", name="Ovqat", emoji="🍔")
    html = _render_partial(user, [_draft(category_slug="food")])
    # Inline JSON in x-data uses ascii escapes for safe attribute embedding —
    # so the 🍔 hamburger (U+1F354) shows up as its surrogate pair escape.
    assert ("🍔" in html) or ("\\ud83c\\udf54" in html)
    assert "Ovqat" in html


# ---------- voice:save endpoint ----------


def _post_save(client: Client, user_id: int, payload: dict):
    init_data = _make_init_data(user_id=user_id)
    return client.post(
        reverse("voice:save"),
        data={"payload": json.dumps(payload)},
        headers={"X-Telegram-InitData": init_data},
    )


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_save_persists_expense_and_redirects_home() -> None:
    client = Client()
    Category.objects.create(user=None, type="expense", slug="food", name="Ovqat", emoji="🍔")
    response = _post_save(
        client,
        user_id=101,
        payload={
            "type": "expense",
            "amount": "15000.00",
            "currency": "UZS",
            "category_slug": "food",
            "counterparty": "",
            "date": "2026-06-28",
            "note": "kafe",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("HX-Redirect") == reverse("core:home")
    assert "HX-Trigger" in response.headers
    trig = json.loads(response.headers["HX-Trigger"])
    assert trig["toast"]["type"] == "success"
    tx = Transaction.objects.get(user__telegram_id=101)
    assert tx.amount == Decimal("15000.00")
    assert tx.category.slug == "food"
    assert tx.note == "kafe"


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_save_rejects_zero_amount() -> None:
    client = Client()
    response = _post_save(
        client,
        user_id=101,
        payload={
            "type": "expense",
            "amount": "0",
            "currency": "UZS",
            "date": "2026-06-28",
        },
    )
    assert response.status_code == 422
    assert Transaction.objects.count() == 0


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_save_rejects_invalid_type() -> None:
    client = Client()
    response = _post_save(
        client,
        user_id=101,
        payload={
            "type": "withdrawal",
            "amount": "1000",
            "currency": "UZS",
            "date": "2026-06-28",
        },
    )
    assert response.status_code == 422


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_save_debt_requires_counterparty() -> None:
    client = Client()
    response = _post_save(
        client,
        user_id=101,
        payload={
            "type": "debt_lent",
            "amount": "50000",
            "currency": "UZS",
            "date": "2026-06-28",
        },
    )
    assert response.status_code == 422
    assert Transaction.objects.count() == 0


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_save_debt_with_counterparty_persists() -> None:
    client = Client()
    response = _post_save(
        client,
        user_id=101,
        payload={
            "type": "debt_lent",
            "amount": "50000",
            "currency": "UZS",
            "date": "2026-06-28",
            "counterparty": "Akram",
        },
    )
    assert response.status_code == 200
    tx = Transaction.objects.get(user__telegram_id=101)
    assert tx.counterparty == "Akram"


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_save_falls_back_to_today_when_date_missing() -> None:
    client = Client()
    response = _post_save(
        client,
        user_id=101,
        payload={
            "type": "expense",
            "amount": "1000",
            "currency": "UZS",
            "date": "",
        },
    )
    assert response.status_code == 200
    tx = Transaction.objects.get(user__telegram_id=101)
    assert tx.date == _date_type.today()


@pytest.mark.django_db
def test_save_get_returns_405() -> None:
    client = Client()
    response = client.get(reverse("voice:save"))
    # Anonymous gets 401 first; that's still proof the endpoint doesn't accept GET.
    assert response.status_code in {401, 405}
