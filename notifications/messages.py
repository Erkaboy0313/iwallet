"""Uzbek copy + inline-keyboard composition for outbound bot messages.

Pure functions over `PushQueueItem.payload_json` — no DB, no network. The
sender layer in `notifications/services.py` calls these to build the
(text, reply_markup) tuple, then ships it via the Telegram client.

Polite "siz" form throughout (project-context: voice + copy rule).
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from .models import NotificationKind

# Callback-data wire format: `<kind>:<action>:<id>` (Telegram caps at 64 bytes).
# Keep IDs as ints and tokens short so we stay well under the limit.
CB_RECURRING_CONFIRM = "rec:ok"
CB_RECURRING_CANCEL = "rec:no"
CB_DEBT_CONFIRM = "debt:ok"
CB_DEBT_CANCEL = "debt:no"


def _format_amount(raw: Any, currency: str) -> str:
    """Format Decimal-ish amount with thousand separators and currency."""
    try:
        amount = Decimal(str(raw))
    except (InvalidOperation, TypeError, ValueError):
        return f"{raw} {currency}"
    # Integer if no fractional part, otherwise 2dp. Thousands separator: space.
    quantized = amount.quantize(Decimal("0.01"))
    int_part, _, frac_part = f"{quantized:f}".partition(".")
    pretty_int = f"{int(int_part):,}".replace(",", " ")
    if frac_part and int(frac_part) != 0:
        return f"{pretty_int}.{frac_part} {currency}"
    return f"{pretty_int} {currency}"


def render_recurring_fired(payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Compose the recurring-fired push (text + inline keyboard).

    Payload shape from `recurring.services.dispatch_one`:
        schedule_id, schedule_name, transaction_id, amount, currency, fired_on.
    """
    name = payload.get("schedule_name", "Takrorlanuvchi xarajat")
    amount = _format_amount(payload.get("amount", 0), payload.get("currency", "UZS"))
    tx_id = payload.get("transaction_id")

    text = (
        f"✅ {name} avtomatik yozildi: {amount}.\n"
        "Hammasi joyidami? Tasdiqlash uchun tugmani bosing."
    )
    reply_markup = {
        "inline_keyboard": [
            [
                {"text": "✓ Tasdiqlash", "callback_data": f"{CB_RECURRING_CONFIRM}:{tx_id}"},
                {"text": "✗ Bekor qilish", "callback_data": f"{CB_RECURRING_CANCEL}:{tx_id}"},
            ]
        ]
    }
    return text, reply_markup


def render_debt_due(payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Compose a debt-due push.

    Payload shape from `notifications.services.enqueue_debt_due_reminders`:
        debt_id, counterparty, remaining_amount, currency, direction, due_date.
    """
    counterparty = payload.get("counterparty", "Kimdir")
    amount = _format_amount(
        payload.get("remaining_amount", 0),
        payload.get("currency", "UZS"),
    )
    direction = payload.get("direction", "borrowed")
    debt_id = payload.get("debt_id")

    # "borrowed" → user owes counterparty → user needs to pay back.
    # "lent" → counterparty owes user → user should collect.
    if direction == "lent":
        body = (
            f"\U0001f4c5 {counterparty} bugun {amount} qaytarish kuni.\n"
            "Qaytardimi? Tasdiqlasangiz qarz yopiladi."
        )
    else:
        body = (
            f"\U0001f4c5 {counterparty}ga {amount} bugun qaytarish kuni.\n"
            "Qaytardingizmi? Tasdiqlasangiz qarz yopiladi."
        )

    reply_markup = {
        "inline_keyboard": [
            [
                {"text": "✓ Ha, qaytarildi", "callback_data": f"{CB_DEBT_CONFIRM}:{debt_id}"},
                {"text": "✗ Hali emas", "callback_data": f"{CB_DEBT_CANCEL}:{debt_id}"},
            ]
        ]
    }
    return body, reply_markup


def render_for_kind(kind: str, payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Dispatch table — keep all kind→renderer wiring in one place.

    Unknown kinds fall back to a neutral message so a future kind shipped
    without a renderer doesn't crash the consumer loop.
    """
    if kind == NotificationKind.RECURRING_FIRED.value:
        return render_recurring_fired(payload)
    if kind == NotificationKind.DEBT_DUE.value:
        return render_debt_due(payload)
    # Daily digest + any future kind: lightweight placeholder.
    text = payload.get("text") or "IWALLET'dan eslatma"
    return text, {}


WELCOME_TEXT = (
    "Salom! IWALLET shaxsiy moliyaviy yordamchingiz.\nQuyidagi tugmani bosib ilovani oching."
)

HELP_TEXT = (
    "IWALLET — Telegram orqali shaxsiy budjet:\n"
    "• Ovoz yoki qo'lda tranzaksiya qo'shing\n"
    "• Qarz va takror xarajatlarni boshqaring\n"
    "• Haftalik / oylik hisobot ko'ring\n\n"
    "Ilovani ochish uchun pastdagi tugmadan foydalaning."
)
