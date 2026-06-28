"""Per-update handlers for the bot webhook (Stories 9.1 + 9.5).

Each handler is async and receives the already-parsed Update sub-dict
(message or callback_query). All DB work tunnels through `sync_to_async`
because we sit on top of Django's sync ORM.

Telegram API calls go through a freshly-constructed `TelegramBotClient` per
invocation — webhook bursts are O(1) per Update, not O(N), so we don't need
connection pooling here. The `process_pending` consumer is where pooling
matters (it reuses one client across the queue).
"""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import quote

from asgiref.sync import sync_to_async
from django.conf import settings

from notifications.messages import HELP_TEXT, WELCOME_TEXT
from notifications.services import handle_callback

from .telegram_client import TelegramAPIError, TelegramBotClient

logger = logging.getLogger(__name__)


def _bot_client() -> TelegramBotClient:
    token = getattr(settings, "TELEGRAM_BOT_TOKEN", "")
    return TelegramBotClient(bot_token=token)


def _webapp_url(start_param: str | None = None) -> str:
    """Compose the WebApp URL the inline button opens.

    Defaults to `settings.WEBAPP_URL` (or the hardcoded prod URL the existing
    `set_menu_button` command uses). When a deep-link `start_param` is set
    we pass it through as `?startapp=` so the WebApp can re-open the right
    pre-filled flow (Story 9.5 in the wider epic — webapp side ships
    separately).
    """
    base = getattr(
        settings,
        "WEBAPP_URL",
        "https://iwallet.buildermode.uz/app/home/",
    )
    if start_param:
        sep = "&" if "?" in base else "?"
        return f"{base}{sep}startapp={quote(start_param, safe='')}"
    return base


def _open_app_keyboard(start_param: str | None = None) -> dict[str, Any]:
    return {
        "inline_keyboard": [
            [
                {
                    "text": "Ilovani ochish",
                    "web_app": {"url": _webapp_url(start_param)},
                }
            ]
        ]
    }


# ----------------------------------------------------------------------------
# Story 9.1 — /start, /help, generic message handler
# ----------------------------------------------------------------------------


async def handle_message_update(message: dict[str, Any]) -> None:
    """Dispatch a Telegram `message` update to the right command handler."""
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    text = (message.get("text") or "").strip()
    if chat_id is None or not text:
        return

    # Telegram commands look like `/start payload` or `/help@botname`.
    command, _, payload = text.partition(" ")
    command_root = command.split("@", 1)[0]

    if command_root == "/start":
        await _handle_start(chat_id, payload.strip())
        return
    if command_root == "/help":
        await _handle_help(chat_id)
        return

    logger.debug("bot: ignoring text from chat=%s: %r", chat_id, text[:64])


async def _handle_start(chat_id: int, payload: str) -> None:
    """Welcome + WebApp button. `payload` is the optional deep-link tail.

    `/start action_recurring__42` → opens the WebApp with `startapp=action_recurring__42`.
    """
    start_param = payload or None
    text = WELCOME_TEXT
    reply_markup = _open_app_keyboard(start_param)
    async with _bot_client() as client:
        try:
            await client.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=reply_markup,
            )
        except TelegramAPIError as exc:
            logger.warning("bot: /start send failed for chat=%s: %s", chat_id, exc)


async def _handle_help(chat_id: int) -> None:
    async with _bot_client() as client:
        try:
            await client.send_message(
                chat_id=chat_id,
                text=HELP_TEXT,
                reply_markup=_open_app_keyboard(),
            )
        except TelegramAPIError as exc:
            logger.warning("bot: /help send failed for chat=%s: %s", chat_id, exc)


# ----------------------------------------------------------------------------
# Story 9.5 — callback_query → confirm/cancel handler
# ----------------------------------------------------------------------------


async def handle_callback_query(query: dict[str, Any]) -> None:
    """Handle one inline-keyboard tap.

    Flow:
      1. Run the appropriate service callback (sync DB write inside `sync_to_async`).
      2. Edit the original message to show the confirmation status (so the user
         sees what happened and the buttons stop being tap-able).
      3. answerCallbackQuery so the loading spinner on the user's button stops.

    Steps 2/3 are best-effort — if Telegram rejects (e.g. message too old to
    edit) we still consider the callback handled because the DB write happened.
    """
    query_id = query.get("id")
    data = query.get("data") or ""
    message = query.get("message") or {}
    chat_id = (message.get("chat") or {}).get("id")
    message_id = message.get("message_id")

    if not query_id:
        return

    result_text = await sync_to_async(handle_callback, thread_sensitive=True)(data)

    async with _bot_client() as client:
        if chat_id is not None and message_id is not None:
            try:
                await client.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=result_text,
                    reply_markup=None,
                )
            except TelegramAPIError as exc:
                logger.info("bot: edit_message_text failed for chat=%s: %s", chat_id, exc)
        try:
            await client.answer_callback_query(
                callback_query_id=query_id,
            )
        except TelegramAPIError as exc:
            logger.info("bot: answerCallbackQuery failed: %s", exc)
