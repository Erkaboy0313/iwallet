"""Management command: enqueue debt-due reminders (Story 9.4).

Usage::

    python manage.py enqueue_debt_due                  # today
    python manage.py enqueue_debt_due --date 2026-07-01  # explicit date

Run from a daily systemd timer (recommended `OnCalendar=*-*-* 09:00:00`
Asia/Tashkent — same slot as `tick_recurring`). The command is idempotent;
the underlying service skips debts already covered by a recent push.
"""

from __future__ import annotations

import logging
from datetime import date

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from notifications.services import enqueue_debt_due_reminders

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Queue debt_due PushQueueItem rows for debts due on a given date (default: today)."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--date",
            dest="run_date",
            default=None,
            help="Override 'today' (ISO YYYY-MM-DD). Useful for backfill + tests.",
        )

    def handle(self, *_args, **options) -> None:
        run_date = self._parse_run_date(options.get("run_date"))
        created = enqueue_debt_due_reminders(on_date=run_date)
        msg = f"enqueue_debt_due on {run_date.isoformat()}: created={created}"
        logger.info(msg)
        if created:
            self.stdout.write(self.style.SUCCESS(msg))
        else:
            self.stdout.write(msg)

    def _parse_run_date(self, raw: str | None) -> date:
        if raw is None:
            return timezone.localdate()
        try:
            return date.fromisoformat(raw)
        except ValueError as exc:
            raise CommandError(
                f"--date must be ISO YYYY-MM-DD (got {raw!r}).",
            ) from exc
