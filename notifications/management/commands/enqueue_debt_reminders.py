"""Management command: weekly reminders on still-open raw debt Transactions.

Sprint v0.8 — Eric wanted the bot to nudge users on debts that have been
sitting a week without a follow-up. Run from a weekly (or daily —
idempotent) systemd timer; the underlying service stamps
``debt_reminder_sent_at`` on each txn so double runs the same day are a
no-op.

Usage::

    python manage.py enqueue_debt_reminders

"""

from __future__ import annotations

import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

from notifications.services import enqueue_debt_reminders

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Queue weekly reminder pushes for debt Transactions 7+ days old without follow-up."

    def handle(self, *_args, **_options) -> None:
        now = timezone.now()
        created = enqueue_debt_reminders(now=now)
        msg = f"enqueue_debt_reminders at {now.isoformat()}: created={created}"
        logger.info(msg)
        if created:
            self.stdout.write(self.style.SUCCESS(msg))
        else:
            self.stdout.write(msg)
