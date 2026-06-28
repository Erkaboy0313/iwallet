"""Write-side business logic for RecurringSchedule (Epic 7).

Lifecycle services (`create_recurring`, `update_recurring`, `delete_recurring`)
and cadence helpers (`compute_next_dispatch_date`, `mark_dispatched`).

The tick service (`dispatch_due` / `dispatch_one`) lives here too — it walks
all `is_active=True, next_dispatch_at<=today` rows, materializes one
Transaction per due day via `transactions.services.create_transaction`, then
advances `next_dispatch_at` by one cadence step.

Idempotency: `last_dispatched_on` is checked + bumped inside the same atomic
block as transaction creation, so running the tick twice on the same calendar
day cannot double-create.
"""

from __future__ import annotations

import calendar
import logging
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction as db_transaction
from django.utils import timezone

from accounts.models import User
from categories.models import Category
from transactions.models import Transaction
from transactions.services import create_transaction

from .exceptions import InvalidAmountError, InvalidNameError, InvalidScheduleError
from .models import RecurringSchedule, RecurringType, ScheduleKind

logger = logging.getLogger(__name__)

DAYS_IN_WEEK = 7
MAX_NAME_LEN = 64


# ---------- validation helpers ----------


def _validate_amount(amount: Decimal | None) -> None:
    if amount is None or amount <= 0:
        raise InvalidAmountError("Summa musbat bo'lishi kerak.")


def _validate_name(name: str) -> str:
    name = (name or "").strip()
    if not name:
        raise InvalidNameError("Nom kiriting.")
    if len(name) > MAX_NAME_LEN:
        raise InvalidNameError("Nom juda uzun (64 belgidan ortiq).")
    return name


def _validate_cadence(
    *,
    schedule_kind: str,
    day_of_month: int | None,
    day_of_week: int | None,
) -> tuple[int | None, int | None]:
    """Return (day_of_month, day_of_week) coerced to the right shape per kind."""
    if schedule_kind == ScheduleKind.MONTHLY.value:
        if day_of_month is None or not (1 <= day_of_month <= 31):
            raise InvalidScheduleError("Oylik takror uchun kunni (1-31) tanlang.")
        return day_of_month, None
    if schedule_kind == ScheduleKind.WEEKLY.value:
        if day_of_week is None or not (0 <= day_of_week <= 6):
            raise InvalidScheduleError("Haftalik takror uchun hafta kunini tanlang.")
        return None, day_of_week
    raise InvalidScheduleError("Takror turi noto'g'ri.")


# ---------- cadence math ----------


def _clamp_day_to_month(year: int, month: int, day: int) -> int:
    """Feb 30 → Feb 28/29, Apr 31 → Apr 30 etc. (project-context rule)."""
    last = calendar.monthrange(year, month)[1]
    return min(day, last)


def _next_monthly(start_from: date, day_of_month: int) -> date:
    """First date on/after `start_from` whose day-of-month is `day_of_month`.

    If the chosen month has fewer days, fall back to the last day of that month.
    """
    target_day = _clamp_day_to_month(start_from.year, start_from.month, day_of_month)
    candidate = start_from.replace(day=target_day)
    if candidate >= start_from:
        return candidate
    # Roll to next month.
    if start_from.month == 12:
        nyear, nmonth = start_from.year + 1, 1
    else:
        nyear, nmonth = start_from.year, start_from.month + 1
    target_day = _clamp_day_to_month(nyear, nmonth, day_of_month)
    return date(nyear, nmonth, target_day)


def _advance_one_month(current: date, day_of_month: int) -> date:
    """Advance `current` to the next month's clamped day."""
    if current.month == 12:
        nyear, nmonth = current.year + 1, 1
    else:
        nyear, nmonth = current.year, current.month + 1
    target_day = _clamp_day_to_month(nyear, nmonth, day_of_month)
    return date(nyear, nmonth, target_day)


def _next_weekly(start_from: date, day_of_week: int) -> date:
    """First date on/after `start_from` matching ISO weekday `day_of_week` (0=Mon)."""
    offset = (day_of_week - start_from.weekday()) % DAYS_IN_WEEK
    return start_from + timedelta(days=offset)


def compute_first_dispatch_date(
    *,
    schedule_kind: str,
    start_date: date,
    day_of_month: int | None,
    day_of_week: int | None,
) -> date:
    """First fire date >= start_date that matches the cadence.

    Used by create_recurring so the user's start_date is the *earliest* possible
    fire (not the actual fire) — we pick the first cadence-matching day on/after
    it. That way "create on the 5th, schedule on the 1st" reasonably waits until
    next month rather than firing immediately on a wrong day.
    """
    if schedule_kind == ScheduleKind.MONTHLY.value:
        assert day_of_month is not None
        return _next_monthly(start_date, day_of_month)
    if schedule_kind == ScheduleKind.WEEKLY.value:
        assert day_of_week is not None
        return _next_weekly(start_date, day_of_week)
    raise InvalidScheduleError("Takror turi noto'g'ri.")


def compute_next_dispatch_date(schedule: RecurringSchedule) -> date:
    """Given the schedule's current next_dispatch_at, compute the one *after*.

    Pure function — does not write. The tick service calls this after
    materializing the current occurrence to advance the cursor.
    """
    if schedule.schedule_kind == ScheduleKind.MONTHLY.value:
        assert schedule.day_of_month is not None
        return _advance_one_month(schedule.next_dispatch_at, schedule.day_of_month)
    if schedule.schedule_kind == ScheduleKind.WEEKLY.value:
        return schedule.next_dispatch_at + timedelta(days=DAYS_IN_WEEK)
    raise InvalidScheduleError("Takror turi noto'g'ri.")


# ---------- CRUD ----------


@db_transaction.atomic
def create_recurring(
    *,
    user: User,
    type_: str,
    name: str,
    amount: Decimal,
    currency: str,
    category: Category | None,
    schedule_kind: str,
    day_of_month: int | None = None,
    day_of_week: int | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> RecurringSchedule:
    """Create a recurring schedule.

    The first `next_dispatch_at` is computed from `start_date` so the row is
    immediately useful to the tick service without an extra save.
    """
    _validate_amount(amount)
    name = _validate_name(name)
    if type_ not in {t.value for t in RecurringType}:
        raise InvalidScheduleError("Tranzaksiya turi noto'g'ri.")
    day_of_month, day_of_week = _validate_cadence(
        schedule_kind=schedule_kind,
        day_of_month=day_of_month,
        day_of_week=day_of_week,
    )
    if start_date is None:
        start_date = timezone.localdate()
    if end_date is not None and end_date < start_date:
        raise InvalidScheduleError("Tugash sanasi boshlanish sanasidan oldin bo'la olmaydi.")

    next_dispatch_at = compute_first_dispatch_date(
        schedule_kind=schedule_kind,
        start_date=start_date,
        day_of_month=day_of_month,
        day_of_week=day_of_week,
    )
    return RecurringSchedule.objects.create(
        user=user,
        type=type_,
        name=name,
        amount=amount,
        currency=currency,
        category=category,
        schedule_kind=schedule_kind,
        day_of_month=day_of_month,
        day_of_week=day_of_week,
        start_date=start_date,
        end_date=end_date,
        next_dispatch_at=next_dispatch_at,
    )


_UNSET: object = object()


@db_transaction.atomic
def update_recurring(
    *,
    schedule: RecurringSchedule,
    name: str | None = None,
    amount: Decimal | None = None,
    currency: str | None = None,
    category: Category | None | object = _UNSET,
    type_: str | None = None,
    schedule_kind: str | None = None,
    day_of_month: int | None = None,
    day_of_week: int | None = None,
    end_date: date | None | object = _UNSET,
) -> RecurringSchedule:
    """Mutate a recurring schedule.

    `category=None` and `end_date=None` both mean "clear the field" so the
    `_UNSET` sentinel distinguishes "leave unchanged" from "explicitly clear".
    Cadence changes recompute `next_dispatch_at` from today's date so the next
    fire respects the new pattern.
    """
    fields: list[str] = []

    if name is not None:
        schedule.name = _validate_name(name)
        fields.append("name")
    if amount is not None:
        _validate_amount(amount)
        schedule.amount = amount
        fields.append("amount")
    if currency is not None:
        schedule.currency = currency
        fields.append("currency")
    if category is not _UNSET:
        schedule.category = category  # type: ignore[assignment]
        fields.append("category")
    if type_ is not None:
        if type_ not in {t.value for t in RecurringType}:
            raise InvalidScheduleError("Tranzaksiya turi noto'g'ri.")
        schedule.type = type_
        fields.append("type")

    cadence_changed = False
    if schedule_kind is not None:
        new_dom, new_dow = _validate_cadence(
            schedule_kind=schedule_kind,
            day_of_month=day_of_month,
            day_of_week=day_of_week,
        )
        schedule.schedule_kind = schedule_kind
        schedule.day_of_month = new_dom
        schedule.day_of_week = new_dow
        fields.extend(["schedule_kind", "day_of_month", "day_of_week"])
        cadence_changed = True

    if end_date is not _UNSET:
        if end_date is not None and end_date < schedule.start_date:  # type: ignore[operator]
            raise InvalidScheduleError("Tugash sanasi boshlanish sanasidan oldin bo'la olmaydi.")
        schedule.end_date = end_date  # type: ignore[assignment]
        fields.append("end_date")

    if cadence_changed:
        today = timezone.localdate()
        schedule.next_dispatch_at = compute_first_dispatch_date(
            schedule_kind=schedule.schedule_kind,
            start_date=today,
            day_of_month=schedule.day_of_month,
            day_of_week=schedule.day_of_week,
        )
        fields.append("next_dispatch_at")

    if fields:
        fields.append("updated_at")
        schedule.save(update_fields=fields)
    return schedule


@db_transaction.atomic
def delete_recurring(*, schedule: RecurringSchedule) -> None:
    """Hard-delete a recurring schedule.

    No soft-delete here: already-materialized Transactions live independently
    in the transactions table, so removing the schedule doesn't lose history.
    """
    schedule.delete()


@db_transaction.atomic
def set_active(*, schedule: RecurringSchedule, is_active: bool) -> RecurringSchedule:
    """Pause (False) / resume (True) a schedule."""
    if schedule.is_active == is_active:
        return schedule
    schedule.is_active = is_active
    schedule.save(update_fields=["is_active", "updated_at"])
    return schedule


def pause_recurring(*, schedule: RecurringSchedule) -> RecurringSchedule:
    """Pause emissions (alias for clarity at call sites)."""
    return set_active(schedule=schedule, is_active=False)


def resume_recurring(*, schedule: RecurringSchedule) -> RecurringSchedule:
    """Resume emissions."""
    return set_active(schedule=schedule, is_active=True)


# ---------- dispatch (tick) ----------


@dataclass(frozen=True)
class DispatchResult:
    """One tick's outcome — surfaced by the management command for logging."""

    materialized: list[Transaction]
    skipped_past_end: int
    skipped_idempotent: int

    @property
    def count(self) -> int:
        return len(self.materialized)


def mark_dispatched(schedule: RecurringSchedule, *, fired_on: date) -> RecurringSchedule:
    """Stamp the idempotency key and advance the cursor. Caller wraps in atomic."""
    schedule.last_dispatched_on = fired_on
    schedule.next_dispatch_at = compute_next_dispatch_date(schedule)
    schedule.save(update_fields=["last_dispatched_on", "next_dispatch_at", "updated_at"])
    return schedule


@db_transaction.atomic
def dispatch_one(
    schedule: RecurringSchedule,
    *,
    today: date,
) -> Transaction | None:
    """Materialize today's Transaction for `schedule` if due and not yet fired.

    Returns the new Transaction, or None if the row is not due yet, was already
    fired today (idempotency), is paused, or has been capped by `end_date`.
    """
    # Paused → nothing to do.
    if not schedule.is_active:
        return None
    # Not due yet (next fire is in the future).
    if schedule.next_dispatch_at > today:
        return None
    # End-date guardrail: a schedule with end_date in the past stops firing,
    # even if next_dispatch_at lagged behind.
    if schedule.end_date is not None and schedule.next_dispatch_at > schedule.end_date:
        return None
    # Idempotency: same calendar day → no-op.
    if schedule.last_dispatched_on == schedule.next_dispatch_at:
        return None

    # Lock the row so concurrent ticks can't double-create.
    locked = RecurringSchedule.objects.select_for_update().get(pk=schedule.pk)
    if not locked.is_active:
        return None
    if locked.next_dispatch_at > today:
        return None
    if locked.last_dispatched_on == locked.next_dispatch_at:
        return None
    if locked.end_date is not None and locked.next_dispatch_at > locked.end_date:
        return None

    tx = create_transaction(
        user=locked.user,
        type=locked.type,
        amount=locked.amount,
        currency=locked.currency,
        date=locked.next_dispatch_at,
        category=locked.category,
        note=f"Takrorlanuvchi: {locked.name}",
    )
    fired_on = locked.next_dispatch_at
    mark_dispatched(locked, fired_on=fired_on)
    # TODO(Epic 9): enqueue a Notification log row + bot push call here so the
    # user gets pinged about each fire. The Notification stub model is wired
    # in notifications/models.py; the queue → bot pipeline lands in Epic 9.
    logger.info(
        "recurring schedule %s fired tx=%s on %s",
        locked.id,
        tx.id,
        fired_on.isoformat(),
    )
    return tx


def dispatch_due(*, today: date | None = None) -> DispatchResult:
    """Tick every active schedule whose next_dispatch_at <= today.

    Idempotent at the *day* granularity — if invoked twice on the same date,
    second pass exits early on each row because `last_dispatched_on` already
    equals `next_dispatch_at`.
    """
    if today is None:
        today = timezone.localdate()

    materialized: list[Transaction] = []
    skipped_past_end = 0
    skipped_idempotent = 0

    due = list(
        RecurringSchedule.objects.due_on(today)
        .select_related("user", "category")
        .order_by("next_dispatch_at", "id")
    )
    for schedule in due:
        if schedule.end_date is not None and schedule.next_dispatch_at > schedule.end_date:
            skipped_past_end += 1
            continue
        if schedule.last_dispatched_on == schedule.next_dispatch_at:
            skipped_idempotent += 1
            continue
        tx = dispatch_one(schedule, today=today)
        if tx is None:
            skipped_idempotent += 1
        else:
            materialized.append(tx)

    return DispatchResult(
        materialized=materialized,
        skipped_past_end=skipped_past_end,
        skipped_idempotent=skipped_idempotent,
    )
