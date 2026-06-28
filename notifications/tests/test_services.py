"""Story 9.2/9.3/9.4/9.5 — service-layer tests with mocked Telegram API."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import httpx
import pytest
from django.utils import timezone

from debts.models import DebtState
from debts.tests.factories import DebtFactory
from notifications.bot.telegram_client import TelegramBotClient
from notifications.models import NotificationKind, PushQueueItem
from notifications.services import (
    cancel_debt_due_callback,
    cancel_recurring_callback,
    confirm_debt_repaid_callback,
    confirm_recurring_callback,
    enqueue_debt_due_reminders,
    handle_callback,
    process_pending,
    send_push,
)
from transactions.models import Transaction
from transactions.tests.factories import TransactionFactory, UserFactory


async def _no_sleep(_seconds: float) -> None:
    return None


def _mock_client(handler, *, max_attempts: int = 3) -> TelegramBotClient:
    transport = httpx.MockTransport(handler)
    http = httpx.AsyncClient(transport=transport)
    return TelegramBotClient(
        bot_token="fake-token",
        client=http,
        max_attempts=max_attempts,
        backoff=(0.0, 0.0, 0.0),
    )


# ----------------------------------------------------------------------------
# send_push (Story 9.2)
# ----------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_send_push_happy_path_flips_sent_at() -> None:
    user = await UserFactory._meta.model.objects.acreate(telegram_id=555, first_name="X")
    item = await PushQueueItem.objects.acreate(
        user=user,
        kind=NotificationKind.RECURRING_FIRED.value,
        payload_json={
            "schedule_name": "Ijara",
            "amount": "2000000",
            "currency": "UZS",
            "transaction_id": 11,
        },
    )

    seen: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        import json

        seen.append(json.loads(request.content))
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 1}})

    client = _mock_client(handler)
    try:
        ok = await send_push(item, client=client, sleep=_no_sleep)
    finally:
        await client.aclose()

    assert ok is True
    refreshed = await PushQueueItem.objects.aget(pk=item.pk)
    assert refreshed.sent_at is not None
    assert seen[0]["chat_id"] == 555
    assert "Ijara" in seen[0]["text"]
    # Inline keyboard had both buttons.
    assert "inline_keyboard" in seen[0]["reply_markup"]


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_send_push_idempotent_skip_when_already_sent() -> None:
    user = await UserFactory._meta.model.objects.acreate(telegram_id=111, first_name="X")
    now = timezone.now()
    item = await PushQueueItem.objects.acreate(
        user=user,
        kind=NotificationKind.RECURRING_FIRED.value,
        payload_json={
            "schedule_name": "X",
            "amount": "1",
            "currency": "UZS",
            "transaction_id": 1,
        },
        sent_at=now,
    )
    called = {"n": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        called["n"] += 1
        return httpx.Response(200, json={"ok": True})

    client = _mock_client(handler)
    try:
        ok = await send_push(item, client=client, sleep=_no_sleep)
    finally:
        await client.aclose()
    assert ok is True
    assert called["n"] == 0


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_send_push_retries_on_transient_error() -> None:
    user = await UserFactory._meta.model.objects.acreate(telegram_id=222, first_name="X")
    item = await PushQueueItem.objects.acreate(
        user=user,
        kind=NotificationKind.RECURRING_FIRED.value,
        payload_json={
            "schedule_name": "Y",
            "amount": "10",
            "currency": "UZS",
            "transaction_id": 2,
        },
    )
    state = {"n": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        state["n"] += 1
        if state["n"] < 3:
            return httpx.Response(503, text="overloaded")
        return httpx.Response(200, json={"ok": True})

    client = _mock_client(handler)
    try:
        ok = await send_push(item, client=client, sleep=_no_sleep)
    finally:
        await client.aclose()
    assert ok is True
    assert state["n"] == 3
    refreshed = await PushQueueItem.objects.aget(pk=item.pk)
    assert refreshed.sent_at is not None


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_send_push_returns_false_on_terminal_telegram_error() -> None:
    user = await UserFactory._meta.model.objects.acreate(telegram_id=333, first_name="X")
    item = await PushQueueItem.objects.acreate(
        user=user,
        kind=NotificationKind.RECURRING_FIRED.value,
        payload_json={
            "schedule_name": "Z",
            "amount": "10",
            "currency": "UZS",
            "transaction_id": 3,
        },
    )

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"ok": False, "description": "chat not found"})

    client = _mock_client(handler, max_attempts=1)
    try:
        ok = await send_push(item, client=client, sleep=_no_sleep)
    finally:
        await client.aclose()
    assert ok is False
    refreshed = await PushQueueItem.objects.aget(pk=item.pk)
    # Failed sends do NOT flip sent_at — next tick will retry.
    assert refreshed.sent_at is None


# ----------------------------------------------------------------------------
# process_pending (Story 9.3)
# ----------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_process_pending_ships_all_unsent_rows() -> None:
    user = await UserFactory._meta.model.objects.acreate(telegram_id=701, first_name="X")
    for i in range(3):
        await PushQueueItem.objects.acreate(
            user=user,
            kind=NotificationKind.RECURRING_FIRED.value,
            payload_json={
                "schedule_name": f"S{i}",
                "amount": "100",
                "currency": "UZS",
                "transaction_id": i + 100,
            },
        )

    state = {"n": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        state["n"] += 1
        return httpx.Response(200, json={"ok": True})

    client = _mock_client(handler)
    try:
        counts = await process_pending(client=client, sleep=_no_sleep)
    finally:
        await client.aclose()
    assert state["n"] == 3
    assert counts["sent"] == 3
    assert counts["failed"] == 0
    assert await PushQueueItem.objects.filter(sent_at__isnull=False).acount() == 3


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_process_pending_skips_already_sent_rows() -> None:
    user = await UserFactory._meta.model.objects.acreate(telegram_id=702, first_name="X")
    await PushQueueItem.objects.acreate(
        user=user,
        kind=NotificationKind.RECURRING_FIRED.value,
        payload_json={
            "schedule_name": "Old",
            "amount": "1",
            "currency": "UZS",
            "transaction_id": 1,
        },
        sent_at=timezone.now(),
    )
    state = {"n": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        state["n"] += 1
        return httpx.Response(200, json={"ok": True})

    client = _mock_client(handler)
    try:
        counts = await process_pending(client=client, sleep=_no_sleep)
    finally:
        await client.aclose()
    # The selector excludes sent rows entirely → no call, no count change.
    assert state["n"] == 0
    assert counts == {"sent": 0, "failed": 0, "skipped": 0}


# ----------------------------------------------------------------------------
# enqueue_debt_due_reminders (Story 9.4)
# ----------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
def test_enqueue_debt_due_reminders_creates_one_per_active_debt() -> None:
    today = timezone.localdate()
    user = UserFactory(telegram_id=999)
    DebtFactory(user=user, expected_return_date=today, state=DebtState.OPEN.value)
    DebtFactory(user=user, expected_return_date=today, state=DebtState.PARTIAL.value)
    # Non-due debt — should be ignored.
    DebtFactory(user=user, expected_return_date=today + timedelta(days=2))
    # Closed debt — should be ignored.
    DebtFactory(user=user, expected_return_date=today, state=DebtState.CLOSED.value)

    created = enqueue_debt_due_reminders(on_date=today)
    assert created == 2
    queued = PushQueueItem.objects.filter(kind=NotificationKind.DEBT_DUE.value)
    assert queued.count() == 2
    payloads = list(queued.values_list("payload_json", flat=True))
    for payload in payloads:
        assert "debt_id" in payload
        assert "counterparty" in payload
        assert "remaining_amount" in payload


@pytest.mark.django_db(transaction=True)
def test_enqueue_debt_due_reminders_idempotent_on_double_run() -> None:
    today = timezone.localdate()
    user = UserFactory(telegram_id=998)
    DebtFactory(user=user, expected_return_date=today)
    DebtFactory(user=user, expected_return_date=today)

    first = enqueue_debt_due_reminders(on_date=today)
    second = enqueue_debt_due_reminders(on_date=today)
    assert first == 2
    assert second == 0  # already queued recently → no new rows
    assert PushQueueItem.objects.count() == 2


@pytest.mark.django_db(transaction=True)
def test_enqueue_debt_due_reminders_returns_zero_when_no_debts_due() -> None:
    today = timezone.localdate()
    UserFactory(telegram_id=1234)
    created = enqueue_debt_due_reminders(on_date=today)
    assert created == 0


# ----------------------------------------------------------------------------
# callback handlers (Story 9.5)
# ----------------------------------------------------------------------------


@pytest.mark.django_db
def test_confirm_recurring_callback_acknowledges_existing_transaction() -> None:
    user = UserFactory(telegram_id=4001)
    tx = TransactionFactory(user=user, date=date.today())
    result = confirm_recurring_callback(transaction_id=tx.id)
    assert "Tasdiqlandi" in result


@pytest.mark.django_db
def test_confirm_recurring_callback_returns_not_found_for_unknown_id() -> None:
    result = confirm_recurring_callback(transaction_id=999999)
    assert "topilmadi" in result.lower()


@pytest.mark.django_db
def test_cancel_recurring_callback_soft_deletes_transaction() -> None:
    user = UserFactory(telegram_id=4002)
    tx = TransactionFactory(user=user, date=date.today())
    result = cancel_recurring_callback(transaction_id=tx.id)
    assert "Bekor qilindi" in result
    refreshed = Transaction.objects.get(pk=tx.pk)
    assert refreshed.is_deleted is True


@pytest.mark.django_db
def test_confirm_debt_repaid_callback_closes_debt() -> None:
    user = UserFactory(telegram_id=4003)
    debt = DebtFactory(
        user=user,
        original_amount=Decimal("50000.00"),
        remaining_amount=Decimal("50000.00"),
    )
    result = confirm_debt_repaid_callback(debt_id=debt.id)
    debt.refresh_from_db()
    assert debt.state == DebtState.CLOSED.value
    assert debt.remaining_amount == Decimal("0.00")
    assert "yopildi" in result.lower()


@pytest.mark.django_db
def test_confirm_debt_repaid_callback_idempotent_on_closed_debt() -> None:
    user = UserFactory(telegram_id=4004)
    debt = DebtFactory(
        user=user,
        original_amount=Decimal("10000.00"),
        remaining_amount=Decimal("0.00"),
        state=DebtState.CLOSED.value,
    )
    result = confirm_debt_repaid_callback(debt_id=debt.id)
    assert "yopilgan" in result.lower()


@pytest.mark.django_db
def test_confirm_debt_repaid_callback_handles_missing_debt() -> None:
    result = confirm_debt_repaid_callback(debt_id=987654)
    assert "topilmadi" in result.lower()


@pytest.mark.django_db
def test_cancel_debt_due_callback_does_not_mutate_state() -> None:
    user = UserFactory(telegram_id=4005)
    debt = DebtFactory(user=user, remaining_amount=Decimal("10000.00"))
    result = cancel_debt_due_callback(_debt_id=debt.id)
    debt.refresh_from_db()
    assert debt.state == DebtState.OPEN.value
    assert debt.remaining_amount == Decimal("10000.00")
    assert "eslataman" in result.lower()


@pytest.mark.django_db
def test_handle_callback_routes_recurring_confirm() -> None:
    user = UserFactory(telegram_id=4006)
    tx = TransactionFactory(user=user, date=date.today())
    result = handle_callback(f"rec:ok:{tx.id}")
    assert "Tasdiqlandi" in result


@pytest.mark.django_db
def test_handle_callback_returns_unknown_for_garbage_data() -> None:
    assert "Eski" in handle_callback("nope:wat:42")
    assert "Eski" in handle_callback("rec:ok:not-an-int")
    assert "Eski" in handle_callback("")


@pytest.mark.django_db
def test_handle_callback_routes_debt_cancel() -> None:
    user = UserFactory(telegram_id=4007)
    debt = DebtFactory(user=user)
    result = handle_callback(f"debt:no:{debt.id}")
    assert "eslataman" in result.lower()
