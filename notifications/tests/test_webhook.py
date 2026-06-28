"""Stories 9.1, 9.5, 9.6 — webhook ASGI app + handler routing."""

from __future__ import annotations

import json
from unittest.mock import patch

import httpx
import pytest
from django.test import override_settings

from debts.models import DebtState
from debts.tests.factories import DebtFactory
from notifications.bot import handlers as handlers_module
from notifications.bot.telegram_client import TelegramBotClient
from notifications.bot.webhook import _secret_from_path, app, handle_webhook
from transactions.tests.factories import TransactionFactory, UserFactory

# ----------------------------------------------------------------------------
# helpers — minimal ASGI receive/send mocks
# ----------------------------------------------------------------------------


class _AsgiBuffer:
    """Captures (status, headers, body) emitted by an ASGI app."""

    def __init__(self) -> None:
        self.status: int | None = None
        self.headers: list[tuple[bytes, bytes]] = []
        self.body = b""

    async def __call__(self, message: dict) -> None:
        if message["type"] == "http.response.start":
            self.status = message["status"]
            self.headers = message.get("headers", [])
        elif message["type"] == "http.response.body":
            self.body += message.get("body", b"")


def _make_receive(body: bytes):
    sent = {"done": False}

    async def receive() -> dict:
        if sent["done"]:
            return {"type": "http.disconnect"}
        sent["done"] = True
        return {"type": "http.request", "body": body, "more_body": False}

    return receive


def _scope(
    method: str,
    path: str,
    *,
    headers: list[tuple[bytes, bytes]] | None = None,
) -> dict:
    return {
        "type": "http",
        "method": method,
        "path": path,
        "headers": headers or [],
        "query_string": b"",
    }


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
# Story 9.1 / 9.6 — webhook secret validation + payload parsing
# ----------------------------------------------------------------------------


def test_secret_from_path_strips_prefix_and_trailing_slash() -> None:
    assert _secret_from_path("/bot/webhook/abc/") == "abc"
    assert _secret_from_path("/bot/webhook/abc") == "abc"
    assert _secret_from_path("/somewhere/else/") is None


@pytest.mark.asyncio
@override_settings(TELEGRAM_WEBHOOK_SECRET="super-secret")
async def test_webhook_rejects_wrong_secret_in_path() -> None:
    buf = _AsgiBuffer()
    await handle_webhook(
        _scope("POST", "/bot/webhook/wrong/"),
        _make_receive(b'{"update_id":1}'),
        buf,
    )
    assert buf.status == 403
    body = json.loads(buf.body)
    assert body["error"] == "invalid_secret"


@pytest.mark.asyncio
@override_settings(TELEGRAM_WEBHOOK_SECRET="super-secret")
async def test_webhook_accepts_header_secret_token() -> None:
    """Telegram can deliver secret via X-Telegram-Bot-Api-Secret-Token header."""
    buf = _AsgiBuffer()
    headers = [(b"x-telegram-bot-api-secret-token", b"super-secret")]
    # Path secret intentionally wrong — header alone is sufficient.
    await handle_webhook(
        _scope("POST", "/bot/webhook/wrong/", headers=headers),
        _make_receive(b'{"update_id":1}'),
        buf,
    )
    assert buf.status == 200


@pytest.mark.asyncio
@override_settings(TELEGRAM_WEBHOOK_SECRET="")
async def test_webhook_refuses_when_secret_not_configured() -> None:
    buf = _AsgiBuffer()
    await handle_webhook(
        _scope("POST", "/bot/webhook/anything/"),
        _make_receive(b"{}"),
        buf,
    )
    assert buf.status == 503


@pytest.mark.asyncio
@override_settings(TELEGRAM_WEBHOOK_SECRET="ok")
async def test_webhook_rejects_non_post() -> None:
    buf = _AsgiBuffer()
    await handle_webhook(
        _scope("GET", "/bot/webhook/ok/"),
        _make_receive(b""),
        buf,
    )
    assert buf.status == 405


@pytest.mark.asyncio
@override_settings(TELEGRAM_WEBHOOK_SECRET="ok")
async def test_webhook_rejects_empty_body() -> None:
    buf = _AsgiBuffer()
    await handle_webhook(
        _scope("POST", "/bot/webhook/ok/"),
        _make_receive(b""),
        buf,
    )
    assert buf.status == 400


@pytest.mark.asyncio
@override_settings(TELEGRAM_WEBHOOK_SECRET="ok")
async def test_webhook_rejects_invalid_json() -> None:
    buf = _AsgiBuffer()
    await handle_webhook(
        _scope("POST", "/bot/webhook/ok/"),
        _make_receive(b"<<<not-json>>>"),
        buf,
    )
    assert buf.status == 400


@pytest.mark.asyncio
@override_settings(TELEGRAM_WEBHOOK_SECRET="ok")
async def test_webhook_swallows_handler_crashes_with_200() -> None:
    """A handler crash must return 200 so Telegram doesn't retry-storm."""
    buf = _AsgiBuffer()

    async def boom(*_args, **_kwargs):
        raise RuntimeError("boom")

    with patch("notifications.bot.webhook._route_update", side_effect=boom):
        await handle_webhook(
            _scope("POST", "/bot/webhook/ok/"),
            _make_receive(b'{"update_id":1}'),
            buf,
        )
    assert buf.status == 200


# ----------------------------------------------------------------------------
# Story 9.1 — /start and /help handlers
# ----------------------------------------------------------------------------


@pytest.mark.asyncio
@override_settings(
    TELEGRAM_WEBHOOK_SECRET="ok",
    TELEGRAM_BOT_TOKEN="fake-token",
    WEBAPP_URL="https://iwallet.example/app/home/",
)
async def test_webhook_routes_start_command_and_sends_welcome() -> None:
    seen: list[dict] = []

    def http_handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 1}})

    mock_client = _mock_client(http_handler)
    with patch.object(handlers_module, "_bot_client", return_value=mock_client):
        buf = _AsgiBuffer()
        body = json.dumps(
            {
                "update_id": 1,
                "message": {
                    "message_id": 10,
                    "chat": {"id": 12345, "type": "private"},
                    "from": {"id": 12345, "first_name": "Eric"},
                    "text": "/start",
                },
            }
        ).encode("utf-8")
        await handle_webhook(
            _scope("POST", "/bot/webhook/ok/"),
            _make_receive(body),
            buf,
        )
    assert buf.status == 200
    assert seen, "bot did not call sendMessage"
    assert seen[0]["chat_id"] == 12345
    assert "Salom" in seen[0]["text"]
    # Inline keyboard contains a WebApp button.
    assert "inline_keyboard" in seen[0]["reply_markup"]


@pytest.mark.asyncio
@override_settings(
    TELEGRAM_WEBHOOK_SECRET="ok",
    TELEGRAM_BOT_TOKEN="fake-token",
    WEBAPP_URL="https://iwallet.example/app/home/",
)
async def test_webhook_routes_start_with_deeplink_payload() -> None:
    seen: list[dict] = []

    def http_handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 1}})

    mock_client = _mock_client(http_handler)
    with patch.object(handlers_module, "_bot_client", return_value=mock_client):
        buf = _AsgiBuffer()
        body = json.dumps(
            {
                "update_id": 2,
                "message": {
                    "message_id": 11,
                    "chat": {"id": 55, "type": "private"},
                    "text": "/start action_recurring__42",
                },
            }
        ).encode("utf-8")
        await handle_webhook(
            _scope("POST", "/bot/webhook/ok/"),
            _make_receive(body),
            buf,
        )
    assert seen
    webapp_url = seen[0]["reply_markup"]["inline_keyboard"][0][0]["web_app"]["url"]
    assert "startapp=action_recurring__42" in webapp_url


@pytest.mark.asyncio
@override_settings(
    TELEGRAM_WEBHOOK_SECRET="ok",
    TELEGRAM_BOT_TOKEN="fake-token",
    WEBAPP_URL="https://iwallet.example/app/home/",
)
async def test_webhook_routes_help_command() -> None:
    seen: list[dict] = []

    def http_handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
        return httpx.Response(200, json={"ok": True})

    mock_client = _mock_client(http_handler)
    with patch.object(handlers_module, "_bot_client", return_value=mock_client):
        buf = _AsgiBuffer()
        body = json.dumps(
            {
                "update_id": 3,
                "message": {
                    "message_id": 12,
                    "chat": {"id": 77},
                    "text": "/help",
                },
            }
        ).encode("utf-8")
        await handle_webhook(
            _scope("POST", "/bot/webhook/ok/"),
            _make_receive(body),
            buf,
        )
    assert seen
    assert "IWALLET" in seen[0]["text"]


@pytest.mark.asyncio
@override_settings(
    TELEGRAM_WEBHOOK_SECRET="ok",
    TELEGRAM_BOT_TOKEN="fake-token",
    WEBAPP_URL="https://iwallet.example/app/home/",
)
async def test_webhook_ignores_non_command_text_message() -> None:
    seen: list[dict] = []

    def http_handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
        return httpx.Response(200, json={"ok": True})

    mock_client = _mock_client(http_handler)
    with patch.object(handlers_module, "_bot_client", return_value=mock_client):
        buf = _AsgiBuffer()
        body = json.dumps(
            {
                "update_id": 4,
                "message": {
                    "message_id": 12,
                    "chat": {"id": 77},
                    "text": "Hello there!",
                },
            }
        ).encode("utf-8")
        await handle_webhook(
            _scope("POST", "/bot/webhook/ok/"),
            _make_receive(body),
            buf,
        )
    # No reply: bot stays quiet on non-command chatter.
    assert seen == []


# ----------------------------------------------------------------------------
# Story 9.5 — callback_query routing
# ----------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
@override_settings(
    TELEGRAM_WEBHOOK_SECRET="ok",
    TELEGRAM_BOT_TOKEN="fake-token",
)
@pytest.mark.asyncio
async def test_webhook_callback_recurring_confirm_round_trip() -> None:
    """Tap "Tasdiqlash" → edit message text, answer callback."""
    from datetime import date as _date

    user = await UserFactory._meta.model.objects.acreate(telegram_id=600, first_name="X")
    tx = await TransactionFactory._meta.model.objects.acreate(
        user=user,
        type="expense",
        amount="100000.00",
        currency="UZS",
        date=_date.today(),
    )

    seen: list[tuple[str, dict]] = []

    def http_handler(request: httpx.Request) -> httpx.Response:
        method = request.url.path.rsplit("/", 1)[-1]
        body = json.loads(request.content)
        seen.append((method, body))
        return httpx.Response(200, json={"ok": True, "result": True})

    mock_client = _mock_client(http_handler)
    with patch.object(handlers_module, "_bot_client", return_value=mock_client):
        buf = _AsgiBuffer()
        body = json.dumps(
            {
                "update_id": 5,
                "callback_query": {
                    "id": "cb-1",
                    "from": {"id": 600, "first_name": "X"},
                    "message": {
                        "message_id": 100,
                        "chat": {"id": 600},
                        "text": "old",
                    },
                    "data": f"rec:ok:{tx.id}",
                },
            }
        ).encode("utf-8")
        await handle_webhook(
            _scope("POST", "/bot/webhook/ok/"),
            _make_receive(body),
            buf,
        )

    methods = [m for m, _ in seen]
    assert "editMessageText" in methods
    assert "answerCallbackQuery" in methods
    edit_body = next(b for m, b in seen if m == "editMessageText")
    assert "Tasdiqlandi" in edit_body["text"]


@pytest.mark.django_db(transaction=True)
@override_settings(
    TELEGRAM_WEBHOOK_SECRET="ok",
    TELEGRAM_BOT_TOKEN="fake-token",
)
@pytest.mark.asyncio
async def test_webhook_callback_debt_confirm_closes_debt() -> None:
    user = await UserFactory._meta.model.objects.acreate(telegram_id=601, first_name="X")
    debt = await DebtFactory._meta.model.objects.acreate(
        user=user,
        direction="borrowed",
        counterparty="Bek",
        original_amount="50000.00",
        remaining_amount="50000.00",
        currency="UZS",
        state=DebtState.OPEN.value,
    )

    seen: list[tuple[str, dict]] = []

    def http_handler(request: httpx.Request) -> httpx.Response:
        method = request.url.path.rsplit("/", 1)[-1]
        body = json.loads(request.content)
        seen.append((method, body))
        return httpx.Response(200, json={"ok": True, "result": True})

    mock_client = _mock_client(http_handler)
    with patch.object(handlers_module, "_bot_client", return_value=mock_client):
        buf = _AsgiBuffer()
        body = json.dumps(
            {
                "update_id": 6,
                "callback_query": {
                    "id": "cb-2",
                    "from": {"id": 601},
                    "message": {
                        "message_id": 101,
                        "chat": {"id": 601},
                        "text": "debt due",
                    },
                    "data": f"debt:ok:{debt.id}",
                },
            }
        ).encode("utf-8")
        await handle_webhook(
            _scope("POST", "/bot/webhook/ok/"),
            _make_receive(body),
            buf,
        )

    await debt.arefresh_from_db()
    assert debt.state == DebtState.CLOSED.value
    edit_body = next(b for m, b in seen if m == "editMessageText")
    assert "yopildi" in edit_body["text"].lower()


# ----------------------------------------------------------------------------
# App-level routing: /healthz falls through to Django
# ----------------------------------------------------------------------------


@pytest.mark.asyncio
@override_settings(TELEGRAM_WEBHOOK_SECRET="ok")
async def test_app_delegates_non_webhook_paths_to_django() -> None:
    """The webhook ASGI app passes `/anything` to the inner Django app.

    We can't easily exercise Django ASGI through the bare scope harness (host
    validation + middleware stack make for noisy plumbing), so we just verify
    the dispatch decision: webhook prefix is handled inline, everything else
    invokes the cached Django app.
    """
    sentinel = {"called": False}

    async def fake_django(_scope, _receive, _send) -> None:
        sentinel["called"] = True

    with patch("notifications.bot.webhook._django_app", new=fake_django):
        buf = _AsgiBuffer()
        await app(
            {
                "type": "http",
                "method": "GET",
                "path": "/admin/",
                "headers": [],
                "query_string": b"",
            },
            _make_receive(b""),
            buf,
        )
    assert sentinel["called"] is True


@pytest.mark.asyncio
async def test_app_handles_lifespan_startup_and_shutdown() -> None:
    """uvicorn fires lifespan messages — we must ack them or the worker hangs."""
    messages: list[dict] = []

    async def receive() -> dict:
        # First call: startup. Second call: shutdown.
        if not messages:
            return {"type": "lifespan.startup"}
        return {"type": "lifespan.shutdown"}

    async def send(message: dict) -> None:
        messages.append(message)

    await app({"type": "lifespan"}, receive, send)
    assert messages[0]["type"] == "lifespan.startup.complete"
    assert messages[-1]["type"] == "lifespan.shutdown.complete"
