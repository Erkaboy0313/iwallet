"""Management command: deliver pending PushQueueItem rows (Story 9.3).

Usage::

    python manage.py send_pending_pushes              # ship up to 100 items
    python manage.py send_pending_pushes --limit 50   # custom batch size

Designed for a systemd `iwallet-send-pushes.timer` running every ~5 min.
Idempotent: any row whose `sent_at` is already populated short-circuits
before a network call, so re-running on overlapping schedules can't
double-send.

Pattern mirrors `recurring.management.commands.tick_recurring` and
`currencies.management.commands.fetch_rates` (Eric's "manage.py + systemd
timer" baseline — no Celery).
"""

from __future__ import annotations

import asyncio
import logging

from django.core.management.base import BaseCommand

from notifications.services import process_pending

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Deliver up to --limit pending PushQueueItem rows via Telegram."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--limit",
            type=int,
            default=100,
            help="Maximum pending rows to ship in one tick (default: 100).",
        )

    def handle(self, *_args, **options) -> None:
        limit = options["limit"]
        counts = asyncio.run(process_pending(limit=limit))
        msg = (
            f"send_pending_pushes: sent={counts['sent']} "
            f"failed={counts['failed']} skipped={counts['skipped']}"
        )
        logger.info(msg)
        if counts["sent"]:
            self.stdout.write(self.style.SUCCESS(msg))
        else:
            self.stdout.write(msg)
