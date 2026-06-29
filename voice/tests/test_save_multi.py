"""Story 6.2 — multi-draft batch save endpoint + multi-card confirm template tests.

Covers atomic create-all-or-nothing, per-card skip semantics, the multi-card
stack template, and Uzbek error copy. Story 6.3 (recurring intent) tests live
in `test_recurring_intent.py`.
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

# ---------- helpers ----------


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


def _render_partial(user, drafts) -> str:
    factory = RequestFactory()
    request = factory.get("/app/voice/transcribe/")
    request.user = user
    return render_to_string(
        "voice/_confirm_partial.html",
        {"drafts": drafts, "recurring": None},
        request=request,
    )


# ---------- Template — multi-card stack ----------


@pytest.mark.django_db
def test_partial_renders_two_cards_when_two_drafts() -> None:
    user = UserFactory()
    Category.objects.create(user=None, type="expense", slug="food", name="Ovqat", emoji="🍔")
    html = _render_partial(user, [_draft(), _draft(note="non")])
    # Single voiceConfirm component; x-for iterates `drafts` to render cards.
    assert 'x-for="(d, i) in drafts"' in html
    # Header summary "X ta tranzaksiya" shown when drafts.length > 1.
    assert "ta tranzaksiya" in html
    # Sticky save button label rendered via inline JS expression.
    assert "tranzaksiya saqlash" in html


@pytest.mark.django_db
def test_partial_renders_single_card_without_header_when_one_draft() -> None:
    user = UserFactory()
    Category.objects.create(user=None, type="expense", slug="food", name="Ovqat", emoji="🍔")
    html = _render_partial(user, [_draft()])
    # No multi-tx header for a single draft.
    assert "ta tranzaksiya</h2>" not in html


@pytest.mark.django_db
def test_partial_each_card_has_remove_button() -> None:
    user = UserFactory()
    Category.objects.create(user=None, type="expense", slug="food", name="Ovqat", emoji="🍔")
    html = _render_partial(user, [_draft(), _draft()])
    # x-for renders one button per draft at runtime; the partial declares it
    # once and Alpine duplicates per array entry.
    assert "remove(i)" in html
    # Sprint v0.6 §7.3 — destructive label demoted to an icon-only × button.
    assert (
        'aria-label="Tranzaksiyani o&#x27;chirish"' in html
        or 'aria-label="Tranzaksiyani o\'chirish"' in html
    )


# ---------- Endpoint — atomic batch save ----------


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_save_multi_persists_three_transactions_atomically() -> None:
    client = Client()
    Category.objects.create(user=None, type="expense", slug="food", name="Ovqat", emoji="🍔")
    Category.objects.create(user=None, type="expense", slug="transport", name="Yo'l", emoji="🚕")
    Category.objects.create(user=None, type="income", slug="salary", name="Oylik", emoji="💰")
    payload = {
        "drafts": [
            _payload_draft(amount="15000", category_slug="transport", note="taxi"),
            _payload_draft(amount="30000", category_slug="food", note="qahva"),
            _payload_draft(type="income", amount="200000", category_slug="salary", note="oylik"),
        ]
    }
    response = _post_save_multi(client, 401, payload)
    assert response.status_code == 200
    assert response.headers.get("HX-Redirect") == reverse("core:home")
    trig = json.loads(response.headers["HX-Trigger"])
    assert trig["toast"]["type"] == "success"
    assert "3 ta tranzaksiya" in trig["toast"]["message"]
    assert Transaction.objects.filter(user__telegram_id=401).count() == 3


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_save_multi_rolls_back_entire_batch_on_one_invalid_amount() -> None:
    """One bad amount → zero transactions persisted (atomic per FR25)."""
    client = Client()
    Category.objects.create(user=None, type="expense", slug="food", name="Ovqat", emoji="🍔")
    payload = {
        "drafts": [
            _payload_draft(amount="15000"),
            _payload_draft(amount="0"),
            _payload_draft(amount="30000"),
        ]
    }
    response = _post_save_multi(client, 402, payload)
    assert response.status_code == 422
    assert Transaction.objects.count() == 0


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_save_multi_with_one_draft_uses_singular_toast_copy() -> None:
    client = Client()
    Category.objects.create(user=None, type="expense", slug="food", name="Ovqat", emoji="🍔")
    response = _post_save_multi(client, 403, {"drafts": [_payload_draft()]})
    assert response.status_code == 200
    trig = json.loads(response.headers["HX-Trigger"])
    assert trig["toast"]["message"] == "Tranzaksiya saqlandi"


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_save_multi_empty_draft_list_rejects() -> None:
    client = Client()
    response = _post_save_multi(client, 404, {"drafts": []})
    assert response.status_code == 422
    assert Transaction.objects.count() == 0


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_save_multi_caps_at_max_drafts() -> None:
    from voice.views import MAX_BATCH_DRAFTS

    client = Client()
    Category.objects.create(user=None, type="expense", slug="food", name="Ovqat", emoji="🍔")
    payload = {"drafts": [_payload_draft() for _ in range(MAX_BATCH_DRAFTS + 1)]}
    response = _post_save_multi(client, 405, payload)
    assert response.status_code == 422
    assert Transaction.objects.count() == 0


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_save_multi_mixes_debt_and_expense_in_one_batch() -> None:
    client = Client()
    Category.objects.create(user=None, type="expense", slug="food", name="Ovqat", emoji="🍔")
    payload = {
        "drafts": [
            _payload_draft(
                type="debt_lent", amount="1000000", counterparty="Akram", category_slug=""
            ),
            _payload_draft(amount="50000", category_slug="food", note="oziq-ovqat"),
        ]
    }
    response = _post_save_multi(client, 406, payload)
    assert response.status_code == 200
    txs = list(Transaction.objects.filter(user__telegram_id=406).order_by("amount"))
    assert len(txs) == 2
    assert txs[0].amount == Decimal("50000.00")
    assert txs[1].type == "debt_lent"
    assert txs[1].counterparty == "Akram"


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_save_multi_debt_without_counterparty_rolls_back_batch() -> None:
    client = Client()
    Category.objects.create(user=None, type="expense", slug="food", name="Ovqat", emoji="🍔")
    payload = {
        "drafts": [
            _payload_draft(amount="15000"),
            _payload_draft(type="debt_lent", amount="50000", category_slug=""),
        ]
    }
    response = _post_save_multi(client, 407, payload)
    assert response.status_code == 422
    assert Transaction.objects.count() == 0


@pytest.mark.django_db
def test_save_multi_anonymous_caller_returns_401() -> None:
    client = Client()
    response = client.post(reverse("voice:save_multi"))
    assert response.status_code == 401


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_save_multi_get_returns_405() -> None:
    client = Client()
    init_data = _make_init_data(user_id=408)
    response = client.get(
        reverse("voice:save_multi"),
        headers={"X-Telegram-InitData": init_data},
    )
    assert response.status_code == 405
