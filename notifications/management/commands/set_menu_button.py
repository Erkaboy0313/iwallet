"""Set the bot's chat menu button to a Telegram Web App (Mini App).

BotFather's "Page" menu button option opens the URL as a plain link and does
NOT supply initData. We need menu_button.type = "web_app" so Telegram injects
the signed initData on launch. This command idempotently posts that config to
the Bot API. Run once after deploy; safe to re-run.
"""

import json

import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

BOT_API_BASE = "https://api.telegram.org"


class Command(BaseCommand):
    help = "Configure the bot's default chat menu button as a Web App (Mini App)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--text",
            default="Ochish",
            help="Menu button label shown in chats (default: 'Ochish').",
        )
        parser.add_argument(
            "--url",
            default=None,
            help="Web App URL. Defaults to settings.WEBAPP_URL or hard-coded prod URL.",
        )

    def handle(self, *_args, **options):
        token = getattr(settings, "TELEGRAM_BOT_TOKEN", None)
        if not token:
            raise CommandError("TELEGRAM_BOT_TOKEN not configured in settings")

        url = options["url"] or getattr(
            settings, "WEBAPP_URL", "https://iwallet.buildermode.uz/app/home/"
        )
        text = options["text"]

        payload = {
            "menu_button": {
                "type": "web_app",
                "text": text,
                "web_app": {"url": url},
            }
        }

        self.stdout.write(f"Posting setChatMenuButton with: {json.dumps(payload)}")
        resp = requests.post(
            f"{BOT_API_BASE}/bot{token}/setChatMenuButton",
            json=payload,
            timeout=10,
        )
        data = resp.json()
        if not data.get("ok"):
            raise CommandError(f"Telegram API rejected: {data}")
        self.stdout.write(self.style.SUCCESS(f"Menu button set OK: {data}"))

        verify = requests.get(f"{BOT_API_BASE}/bot{token}/getChatMenuButton", timeout=10).json()
        self.stdout.write(f"getChatMenuButton: {json.dumps(verify, indent=2)}")
