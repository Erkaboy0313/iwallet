"""Stories 9.3, 9.4, 9.7 — management command integration."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from io import StringIO
from unittest.mock import patch

import httpx
import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings
from django.utils import timezone

from debts.models import DebtState
from debts.tests.factories import DebtFactory
from notifications.bot.telegram_client import TelegramBotClient
from notifications.models import NotificationKind, PushQueueItem
from transactions.tests.factories import UserFactory


def _mock_client(handler, *, max_attempts: int = 1) -> TelegramBotClient:
    transport = httpx.MockTransport(handler)
    http = httpx.AsyncClient(transport=transport)
    return TelegramBotClient(
        bot_token="fake-token",
        client=http,
        max_attempts=max_attempts,
        backoff=(0.0, 0.0, 0.0),
    )


# ----------------------------------------------------------------------------
# Story 9.3 — send_pending_pushes command
# ----------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
def test_send_pending_pushes_invokes_process_pending() -> None:
    user = UserFactory(telegram_id=8001)
    PushQueueItem.objects.create(
        user=user,
        kind=NotificationKind.RECURRING_FIRED.value,
        payload_json={
            "schedule_name": "Internet",
            "amount": "150000",
            "currency": "UZS",
            "transaction_id": 42,
        },
    )

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": True})

    mock_client = _mock_client(handler)

    async def fake_process_pending(*, limit: int, **_kwargs):
        # Use the real implementation but with the mocked client.
        from notifications.services import process_pending as real

        try:
            return await real(limit=limit, client=mock_client, sleep=lambda _s: None)
        finally:
            await mock_client.aclose()

    with patch(
        "notifications.management.commands.send_pending_pushes.process_pending",
        new=fake_process_pending,
    ):
        buf = StringIO()
        call_command("send_pending_pushes", stdout=buf)
    assert "sent=1" in buf.getvalue()


@pytest.mark.django_db(transaction=True)
@override_settings(TELEGRAM_BOT_TOKEN="")
def test_send_pending_pushes_handles_missing_token_gracefully() -> None:
    """No token → command logs but exits 0 (cron must not loop-alert)."""
    UserFactory(telegram_id=8002)
    buf = StringIO()
    call_command("send_pending_pushes", stdout=buf)
    # Empty token → process_pending returns zeros without raising.
    assert "sent=0" in buf.getvalue()


@pytest.mark.django_db(transaction=True)
def test_send_pending_pushes_respects_limit_argument() -> None:
    user = UserFactory(telegram_id=8003)
    for i in range(5):
        PushQueueItem.objects.create(
            user=user,
            kind=NotificationKind.RECURRING_FIRED.value,
            payload_json={
                "schedule_name": f"S{i}",
                "amount": "100",
                "currency": "UZS",
                "transaction_id": 9000 + i,
            },
        )
    sent: list[int] = []

    def handler(_request: httpx.Request) -> httpx.Response:
        sent.append(1)
        return httpx.Response(200, json={"ok": True})

    mock_client = _mock_client(handler)

    async def fake_process_pending(*, limit: int, **_kwargs):
        from notifications.services import process_pending as real

        try:
            return await real(limit=limit, client=mock_client, sleep=lambda _s: None)
        finally:
            await mock_client.aclose()

    with patch(
        "notifications.management.commands.send_pending_pushes.process_pending",
        new=fake_process_pending,
    ):
        buf = StringIO()
        call_command("send_pending_pushes", "--limit", "2", stdout=buf)
    assert len(sent) == 2
    assert PushQueueItem.objects.filter(sent_at__isnull=False).count() == 2


# ----------------------------------------------------------------------------
# Story 9.4 — enqueue_debt_due command
# ----------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
def test_enqueue_debt_due_command_creates_rows() -> None:
    today = timezone.localdate()
    user = UserFactory(telegram_id=7001)
    DebtFactory(
        user=user,
        expected_return_date=today,
        counterparty="Karim",
        original_amount=Decimal("100000.00"),
        remaining_amount=Decimal("100000.00"),
    )
    DebtFactory(
        user=user,
        expected_return_date=today,
        counterparty="Akram",
        original_amount=Decimal("200000.00"),
        remaining_amount=Decimal("200000.00"),
    )
    # Tomorrow's debt → ignored.
    DebtFactory(
        user=user,
        expected_return_date=today + timedelta(days=1),
        counterparty="Dilshod",
    )

    buf = StringIO()
    call_command("enqueue_debt_due", stdout=buf)
    assert "created=2" in buf.getvalue()
    assert PushQueueItem.objects.filter(kind=NotificationKind.DEBT_DUE.value).count() == 2


@pytest.mark.django_db(transaction=True)
def test_enqueue_debt_due_command_with_explicit_date() -> None:
    target = date(2026, 8, 15)
    user = UserFactory(telegram_id=7002)
    DebtFactory(user=user, expected_return_date=target)
    DebtFactory(user=user, expected_return_date=date(2026, 8, 16))

    buf = StringIO()
    call_command("enqueue_debt_due", "--date", target.isoformat(), stdout=buf)
    assert "created=1" in buf.getvalue()


@pytest.mark.django_db(transaction=True)
def test_enqueue_debt_due_command_rejects_invalid_date() -> None:
    with pytest.raises(CommandError):
        call_command("enqueue_debt_due", "--date", "not-a-date")


@pytest.mark.django_db(transaction=True)
def test_enqueue_debt_due_command_skips_closed_debts() -> None:
    today = timezone.localdate()
    user = UserFactory(telegram_id=7003)
    DebtFactory(
        user=user,
        expected_return_date=today,
        state=DebtState.CLOSED.value,
        original_amount=Decimal("1.00"),
        remaining_amount=Decimal("0.00"),
    )
    buf = StringIO()
    call_command("enqueue_debt_due", stdout=buf)
    assert "created=0" in buf.getvalue()


# ----------------------------------------------------------------------------
# Story 9.7 — setup_bot command
# ----------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
@override_settings(
    TELEGRAM_BOT_TOKEN="fake-token",
    TELEGRAM_WEBHOOK_SECRET="secret-abc",
    WEBHOOK_BASE_URL="https://iwallet.example",
)
def test_setup_bot_registers_commands_and_webhook() -> None:
    seen_methods: list[tuple[str, dict]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        import json

        method = request.url.path.rsplit("/", 1)[-1]
        body = json.loads(request.content)
        seen_methods.append((method, body))
        return httpx.Response(200, json={"ok": True, "result": True})

    mock_client = _mock_client(handler, max_attempts=1)

    with patch(
        "notifications.management.commands.setup_bot.TelegramBotClient",
        return_value=mock_client,
    ):
        buf = StringIO()
        call_command("setup_bot", stdout=buf)

    methods = [m for m, _ in seen_methods]
    assert "setMyCommands" in methods
    assert "setWebhook" in methods
    # Webhook URL was assembled from WEBHOOK_BASE_URL + secret.
    webhook_body = next(body for m, body in seen_methods if m == "setWebhook")
    assert webhook_body["url"] == "https://iwallet.example/bot/webhook/secret-abc/"
    assert webhook_body["secret_token"] == "secret-abc"
    assert "message" in webhook_body["allowed_updates"]
    assert "callback_query" in webhook_body["allowed_updates"]


@override_settings(TELEGRAM_BOT_TOKEN="")
def test_setup_bot_fails_when_token_missing() -> None:
    with pytest.raises(CommandError):
        call_command("setup_bot")


@override_settings(
    TELEGRAM_BOT_TOKEN="fake-token",
    TELEGRAM_WEBHOOK_SECRET="",
    WEBHOOK_BASE_URL="https://example.com",
)
def test_setup_bot_fails_when_secret_missing_and_webhook_required() -> None:
    with pytest.raises(CommandError):
        call_command("setup_bot")


@pytest.mark.django_db(transaction=True)
@override_settings(
    TELEGRAM_BOT_TOKEN="fake-token",
    TELEGRAM_WEBHOOK_SECRET="secret",
    WEBHOOK_BASE_URL="https://example.com",
)
def test_setup_bot_skip_webhook_flag_only_registers_commands() -> None:
    seen_methods: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_methods.append(request.url.path.rsplit("/", 1)[-1])
        return httpx.Response(200, json={"ok": True, "result": True})

    mock_client = _mock_client(handler, max_attempts=1)

    with patch(
        "notifications.management.commands.setup_bot.TelegramBotClient",
        return_value=mock_client,
    ):
        buf = StringIO()
        call_command("setup_bot", "--skip-webhook", stdout=buf)

    assert "setMyCommands" in seen_methods
    assert "setWebhook" not in seen_methods
