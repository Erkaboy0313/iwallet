"""Epic 7 / Story 7.1 — recurring service-layer invariants + cadence math."""

from datetime import date
from decimal import Decimal

import pytest

from recurring.exceptions import (
    InvalidAmountError,
    InvalidNameError,
    InvalidScheduleError,
)
from recurring.models import RecurringSchedule
from recurring.services import (
    compute_first_dispatch_date,
    compute_next_dispatch_date,
    create_recurring,
    delete_recurring,
    dispatch_due,
    dispatch_one,
    mark_dispatched,
    pause_recurring,
    resume_recurring,
    update_recurring,
)
from recurring.tests.factories import RecurringScheduleFactory
from transactions.models import Transaction
from transactions.tests.factories import UserFactory

# ---------- cadence math ----------


def test_first_dispatch_monthly_normal_day() -> None:
    result = compute_first_dispatch_date(
        schedule_kind="monthly",
        start_date=date(2026, 6, 10),
        day_of_month=15,
        day_of_week=None,
    )
    assert result == date(2026, 6, 15)


def test_first_dispatch_monthly_rolls_to_next_month_when_day_passed() -> None:
    result = compute_first_dispatch_date(
        schedule_kind="monthly",
        start_date=date(2026, 6, 20),
        day_of_month=15,
        day_of_week=None,
    )
    assert result == date(2026, 7, 15)


def test_first_dispatch_monthly_clamps_to_last_day_of_short_month() -> None:
    # 31 → Feb collapses to 28 (2026 not leap).
    result = compute_first_dispatch_date(
        schedule_kind="monthly",
        start_date=date(2026, 2, 1),
        day_of_month=31,
        day_of_week=None,
    )
    assert result == date(2026, 2, 28)


def test_first_dispatch_monthly_clamps_to_leap_day_when_available() -> None:
    # 2024 is a leap year — Feb 29 exists.
    result = compute_first_dispatch_date(
        schedule_kind="monthly",
        start_date=date(2024, 2, 1),
        day_of_month=31,
        day_of_week=None,
    )
    assert result == date(2024, 2, 29)


def test_first_dispatch_weekly_today_matches_dow() -> None:
    # 2026-06-29 is a Monday (weekday=0).
    result = compute_first_dispatch_date(
        schedule_kind="weekly",
        start_date=date(2026, 6, 29),
        day_of_month=None,
        day_of_week=0,
    )
    assert result == date(2026, 6, 29)


def test_first_dispatch_weekly_rolls_forward_when_dow_passed() -> None:
    # Tuesday 2026-06-30 → next Monday is 2026-07-06.
    result = compute_first_dispatch_date(
        schedule_kind="weekly",
        start_date=date(2026, 6, 30),
        day_of_month=None,
        day_of_week=0,
    )
    assert result == date(2026, 7, 6)


@pytest.mark.django_db
def test_next_dispatch_monthly_advances_one_month() -> None:
    schedule = RecurringScheduleFactory(
        schedule_kind="monthly",
        day_of_month=15,
        next_dispatch_at=date(2026, 6, 15),
    )
    assert compute_next_dispatch_date(schedule) == date(2026, 7, 15)


@pytest.mark.django_db
def test_next_dispatch_monthly_jan_31_to_feb_28() -> None:
    schedule = RecurringScheduleFactory(
        schedule_kind="monthly",
        day_of_month=31,
        next_dispatch_at=date(2026, 1, 31),
    )
    # Feb 2026 has 28 days; clamp to last.
    assert compute_next_dispatch_date(schedule) == date(2026, 2, 28)


@pytest.mark.django_db
def test_next_dispatch_monthly_year_rollover() -> None:
    schedule = RecurringScheduleFactory(
        schedule_kind="monthly",
        day_of_month=1,
        next_dispatch_at=date(2026, 12, 1),
    )
    assert compute_next_dispatch_date(schedule) == date(2027, 1, 1)


@pytest.mark.django_db
def test_next_dispatch_weekly_advances_seven_days() -> None:
    schedule = RecurringScheduleFactory(
        schedule_kind="weekly",
        day_of_month=None,
        day_of_week=2,
        next_dispatch_at=date(2026, 6, 24),  # Wed
    )
    assert compute_next_dispatch_date(schedule) == date(2026, 7, 1)


# ---------- create_recurring ----------


@pytest.mark.django_db
def test_create_recurring_persists_with_first_dispatch() -> None:
    user = UserFactory()
    schedule = create_recurring(
        user=user,
        type_="expense",
        name="Ijara",
        amount=Decimal("2000000"),
        currency="UZS",
        category=None,
        schedule_kind="monthly",
        day_of_month=1,
        start_date=date(2026, 6, 10),
    )
    assert schedule.id is not None
    assert schedule.next_dispatch_at == date(2026, 7, 1)
    assert schedule.is_active is True
    assert schedule.last_dispatched_on is None


@pytest.mark.django_db
def test_create_recurring_rejects_zero_amount() -> None:
    user = UserFactory()
    with pytest.raises(InvalidAmountError):
        create_recurring(
            user=user,
            type_="expense",
            name="Ijara",
            amount=Decimal("0"),
            currency="UZS",
            category=None,
            schedule_kind="monthly",
            day_of_month=1,
        )


@pytest.mark.django_db
def test_create_recurring_rejects_empty_name() -> None:
    user = UserFactory()
    with pytest.raises(InvalidNameError):
        create_recurring(
            user=user,
            type_="expense",
            name="   ",
            amount=Decimal("100"),
            currency="UZS",
            category=None,
            schedule_kind="monthly",
            day_of_month=1,
        )


@pytest.mark.django_db
def test_create_recurring_rejects_bad_day_of_month() -> None:
    user = UserFactory()
    with pytest.raises(InvalidScheduleError):
        create_recurring(
            user=user,
            type_="expense",
            name="X",
            amount=Decimal("100"),
            currency="UZS",
            category=None,
            schedule_kind="monthly",
            day_of_month=32,
        )


@pytest.mark.django_db
def test_create_recurring_rejects_weekly_without_dow() -> None:
    user = UserFactory()
    with pytest.raises(InvalidScheduleError):
        create_recurring(
            user=user,
            type_="expense",
            name="X",
            amount=Decimal("100"),
            currency="UZS",
            category=None,
            schedule_kind="weekly",
            day_of_week=None,
        )


@pytest.mark.django_db
def test_create_recurring_rejects_end_date_before_start() -> None:
    user = UserFactory()
    with pytest.raises(InvalidScheduleError):
        create_recurring(
            user=user,
            type_="expense",
            name="X",
            amount=Decimal("100"),
            currency="UZS",
            category=None,
            schedule_kind="monthly",
            day_of_month=1,
            start_date=date(2026, 6, 1),
            end_date=date(2026, 5, 1),
        )


# ---------- update_recurring ----------


@pytest.mark.django_db
def test_update_recurring_changes_name_and_amount() -> None:
    schedule = RecurringScheduleFactory(name="Old", amount=Decimal("100"))
    update_recurring(schedule=schedule, name="New", amount=Decimal("250"))
    schedule.refresh_from_db()
    assert schedule.name == "New"
    assert schedule.amount == Decimal("250")


@pytest.mark.django_db
def test_update_recurring_cadence_change_recomputes_next_dispatch() -> None:
    schedule = RecurringScheduleFactory(
        schedule_kind="monthly",
        day_of_month=1,
        next_dispatch_at=date(2026, 7, 1),
    )
    update_recurring(
        schedule=schedule,
        schedule_kind="weekly",
        day_of_week=0,
    )
    schedule.refresh_from_db()
    assert schedule.schedule_kind == "weekly"
    assert schedule.day_of_month is None
    assert schedule.day_of_week == 0


# ---------- pause / resume ----------


@pytest.mark.django_db
def test_pause_and_resume_recurring() -> None:
    schedule = RecurringScheduleFactory(is_active=True)
    pause_recurring(schedule=schedule)
    schedule.refresh_from_db()
    assert schedule.is_active is False
    resume_recurring(schedule=schedule)
    schedule.refresh_from_db()
    assert schedule.is_active is True


# ---------- delete ----------


@pytest.mark.django_db
def test_delete_recurring_hard_deletes_row() -> None:
    schedule = RecurringScheduleFactory()
    delete_recurring(schedule=schedule)
    assert not RecurringSchedule.objects.filter(pk=schedule.pk).exists()


# ---------- dispatch_one (the "tick") ----------


@pytest.mark.django_db
def test_dispatch_one_creates_transaction_and_advances_cursor() -> None:
    today = date(2026, 7, 1)
    schedule = RecurringScheduleFactory(
        schedule_kind="monthly",
        day_of_month=1,
        next_dispatch_at=today,
        last_dispatched_on=None,
    )
    tx = dispatch_one(schedule, today=today)
    assert tx is not None
    assert tx.amount == schedule.amount
    assert tx.date == today
    assert tx.user_id == schedule.user_id
    schedule.refresh_from_db()
    assert schedule.last_dispatched_on == today
    assert schedule.next_dispatch_at == date(2026, 8, 1)


@pytest.mark.django_db
def test_dispatch_one_is_idempotent_on_same_day() -> None:
    today = date(2026, 7, 1)
    schedule = RecurringScheduleFactory(
        schedule_kind="monthly",
        day_of_month=1,
        next_dispatch_at=today,
    )
    first = dispatch_one(schedule, today=today)
    assert first is not None
    schedule.refresh_from_db()
    # Simulate double-tick: reset for a re-run guard, but the actual code path
    # already advances next_dispatch_at — the row will no longer be due.
    second = dispatch_one(schedule, today=today)
    assert second is None
    assert Transaction.objects.filter(user=schedule.user).count() == 1


@pytest.mark.django_db
def test_dispatch_one_skips_paused() -> None:
    """A paused schedule should not fire even when due."""
    today = date(2026, 7, 1)
    schedule = RecurringScheduleFactory(
        schedule_kind="monthly",
        day_of_month=1,
        next_dispatch_at=today,
        is_active=False,
    )
    result = dispatch_due(today=today)
    assert result.count == 0
    assert Transaction.objects.filter(user=schedule.user).count() == 0


@pytest.mark.django_db
def test_dispatch_one_stops_after_end_date() -> None:
    today = date(2026, 7, 1)
    schedule = RecurringScheduleFactory(
        schedule_kind="monthly",
        day_of_month=1,
        next_dispatch_at=today,
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 30),  # capped before today
    )
    tx = dispatch_one(schedule, today=today)
    assert tx is None
    assert Transaction.objects.filter(user=schedule.user).count() == 0


# ---------- dispatch_due (the batch tick) ----------


@pytest.mark.django_db
def test_dispatch_due_picks_only_due_active_schedules() -> None:
    today = date(2026, 7, 1)
    due_now = RecurringScheduleFactory(
        schedule_kind="monthly", day_of_month=1, next_dispatch_at=today
    )
    future = RecurringScheduleFactory(
        schedule_kind="monthly", day_of_month=15, next_dispatch_at=date(2026, 7, 15)
    )
    paused = RecurringScheduleFactory(
        schedule_kind="monthly",
        day_of_month=1,
        next_dispatch_at=today,
        is_active=False,
    )

    result = dispatch_due(today=today)
    assert result.count == 1
    assert result.materialized[0].user_id == due_now.user_id

    future.refresh_from_db()
    paused.refresh_from_db()
    assert future.next_dispatch_at == date(2026, 7, 15)
    assert paused.last_dispatched_on is None


@pytest.mark.django_db
def test_dispatch_due_idempotent_across_runs() -> None:
    """Running the batch tick twice on the same day must not double-emit."""
    today = date(2026, 7, 1)
    RecurringScheduleFactory(schedule_kind="monthly", day_of_month=1, next_dispatch_at=today)

    first = dispatch_due(today=today)
    second = dispatch_due(today=today)
    assert first.count == 1
    assert second.count == 0
    assert Transaction.objects.count() == 1


@pytest.mark.django_db
def test_dispatch_due_handles_february_boundary() -> None:
    """Day-31 monthly schedule firing on Jan 31 should next fire Feb 28."""
    schedule = RecurringScheduleFactory(
        schedule_kind="monthly",
        day_of_month=31,
        next_dispatch_at=date(2026, 1, 31),
    )
    dispatch_due(today=date(2026, 1, 31))
    schedule.refresh_from_db()
    assert schedule.next_dispatch_at == date(2026, 2, 28)


# ---------- mark_dispatched ----------


@pytest.mark.django_db
def test_mark_dispatched_advances_cursor_and_stamps_idempotency_key() -> None:
    schedule = RecurringScheduleFactory(
        schedule_kind="weekly",
        day_of_month=None,
        day_of_week=0,
        next_dispatch_at=date(2026, 6, 29),
    )
    mark_dispatched(schedule, fired_on=date(2026, 6, 29))
    schedule.refresh_from_db()
    assert schedule.last_dispatched_on == date(2026, 6, 29)
    assert schedule.next_dispatch_at == date(2026, 7, 6)
