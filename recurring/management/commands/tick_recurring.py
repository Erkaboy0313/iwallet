"""Management command: materialize today's due recurring transactions (Story 7.3).

Usage::

    python manage.py tick_recurring             # uses today's local date
    python manage.py tick_recurring --date 2026-07-01   # backfill / debug

Designed for a daily systemd timer (Eric will wire deploy/systemd/
iwallet-tick-recurring.timer later — recommended schedule:
`OnCalendar=*-*-* 09:00:00` in Asia/Tashkent). The command is idempotent:
if invoked twice on the same calendar day, the second run finds
`last_dispatched_on == next_dispatch_at` for every schedule it already
fired and exits without re-creating transactions.

Per Epic 7 AC the next-step is wiring a notifications.PushQueueItem row +
a Telegram bot send via Epic 9. The service layer logs a TODO at the
fire site; this command surfaces totals to stdout for cron logging.
"""

from __future__ import annotations

import logging
from datetime import date

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from recurring.services import dispatch_due

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Materialize today's due recurring transactions (idempotent)."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--date",
            dest="run_date",
            default=None,
            help="Override 'today' (ISO YYYY-MM-DD). Useful for backfill + tests.",
        )

    def handle(self, *_args, **options) -> None:
        run_date = self._parse_run_date(options.get("run_date"))
        result = dispatch_due(today=run_date)

        msg = (
            f"tick_recurring on {run_date.isoformat()}: "
            f"materialized={result.count} "
            f"idempotent_skips={result.skipped_idempotent} "
            f"past_end_skips={result.skipped_past_end}"
        )
        logger.info(msg)
        if result.count:
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
