"""Write-side business logic for notifications (Epic 9).

Three concerns live here:

1. `send_push(item)` — formats, ships, marks-as-sent. Idempotent (skips when
   `sent_at` is already populated). Async because the Telegram client uses
   httpx.AsyncClient.
2. `process_pending(...)` — the management-command tick walking the queue.
3. `enqueue_debt_due_reminders(...)` — Story 9.4 enqueuer for debts hitting
   their `expected_return_date` today.
4. Callback handlers for inline-keyboard taps — Story 9.5.

Per project-context: views never write to the DB directly; they call these.
The webhook view in `notifications/bot/webhook.py` is the lone caller for the
callback handlers.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date
from decimal import Decimal
from typing import Any

from asgiref.sync import sync_to_async
from django.conf import settings
from django.db import transaction as db_transaction
from django.utils import timezone

from debts.exceptions import (
    DebtAlreadyClosedError,
    RepaymentExceedsRemainingError,
)
from debts.models import Debt
from debts.services import apply_repayment

from .bot.telegram_client import TelegramAPIError, TelegramBotClient
from .messages import (
    CB_DEBT_CANCEL,
    CB_DEBT_CONFIRM,
    CB_RECURRING_CANCEL,
    CB_RECURRING_CONFIRM,
    render_for_kind,
)
from .models import NotificationKind, PushQueueItem
from .selectors import already_queued_debt_due_ids, debts_due_on, pending_pushes

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------------
# Story 9.2 — send a single queued push
# ----------------------------------------------------------------------------


async def send_push(
    item: PushQueueItem,
    *,
    client: TelegramBotClient | None = None,
    sleep: Any = None,
) -> bool:
    """Deliver `item` via Telegram and flip `sent_at` atomically.

    Returns True if a send was attempted (or already done — idempotent skip).
    Returns False if the send was attempted but Telegram terminally rejected
    it — the row stays unsent and the caller can decide whether to back off.

    `client` is injectable so the management command (and tests) can share a
    single `httpx.AsyncClient`/transport across many items.

    Idempotency: a row whose `sent_at` is set short-circuits before any
    network call. Caller can safely re-run.
    """
    if item.sent_at is not None:
        logger.debug("push %s already sent at %s — skip", item.id, item.sent_at)
        return True

    text, reply_markup = render_for_kind(item.kind, item.payload_json or {})

    owns_client = client is None
    if client is None:
        bot_token = getattr(settings, "TELEGRAM_BOT_TOKEN", "")
        if not bot_token:
            logger.error("push %s: TELEGRAM_BOT_TOKEN not configured", item.id)
            return False
        client = TelegramBotClient(bot_token=bot_token)

    try:
        try:
            await client.send_message(
                chat_id=item.user_id,
                text=text,
                reply_markup=reply_markup or None,
                sleep=sleep,
            )
        except TelegramAPIError as exc:
            logger.warning("push %s send failed: %s", item.id, exc)
            return False
    finally:
        if owns_client:
            await client.aclose()

    # Stamp sent_at in its own atomic block — even if the bot crashes between
    # send + save, the next tick will re-send (Telegram has no message-level
    # idempotency; we accept the rare double-send over silent drops).
    await sync_to_async(_mark_sent, thread_sensitive=True)(item.id)
    logger.info("push %s sent → user=%s kind=%s", item.id, item.user_id, item.kind)
    return True


@db_transaction.atomic
def _mark_sent(item_id: int) -> None:
    PushQueueItem.objects.filter(pk=item_id, sent_at__isnull=True).update(sent_at=timezone.now())


# ----------------------------------------------------------------------------
# Story 9.3 — process the queue (one tick of the management command)
# ----------------------------------------------------------------------------


async def process_pending(
    *,
    limit: int = 100,
    client: TelegramBotClient | None = None,
    sleep: Any = None,
) -> dict[str, int]:
    """Walk up to `limit` pending pushes, delivering each via Telegram.

    Returns a counts dict for command logging:
        {"sent": int, "failed": int, "skipped": int}.

    Uses a shared `TelegramBotClient` so we don't reopen the HTTPS connection
    per push (matters once the queue grows past a handful of items).
    """
    owns_client = client is None
    if client is None:
        bot_token = getattr(settings, "TELEGRAM_BOT_TOKEN", "")
        if not bot_token:
            logger.error("process_pending: TELEGRAM_BOT_TOKEN not configured")
            return {"sent": 0, "failed": 0, "skipped": 0}
        client = TelegramBotClient(bot_token=bot_token)

    counts = {"sent": 0, "failed": 0, "skipped": 0}
    try:
        items = await sync_to_async(_fetch_pending, thread_sensitive=True)(limit)
        for item in items:
            if item.sent_at is not None:
                counts["skipped"] += 1
                continue
            ok = await send_push(item, client=client, sleep=sleep)
            if ok and item.sent_at is None:
                # send_push refreshed via UPDATE — refetch sent_at locally so
                # counts are accurate (we don't refresh_from_db here; we just
                # trust the boolean signal).
                counts["sent"] += 1
            elif ok:
                counts["skipped"] += 1
            else:
                counts["failed"] += 1
    finally:
        if owns_client:
            await client.aclose()

    return counts


def _fetch_pending(limit: int) -> list[PushQueueItem]:
    return list(pending_pushes(limit=limit))


# ----------------------------------------------------------------------------
# Story 9.4 — enqueue debt-due reminders
# ----------------------------------------------------------------------------


@db_transaction.atomic
def enqueue_debt_due_reminders(*, on_date: date | None = None) -> int:
    """Create `PushQueueItem(kind='debt_due')` rows for every active debt
    whose `expected_return_date` matches `on_date` (defaults to today).

    Skips debts that already have a debt_due push in the last 24h to keep
    the management command safe to run multiple times per day.

    Returns the number of rows actually created.
    """
    if on_date is None:
        on_date = timezone.localdate()

    due_debts = list(debts_due_on(on_date))
    if not due_debts:
        return 0

    already = already_queued_debt_due_ids(debt_ids=[d.id for d in due_debts], since=1)

    created = 0
    for debt in due_debts:
        if debt.id in already:
            logger.debug("debt %s already has recent push, skipping", debt.id)
            continue
        PushQueueItem.objects.create(
            user=debt.user,
            kind=NotificationKind.DEBT_DUE.value,
            payload_json={
                "debt_id": debt.id,
                "counterparty": debt.counterparty,
                "remaining_amount": str(debt.remaining_amount),
                "currency": debt.currency,
                "direction": debt.direction,
                "due_date": on_date.isoformat(),
            },
        )
        created += 1

    logger.info("enqueue_debt_due_reminders: created=%d due=%d", created, len(due_debts))
    return created


# ----------------------------------------------------------------------------
# Story 9.5 — callback handlers (recurring / debt 1-tap actions)
# ----------------------------------------------------------------------------


def parse_callback_data(data: str) -> tuple[str, str, str | None]:
    """Split `<prefix>:<action>:<id>` callback_data.

    Returns (prefix, action, id_str). `prefix` + `action` are bytes from the
    `CB_*` constants in `notifications.messages`. `id_str` may be None if the
    payload is malformed; the handlers treat that as a no-op.
    """
    parts = (data or "").split(":", 2)
    if len(parts) < 2:
        return ("", "", None)
    if len(parts) == 2:
        return (parts[0], parts[1], None)
    return (parts[0], parts[1], parts[2])


@db_transaction.atomic
def confirm_recurring_callback(*, transaction_id: int) -> str:
    """User tapped "Tasdiqlash" on a recurring-fired push.

    The Transaction was already created by `recurring.services.dispatch_one`
    when the schedule fired, so confirmation is a pure acknowledgement — no
    new DB write. We return a short message to edit the original push with.
    """
    from transactions.models import Transaction

    exists = Transaction.objects.filter(pk=transaction_id, is_deleted=False).exists()
    if not exists:
        return "Tranzaksiya topilmadi yoki o'chirilgan."
    return "✅ Tasdiqlandi. Tranzaksiya saqlandi."


@db_transaction.atomic
def cancel_recurring_callback(*, transaction_id: int) -> str:
    """User tapped "Bekor qilish" — soft-delete the auto-created Transaction.

    Uses `transactions.services.soft_delete_transaction` so the FR8 restore
    window applies (user can undo from History within 7 days).
    """
    from transactions.models import Transaction
    from transactions.services import soft_delete_transaction

    tx = Transaction.objects.filter(pk=transaction_id, is_deleted=False).first()
    if tx is None:
        return "Tranzaksiya topilmadi yoki allaqachon o'chirilgan."
    soft_delete_transaction(tx=tx)
    return "✗ Bekor qilindi. Tranzaksiya o'chirildi (7 kun ichida tiklash mumkin)."


@db_transaction.atomic
def confirm_debt_repaid_callback(*, debt_id: int) -> str:
    """User tapped "Ha, qaytarildi" on a debt-due push.

    Applies a full repayment of the debt's remaining_amount via
    `debts.services.apply_repayment`. Idempotent — if the debt is already
    closed (e.g. user closed it in WebApp before tapping), we just confirm.
    """
    debt = Debt.objects.filter(pk=debt_id).first()
    if debt is None:
        return "Qarz topilmadi."
    if debt.is_terminal:
        return "✅ Qarz allaqachon yopilgan."

    remaining = debt.remaining_amount
    try:
        apply_repayment(
            debt=debt,
            amount=remaining,
            currency=debt.currency,
            note="Bot orqali tasdiqlandi",
        )
    except (DebtAlreadyClosedError, RepaymentExceedsRemainingError) as exc:
        logger.info("confirm_debt_repaid_callback no-op: %s", exc)
        return "✅ Qarz allaqachon yopilgan."

    return f"✅ Qarz yopildi: {_fmt_amount(remaining, debt.currency)}."


@db_transaction.atomic
def cancel_debt_due_callback(*, _debt_id: int) -> str:
    """User tapped "Hali emas" — we don't mutate the debt, just acknowledge.

    The debt-due reminder will not fire again today (dedupe window) and the
    next reminder fires when the user reschedules.
    """
    return "Tushunarli, eslataman."


def _fmt_amount(amount: Decimal, currency: str) -> str:
    quantized = amount.quantize(Decimal("0.01"))
    int_part, _, frac_part = f"{quantized:f}".partition(".")
    pretty_int = f"{int(int_part):,}".replace(",", " ")
    if frac_part and int(frac_part) != 0:
        return f"{pretty_int}.{frac_part} {currency}"
    return f"{pretty_int} {currency}"


# Routing table consumed by the webhook view — keeps all callback wiring here.
CALLBACK_ROUTES = {
    CB_RECURRING_CONFIRM: ("recurring", "confirm"),
    CB_RECURRING_CANCEL: ("recurring", "cancel"),
    CB_DEBT_CONFIRM: ("debt", "confirm"),
    CB_DEBT_CANCEL: ("debt", "cancel"),
}


def handle_callback(data: str) -> str:
    """Synchronous dispatcher → returns the edited-message text.

    The webhook view runs this inside `sync_to_async` because all branches
    touch the ORM. Returning a plain string keeps the view glue minimal.
    """
    prefix, action, id_str = parse_callback_data(data)
    key = f"{prefix}:{action}"
    if key not in CALLBACK_ROUTES:
        return "Eski yoki noma'lum amal."

    try:
        entity_id = int(id_str) if id_str is not None else None
    except (TypeError, ValueError):
        return "Eski yoki noma'lum amal."
    if entity_id is None:
        return "Eski yoki noma'lum amal."

    if key == CB_RECURRING_CONFIRM:
        return confirm_recurring_callback(transaction_id=entity_id)
    if key == CB_RECURRING_CANCEL:
        return cancel_recurring_callback(transaction_id=entity_id)
    if key == CB_DEBT_CONFIRM:
        return confirm_debt_repaid_callback(debt_id=entity_id)
    if key == CB_DEBT_CANCEL:
        return cancel_debt_due_callback(_debt_id=entity_id)
    return "Eski yoki noma'lum amal."


__all__ = [
    "send_push",
    "process_pending",
    "enqueue_debt_due_reminders",
    "handle_callback",
    "parse_callback_data",
    "confirm_recurring_callback",
    "cancel_recurring_callback",
    "confirm_debt_repaid_callback",
    "cancel_debt_due_callback",
]


# Stop ruff from complaining about an unused-asyncio import in some environments
# (the symbol is used by the async path via the management command's runner).
_ = asyncio
