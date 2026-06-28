"""Management command: register bot commands + set webhook URL (Story 9.7).

Eric runs this once after a deploy (or after rotating the webhook secret).
Companion to `set_menu_button`. Each call is idempotent — Telegram's
`setWebhook` and `setMyCommands` are pure overwrites.

Usage::

    python manage.py setup_bot                         # uses settings defaults
    python manage.py setup_bot --webhook-url https://iwallet.example/bot/webhook/SECRET/

The webhook URL is built from `settings.WEBHOOK_BASE_URL` (or `WEBAPP_URL`'s
origin as a fallback) + `/bot/webhook/<TELEGRAM_WEBHOOK_SECRET>/` if not
explicitly passed.
"""

from __future__ import annotations

import asyncio
import logging
from urllib.parse import urlparse

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from notifications.bot.telegram_client import TelegramAPIError, TelegramBotClient

logger = logging.getLogger(__name__)

BOT_COMMANDS = [
    {"command": "start", "description": "Ilovani ochish"},
    {"command": "help", "description": "Yordam va ko'rsatma"},
]


class Command(BaseCommand):
    help = "Register /start, /help and configure the Telegram webhook URL."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--webhook-url",
            dest="webhook_url",
            default=None,
            help="Full webhook URL. Defaults to <WEBHOOK_BASE_URL>/bot/webhook/<SECRET>/.",
        )
        parser.add_argument(
            "--skip-webhook",
            action="store_true",
            help="Only register commands; leave the webhook URL untouched.",
        )
        parser.add_argument(
            "--skip-commands",
            action="store_true",
            help="Only set the webhook URL; leave bot commands untouched.",
        )

    def handle(self, *_args, **options) -> None:
        token = getattr(settings, "TELEGRAM_BOT_TOKEN", "")
        if not token:
            raise CommandError("TELEGRAM_BOT_TOKEN not configured.")

        skip_webhook = options.get("skip_webhook", False)
        skip_commands = options.get("skip_commands", False)

        webhook_url = options.get("webhook_url") or _derive_webhook_url()
        if not skip_webhook and not webhook_url:
            raise CommandError(
                "Could not derive webhook URL — pass --webhook-url or set WEBHOOK_BASE_URL.",
            )

        secret = getattr(settings, "TELEGRAM_WEBHOOK_SECRET", "")
        if not skip_webhook and not secret:
            raise CommandError("TELEGRAM_WEBHOOK_SECRET not configured.")

        asyncio.run(
            self._setup(
                token=token,
                webhook_url=webhook_url,
                secret=secret,
                skip_webhook=skip_webhook,
                skip_commands=skip_commands,
            )
        )

    async def _setup(
        self,
        *,
        token: str,
        webhook_url: str | None,
        secret: str,
        skip_webhook: bool,
        skip_commands: bool,
    ) -> None:
        async with TelegramBotClient(bot_token=token) as client:
            if not skip_commands:
                try:
                    await client.set_my_commands(commands=BOT_COMMANDS)
                except TelegramAPIError as exc:
                    raise CommandError(f"setMyCommands failed: {exc}") from exc
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Registered commands: {[c['command'] for c in BOT_COMMANDS]}"
                    ),
                )

            if not skip_webhook and webhook_url:
                try:
                    await client.set_webhook(
                        url=webhook_url,
                        secret_token=secret,
                        allowed_updates=["message", "callback_query"],
                    )
                except TelegramAPIError as exc:
                    raise CommandError(f"setWebhook failed: {exc}") from exc
                self.stdout.write(self.style.SUCCESS(f"Webhook set to: {webhook_url}"))


def _derive_webhook_url() -> str | None:
    """Build the webhook URL from settings.WEBHOOK_BASE_URL or WEBAPP_URL origin."""
    base = getattr(settings, "WEBHOOK_BASE_URL", "")
    if not base:
        webapp_url = getattr(settings, "WEBAPP_URL", "")
        if webapp_url:
            parsed = urlparse(webapp_url)
            if parsed.scheme and parsed.netloc:
                base = f"{parsed.scheme}://{parsed.netloc}"
    if not base:
        return None

    secret = getattr(settings, "TELEGRAM_WEBHOOK_SECRET", "")
    if not secret:
        return None

    base = base.rstrip("/")
    return f"{base}/bot/webhook/{secret}/"
