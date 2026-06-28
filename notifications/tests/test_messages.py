"""Story 9.2 — message-formatting unit tests (no DB, no network)."""

from __future__ import annotations

from notifications.messages import (
    CB_DEBT_CANCEL,
    CB_DEBT_CONFIRM,
    CB_RECURRING_CANCEL,
    CB_RECURRING_CONFIRM,
    render_debt_due,
    render_for_kind,
    render_recurring_fired,
)
from notifications.models import NotificationKind


def test_render_recurring_fired_emits_uzbek_polite_copy() -> None:
    text, markup = render_recurring_fired(
        {
            "schedule_name": "Ijara",
            "amount": "2000000.00",
            "currency": "UZS",
            "transaction_id": 42,
        }
    )
    assert "Ijara" in text
    assert "UZS" in text
    # Polite form: no rude "qildim"; we use "tasdiqlash"/"bosing".
    assert "tugmani bosing" in text
    # Inline keyboard wires both confirm + cancel with the tx id.
    buttons = markup["inline_keyboard"][0]
    callbacks = {b["callback_data"] for b in buttons}
    assert f"{CB_RECURRING_CONFIRM}:42" in callbacks
    assert f"{CB_RECURRING_CANCEL}:42" in callbacks


def test_render_recurring_amount_with_thousands_separator() -> None:
    text, _ = render_recurring_fired(
        {
            "schedule_name": "Test",
            "amount": "1234567.00",
            "currency": "UZS",
            "transaction_id": 1,
        }
    )
    # Thousands separator is a space ("1 234 567 UZS").
    assert "1 234 567 UZS" in text


def test_render_debt_due_borrowed_direction() -> None:
    text, markup = render_debt_due(
        {
            "debt_id": 7,
            "counterparty": "Karim",
            "remaining_amount": "500000.00",
            "currency": "UZS",
            "direction": "borrowed",
        }
    )
    # I owe Karim → second-person address.
    assert "Karimga" in text
    assert "500 000 UZS" in text
    buttons = markup["inline_keyboard"][0]
    callbacks = {b["callback_data"] for b in buttons}
    assert f"{CB_DEBT_CONFIRM}:7" in callbacks
    assert f"{CB_DEBT_CANCEL}:7" in callbacks


def test_render_debt_due_lent_direction() -> None:
    text, _ = render_debt_due(
        {
            "debt_id": 9,
            "counterparty": "Akram",
            "remaining_amount": "100000.00",
            "currency": "UZS",
            "direction": "lent",
        }
    )
    # Akram owes me → "Akram bugun ... qaytarish kuni".
    assert "Akram" in text
    assert "qaytarish kuni" in text


def test_render_for_kind_dispatches_by_kind() -> None:
    text_rec, _ = render_for_kind(
        NotificationKind.RECURRING_FIRED.value,
        {"schedule_name": "Internet", "amount": "200000", "currency": "UZS", "transaction_id": 3},
    )
    assert "Internet" in text_rec

    text_debt, _ = render_for_kind(
        NotificationKind.DEBT_DUE.value,
        {
            "debt_id": 1,
            "counterparty": "Dilshod",
            "remaining_amount": "50000",
            "currency": "UZS",
            "direction": "borrowed",
        },
    )
    assert "Dilshod" in text_debt


def test_render_for_kind_unknown_returns_neutral_text() -> None:
    """A future notification kind without a renderer must not crash the sender."""
    text, markup = render_for_kind("daily_digest", {"text": "Salom!"})
    assert text == "Salom!"
    assert markup == {}
