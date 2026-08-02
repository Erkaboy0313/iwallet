"""Sprint v0.9 — support-chat relay: user ↔ admin.

Covers `handle_message_update`'s two new branches:

  - non-admin text  → forward to admin, log AdminMessageLink
  - admin reply     → look up link, deliver text to original user

Plus edge cases: no ADMIN_CHAT_ID set (silent drop), admin's own text
(no self-forward), admin replies to something unrelated (silent no-op).

Uses `httpx.MockTransport` for the Telegram API — matches the pattern in
`test_webhook.py`.
"""

from __future__ import annotations

import json
from unittest.mock import patch

import httpx
import pytest
from django.test import override_settings

from notifications.bot import handlers as handlers_module
from notifications.bot.handlers import handle_message_update
from notifications.bot.telegram_client import TelegramBotClient
from notifications.models import AdminMessageLink


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
# forward: user text → admin
# ----------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
@override_settings(
    TELEGRAM_BOT_TOKEN="fake-token",
    TELEGRAM_ADMIN_CHAT_ID=999,
)
@pytest.mark.asyncio
async def test_user_text_forwarded_to_admin_and_link_saved() -> None:
    seen: list[dict] = []

    def http_handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
        return httpx.Response(
            200, json={"ok": True, "result": {"message_id": 4242, "chat": {"id": 999}}}
        )

    mock_client = _mock_client(http_handler)
    with patch.object(handlers_module, "_bot_client", return_value=mock_client):
        await handle_message_update(
            {
                "message_id": 10,
                "chat": {"id": 12345, "type": "private"},
                "from": {
                    "id": 12345,
                    "first_name": "Erkaboy",
                    "username": "erkaboy",
                },
                "text": "Salom Eric, savolim bor!",
            }
        )

    assert seen, "bot did not call sendMessage"
    payload = seen[0]
    assert payload["chat_id"] == 999  # goes to admin
    assert payload["parse_mode"] == "HTML"
    assert "@erkaboy" in payload["text"]
    assert "12345" in payload["text"]
    assert "Salom Eric, savolim bor!" in payload["text"]
    assert "Erkaboy" in payload["text"]

    # Link row written for the admin reply routing.
    links = [link async for link in AdminMessageLink.objects.all()]
    assert len(links) == 1
    assert links[0].admin_chat_id == 999
    assert links[0].admin_message_id == 4242
    assert links[0].user_telegram_id == 12345


@pytest.mark.django_db(transaction=True)
@override_settings(
    TELEGRAM_BOT_TOKEN="fake-token",
    TELEGRAM_ADMIN_CHAT_ID=999,
)
@pytest.mark.asyncio
async def test_user_without_username_uses_placeholder() -> None:
    """Some Telegram accounts don't have @username — fall back gracefully."""
    seen: list[dict] = []

    def http_handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 4243}})

    mock_client = _mock_client(http_handler)
    with patch.object(handlers_module, "_bot_client", return_value=mock_client):
        await handle_message_update(
            {
                "message_id": 11,
                "chat": {"id": 5555, "type": "private"},
                "from": {"id": 5555, "first_name": "Anon"},
                "text": "hello",
            }
        )

    assert seen
    assert "no username" in seen[0]["text"]
    # Still identifiable by numeric id.
    assert "5555" in seen[0]["text"]


@pytest.mark.django_db(transaction=True)
@override_settings(
    TELEGRAM_BOT_TOKEN="fake-token",
    TELEGRAM_ADMIN_CHAT_ID=999,
)
@pytest.mark.asyncio
async def test_user_text_html_special_chars_escaped() -> None:
    """User's text goes into an HTML-parse-mode envelope — must be escaped."""
    seen: list[dict] = []

    def http_handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 1}})

    mock_client = _mock_client(http_handler)
    with patch.object(handlers_module, "_bot_client", return_value=mock_client):
        await handle_message_update(
            {
                "message_id": 12,
                "chat": {"id": 700, "type": "private"},
                "from": {"id": 700, "username": "attacker"},
                "text": "<script>alert(1)</script> & <b>bold</b>",
            }
        )

    body = seen[0]["text"]
    # Angle brackets from the user must be escaped so Telegram doesn't parse
    # them as tags; the header <b> we emit ourselves is fine.
    assert "&lt;script&gt;" in body
    assert "&amp;" in body
    assert "<script>" not in body


# ----------------------------------------------------------------------------
# reverse: admin swipe-to-reply → user
# ----------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
@override_settings(
    TELEGRAM_BOT_TOKEN="fake-token",
    TELEGRAM_ADMIN_CHAT_ID=999,
)
@pytest.mark.asyncio
async def test_admin_reply_to_linked_message_delivers_to_user() -> None:
    await AdminMessageLink.objects.acreate(
        admin_chat_id=999,
        admin_message_id=4242,
        user_telegram_id=12345,
    )

    seen: list[dict] = []

    def http_handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 1}})

    mock_client = _mock_client(http_handler)
    with patch.object(handlers_module, "_bot_client", return_value=mock_client):
        await handle_message_update(
            {
                "message_id": 50,
                "chat": {"id": 999, "type": "private"},
                "from": {"id": 999, "first_name": "Eric"},
                "reply_to_message": {
                    "message_id": 4242,
                    "chat": {"id": 999},
                    "text": "📩 @erkaboy  (id: 12345)\nFoydalanuvchi: Erkaboy\n—\nSalom",
                },
                "text": "Salom Erkaboy, mana javob.",
            }
        )

    assert seen, "reply was not routed to user"
    payload = seen[0]
    assert payload["chat_id"] == 12345
    assert payload["text"] == "Salom Erkaboy, mana javob."
    # Plain text — no HTML overhead for the user side.
    assert "parse_mode" not in payload


@pytest.mark.django_db(transaction=True)
@override_settings(
    TELEGRAM_BOT_TOKEN="fake-token",
    TELEGRAM_ADMIN_CHAT_ID=999,
)
@pytest.mark.asyncio
async def test_admin_reply_to_unlinked_message_is_silent_noop() -> None:
    """Admin swipes-to-reply on something unrelated — no crash, no delivery."""
    seen: list[dict] = []

    def http_handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 1}})

    mock_client = _mock_client(http_handler)
    with patch.object(handlers_module, "_bot_client", return_value=mock_client):
        await handle_message_update(
            {
                "message_id": 51,
                "chat": {"id": 999, "type": "private"},
                "from": {"id": 999},
                "reply_to_message": {
                    "message_id": 99999,  # not in AdminMessageLink
                    "chat": {"id": 999},
                    "text": "some old message",
                },
                "text": "reply text",
            }
        )
    assert seen == []


# ----------------------------------------------------------------------------
# edge cases
# ----------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
@override_settings(
    TELEGRAM_BOT_TOKEN="fake-token",
    TELEGRAM_ADMIN_CHAT_ID=999,
)
@pytest.mark.asyncio
async def test_admin_own_non_reply_text_does_not_forward_to_self() -> None:
    """If Eric DMs the bot to test something, don't loop it back to himself."""
    seen: list[dict] = []

    def http_handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 1}})

    mock_client = _mock_client(http_handler)
    with patch.object(handlers_module, "_bot_client", return_value=mock_client):
        await handle_message_update(
            {
                "message_id": 60,
                "chat": {"id": 999, "type": "private"},
                "from": {"id": 999, "first_name": "Eric"},
                "text": "testing 123",
            }
        )
    assert seen == []


@pytest.mark.django_db(transaction=True)
@override_settings(
    TELEGRAM_BOT_TOKEN="fake-token",
    TELEGRAM_ADMIN_CHAT_ID=0,
)
@pytest.mark.asyncio
async def test_user_text_silently_dropped_when_admin_id_not_set() -> None:
    """No ADMIN_CHAT_ID → feature disabled, no crash, no send, warning logged."""
    seen: list[dict] = []

    def http_handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 1}})

    mock_client = _mock_client(http_handler)
    with patch.object(handlers_module, "_bot_client", return_value=mock_client):
        await handle_message_update(
            {
                "message_id": 70,
                "chat": {"id": 12345, "type": "private"},
                "from": {"id": 12345, "username": "erkaboy"},
                "text": "help please",
            }
        )
    assert seen == []
    # No link row either.
    count = await AdminMessageLink.objects.acount()
    assert count == 0
