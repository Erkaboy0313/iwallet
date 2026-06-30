"""Recurring service-layer invariants + cadence math + prompt resolution."""

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
    confirm_prompt,
    create_recurring,
    defer_prompt,
    delete_recurring,
    pause_recurring,
    resume_recurring,
    skip_prompt,
    update_recurring,
)
from recurring.tests.factories import RecurringScheduleFactory
from transactions.models import Transaction
from transactions.tests.factories import UserFactory

# ---------- cadence math ----------


def test_first_dispatch_monthly_normal_day() -> None:
    assert compute_first_dispatch_date(
        schedule_kind="monthly",
        start_date=date(2026, 6, 10),
        day_of_month=15,
        day_of_week=None,
    ) == date(2026, 6, 15)


def test_first_dispatch_monthly_rolls_to_next_month_when_day_passed() -> None:
    assert compute_first_dispatch_date(
        schedule_kind="monthly",
        start_date=date(2026, 6, 20),
        day_of_month=15,
        day_of_week=None,
    ) == date(2026, 7, 15)


def test_first_dispatch_monthly_clamps_to_last_day_of_short_month() -> None:
    assert compute_first_dispatch_date(
        schedule_kind="monthly",
        start_date=date(2026, 2, 1),
        day_of_month=31,
        day_of_week=None,
    ) == date(2026, 2, 28)


def test_first_dispatch_monthly_clamps_to_leap_day_when_available() -> None:
    assert compute_first_dispatch_date(
        schedule_kind="monthly",
        start_date=date(2024, 2, 1),
        day_of_month=31,
        day_of_week=None,
    ) == date(2024, 2, 29)


def test_first_dispatch_weekly_today_matches_dow() -> None:
    # 2026-06-29 is a Monday (weekday=0).
    assert compute_first_dispatch_date(
        schedule_kind="weekly",
        start_date=date(2026, 6, 29),
        day_of_month=None,
        day_of_week=0,
    ) == date(2026, 6, 29)


def test_first_dispatch_weekly_rolls_forward_when_dow_passed() -> None:
    assert compute_first_dispatch_date(
        schedule_kind="weekly",
        start_date=date(2026, 6, 30),
        day_of_month=None,
        day_of_week=0,
    ) == date(2026, 7, 6)


def test_first_dispatch_daily_uses_start_date() -> None:
    assert compute_first_dispatch_date(
        schedule_kind="daily",
        start_date=date(2026, 6, 10),
        day_of_month=None,
        day_of_week=None,
    ) == date(2026, 6, 10)


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
        next_dispatch_at=date(2026, 6, 24),
    )
    assert compute_next_dispatch_date(schedule) == date(2026, 7, 1)


@pytest.mark.django_db
def test_next_dispatch_daily_advances_one_day() -> None:
    schedule = RecurringScheduleFactory(
        schedule_kind="daily",
        day_of_month=None,
        day_of_week=None,
        next_dispatch_at=date(2026, 6, 24),
    )
    assert compute_next_dispatch_date(schedule) == date(2026, 6, 25)


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
def test_create_recurring_daily_starts_today() -> None:
    user = UserFactory()
    schedule = create_recurring(
        user=user,
        type_="expense",
        name="Metro",
        amount=Decimal("2000"),
        currency="UZS",
        category=None,
        schedule_kind="daily",
        start_date=date(2026, 6, 10),
    )
    assert schedule.schedule_kind == "daily"
    assert schedule.day_of_month is None
    assert schedule.day_of_week is None
    assert schedule.next_dispatch_at == date(2026, 6, 10)


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


# ---------- prompt resolution: confirm ----------


@pytest.mark.django_db
def test_confirm_prompt_creates_transaction_and_advances_cursor() -> None:
    today = date(2026, 7, 1)
    schedule = RecurringScheduleFactory(
        schedule_kind="monthly",
        day_of_month=1,
        next_dispatch_at=today,
        amount=Decimal("100000"),
    )
    tx = confirm_prompt(schedule=schedule, today=today)
    assert tx is not None
    assert tx.amount == Decimal("100000")
    assert tx.date == today
    schedule.refresh_from_db()
    assert schedule.last_dispatched_on == today
    assert schedule.next_dispatch_at == date(2026, 8, 1)
    assert schedule.defer_until is None


@pytest.mark.django_db
def test_confirm_prompt_with_overridden_amount_doesnt_change_schedule_default() -> None:
    today = date(2026, 7, 1)
    schedule = RecurringScheduleFactory(
        schedule_kind="monthly",
        day_of_month=1,
        next_dispatch_at=today,
        amount=Decimal("100000"),
    )
    tx = confirm_prompt(schedule=schedule, today=today, amount=Decimal("110000"))
    assert tx is not None
    assert tx.amount == Decimal("110000")
    schedule.refresh_from_db()
    assert schedule.amount == Decimal("100000")  # default untouched


@pytest.mark.django_db
def test_confirm_prompt_save_amount_persists_new_default() -> None:
    today = date(2026, 7, 1)
    schedule = RecurringScheduleFactory(
        schedule_kind="monthly",
        day_of_month=1,
        next_dispatch_at=today,
        amount=Decimal("100000"),
    )
    confirm_prompt(
        schedule=schedule,
        today=today,
        amount=Decimal("110000"),
        save_amount=True,
    )
    schedule.refresh_from_db()
    assert schedule.amount == Decimal("110000")


@pytest.mark.django_db
def test_confirm_prompt_is_noop_when_not_due_yet() -> None:
    schedule = RecurringScheduleFactory(
        schedule_kind="monthly",
        day_of_month=15,
        next_dispatch_at=date(2026, 7, 15),
    )
    tx = confirm_prompt(schedule=schedule, today=date(2026, 7, 1))
    assert tx is None
    assert Transaction.objects.count() == 0


@pytest.mark.django_db
def test_confirm_prompt_is_noop_when_paused() -> None:
    today = date(2026, 7, 1)
    schedule = RecurringScheduleFactory(
        schedule_kind="monthly",
        day_of_month=1,
        next_dispatch_at=today,
        is_active=False,
    )
    tx = confirm_prompt(schedule=schedule, today=today)
    assert tx is None
    assert Transaction.objects.count() == 0


@pytest.mark.django_db
def test_confirm_prompt_is_noop_after_end_date() -> None:
    today = date(2026, 7, 1)
    schedule = RecurringScheduleFactory(
        schedule_kind="monthly",
        day_of_month=1,
        next_dispatch_at=today,
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 30),
    )
    tx = confirm_prompt(schedule=schedule, today=today)
    assert tx is None
    assert Transaction.objects.count() == 0


# ---------- prompt resolution: skip ----------


@pytest.mark.django_db
def test_skip_prompt_advances_cursor_without_transaction() -> None:
    today = date(2026, 7, 1)
    schedule = RecurringScheduleFactory(
        schedule_kind="daily",
        day_of_month=None,
        day_of_week=None,
        next_dispatch_at=today,
    )
    skip_prompt(schedule=schedule, today=today)
    schedule.refresh_from_db()
    assert schedule.last_dispatched_on == today
    assert schedule.next_dispatch_at == date(2026, 7, 2)
    assert Transaction.objects.count() == 0


# ---------- prompt resolution: defer ----------


@pytest.mark.django_db
def test_defer_prompt_hides_until_tomorrow_without_advancing() -> None:
    today = date(2026, 7, 1)
    schedule = RecurringScheduleFactory(
        schedule_kind="daily",
        day_of_month=None,
        day_of_week=None,
        next_dispatch_at=today,
    )
    defer_prompt(schedule=schedule, today=today)
    schedule.refresh_from_db()
    assert schedule.defer_until == date(2026, 7, 2)
    assert schedule.next_dispatch_at == today  # cursor not advanced
    assert Transaction.objects.count() == 0
