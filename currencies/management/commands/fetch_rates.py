"""Management command: fetch CBU.uz daily rates (Story 5.3).

Usage::

    python manage.py fetch_rates           # only fetch if today's rates missing
    python manage.py fetch_rates --force   # always fetch and overwrite today

Designed for cron / systemd timer (the timer YAML lands later — for now Eric
triggers manually after first deploy and from time to time). Exits 0 on any
non-crash path so the cron doesn't email on transient CBU outages — the stale
fallback in the UI handles user-facing degradation.
"""

from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from currencies.cbu_client import fetch_cbu_rates
from currencies.exceptions import CbuUnavailableError
from currencies.services import store_rates, update_rates_if_stale

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Fetch today's USD/RUB rates from CBU.uz and store them."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--force",
            action="store_true",
            help="Re-fetch and overwrite even if today's rates are already cached.",
        )

    def handle(self, *_args, **options) -> None:
        today = timezone.localdate()
        if options.get("force"):
            self._force_fetch(today)
            return
        attempted = update_rates_if_stale(today=today)
        if not attempted:
            self.stdout.write(self.style.SUCCESS(f"Rates already cached for {today} — no-op."))
            return
        self.stdout.write(self.style.SUCCESS(f"Rates checked/refreshed for {today}."))

    def _force_fetch(self, today: date) -> None:
        try:
            payload = fetch_cbu_rates()
        except CbuUnavailableError as exc:
            self.stderr.write(self.style.WARNING(f"CBU.uz unreachable: {exc}"))
            return
        payload_date = payload.pop("date", today)
        rates = {k: v for k, v in payload.items() if isinstance(v, Decimal)}
        store_rates(on_date=payload_date, rates=rates)
        self.stdout.write(
            self.style.SUCCESS(f"Force-fetched {len(rates)} rates for {payload_date}."),
        )
