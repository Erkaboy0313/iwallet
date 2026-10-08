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

import html
import logging
from typing import Any
from urllib.parse import quote

from asgiref.sync import sync_to_async
from django.conf import settings

from notifications.messages import HELP_TEXT, WELCOME_TEXT
from notifications.models import AdminMessageLink
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
        "https://track.hygen.uz/app/home/",
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
    """Dispatch a Telegram `message` update to the right command handler.

    Order of branches:
      1. `/start`, `/help` — always answered.
      2. Admin's swipe-to-reply on a forwarded user message → relay text back.
      3. Any other text from a non-admin user → forward into admin chat.
      4. Anything else → silent no-op.
    """
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

    # Support-chat relay (both directions). Skip entirely if the feature is
    # not configured — user's text is silently dropped after a warning log.
    admin_chat_id = getattr(settings, "TELEGRAM_ADMIN_CHAT_ID", 0) or 0
    if not admin_chat_id:
        logger.warning("bot: TELEGRAM_ADMIN_CHAT_ID not set — dropping text from chat=%s", chat_id)
        return

    reply_to = message.get("reply_to_message")
    sender = message.get("from") or {}
    sender_id = sender.get("id")

    # (2) Admin replied to a forwarded user message → route back to that user.
    if reply_to and sender_id == admin_chat_id:
        routed = await _relay_admin_reply(reply_to, text)
        if routed:
            return
        # Fall through: admin typed a random text that happens to be a reply
        # to something unrelated. Nothing else to do — don't forward the
        # admin's own message to themselves.
        return

    # (3) Non-admin user's text → forward to admin. Do NOT forward messages
    # the admin sent to themselves (they may DM the bot to test something).
    if sender_id == admin_chat_id:
        logger.debug("bot: admin self-message, no forward (chat=%s)", chat_id)
        return

    await _forward_to_admin(chat_id, sender, text)


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
# Sprint v0.9 — support-chat relay (user ↔ admin)
# ----------------------------------------------------------------------------


def _format_admin_forward(user_dict: dict[str, Any], text: str) -> str:
    """Compose the HTML-formatted admin-facing message.

    Escapes the user's text so `<`, `&`, etc. don't blow up `parse_mode=HTML`.
    """
    username = user_dict.get("username")
    display_username = f"@{username}" if username else "no username"
    first_name = user_dict.get("first_name") or ""
    last_name = user_dict.get("last_name") or ""
    full_name = " ".join(part for part in (first_name, last_name) if part) or "—"
    user_id = user_dict.get("id", "?")

    header = (
        f"📩 <b>{html.escape(display_username)}</b>  (id: {user_id})\n"
        f"Foydalanuvchi: {html.escape(full_name)}"
    )
    return f"{header}\n—\n{html.escape(text)}"


async def _forward_to_admin(
    user_chat_id: int,
    user_dict: dict[str, Any],
    text: str,
) -> None:
    """Send a formatted message into the admin chat and log the link.

    On send failure (bot blocked by admin, wrong id, etc.) we log and drop —
    the user sees nothing. Their message is lost; this is acceptable for MVP
    since the admin chat_id going bad is a config problem, not a user problem.
    """
    admin_chat_id = getattr(settings, "TELEGRAM_ADMIN_CHAT_ID", 0) or 0
    if not admin_chat_id:
        return  # defense in depth — caller should have short-circuited already

    body = _format_admin_forward(user_dict, text)
    async with _bot_client() as client:
        try:
            response = await client.send_message(
                chat_id=admin_chat_id,
                text=body,
                parse_mode="HTML",
            )
        except TelegramAPIError as exc:
            logger.warning("bot: forward to admin failed for user=%s: %s", user_chat_id, exc)
            return

    message_id = (response.get("result") or {}).get("message_id")
    if message_id is None:
        logger.warning("bot: admin forward returned no message_id: %s", response)
        return

    await sync_to_async(_save_link, thread_sensitive=True)(
        admin_chat_id, int(message_id), int(user_chat_id)
    )


def _save_link(admin_chat_id: int, admin_message_id: int, user_telegram_id: int) -> None:
    """Insert an AdminMessageLink, tolerating the (rare) duplicate race."""
    AdminMessageLink.objects.get_or_create(
        admin_chat_id=admin_chat_id,
        admin_message_id=admin_message_id,
        defaults={"user_telegram_id": user_telegram_id},
    )


async def _relay_admin_reply(
    reply_to_message: dict[str, Any],
    admin_text: str,
) -> bool:
    """If `reply_to_message` maps to a user, send `admin_text` to that user.

    Returns True if the reply was routed, False if the replied-to message
    isn't one of our forwards (silent no-op — the admin may have swipe-replied
    to something random in the same chat).
    """
    replied_chat_id = (reply_to_message.get("chat") or {}).get("id")
    replied_message_id = reply_to_message.get("message_id")
    if replied_chat_id is None or replied_message_id is None:
        return False

    link = await sync_to_async(_lookup_link, thread_sensitive=True)(
        int(replied_chat_id), int(replied_message_id)
    )
    if link is None:
        return False

    async with _bot_client() as client:
        try:
            await client.send_message(
                chat_id=link.user_telegram_id,
                text=admin_text,
            )
        except TelegramAPIError as exc:
            logger.warning(
                "bot: admin reply relay failed for user=%s: %s",
                link.user_telegram_id,
                exc,
            )
            # Still consider it "routed" — the mapping matched; the delivery
            # failure is a Telegram-side problem the admin can retry manually.
            return True
    return True


def _lookup_link(admin_chat_id: int, admin_message_id: int) -> AdminMessageLink | None:
    return AdminMessageLink.objects.filter(
        admin_chat_id=admin_chat_id,
        admin_message_id=admin_message_id,
    ).first()


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
