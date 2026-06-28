"""Epic 7 / Story 7.3 — tick_recurring management command + push enqueue."""

from datetime import date
from io import StringIO

import pytest
from django.core.management import call_command

from notifications.models import NotificationKind, PushQueueItem
from recurring.tests.factories import RecurringScheduleFactory
from transactions.models import Transaction


@pytest.mark.django_db
def test_tick_command_materializes_due_schedule_and_enqueues_push() -> None:
    """When a schedule is due, the tick creates a Transaction AND a
    PushQueueItem row so Epic 9's bot consumer has something to read."""
    today = date(2026, 7, 1)
    schedule = RecurringScheduleFactory(
        schedule_kind="monthly",
        day_of_month=1,
        next_dispatch_at=today,
        name="Ijara",
    )
    stdout = StringIO()
    call_command("tick_recurring", "--date", today.isoformat(), stdout=stdout)
    out = stdout.getvalue()
    assert "materialized=1" in out

    schedule.refresh_from_db()
    assert schedule.last_dispatched_on == today
    assert schedule.next_dispatch_at == date(2026, 8, 1)
    assert Transaction.objects.filter(user=schedule.user).count() == 1

    queued = PushQueueItem.objects.filter(user=schedule.user)
    assert queued.count() == 1
    item = queued.first()
    assert item.kind == NotificationKind.RECURRING_FIRED.value
    assert item.payload_json["schedule_id"] == schedule.id
    assert item.payload_json["schedule_name"] == "Ijara"
    assert item.sent_at is None


@pytest.mark.django_db
def test_tick_command_idempotent_on_double_run() -> None:
    """Running twice on the same date must not double-emit or double-queue."""
    today = date(2026, 7, 1)
    RecurringScheduleFactory(schedule_kind="monthly", day_of_month=1, next_dispatch_at=today)
    call_command("tick_recurring", "--date", today.isoformat(), stdout=StringIO())
    call_command("tick_recurring", "--date", today.isoformat(), stdout=StringIO())
    assert Transaction.objects.count() == 1
    assert PushQueueItem.objects.count() == 1


@pytest.mark.django_db
def test_tick_command_skips_paused_schedule() -> None:
    today = date(2026, 7, 1)
    RecurringScheduleFactory(
        schedule_kind="monthly",
        day_of_month=1,
        next_dispatch_at=today,
        is_active=False,
    )
    stdout = StringIO()
    call_command("tick_recurring", "--date", today.isoformat(), stdout=stdout)
    assert "materialized=0" in stdout.getvalue()
    assert Transaction.objects.count() == 0
    assert PushQueueItem.objects.count() == 0


@pytest.mark.django_db
def test_tick_command_skips_schedule_past_end_date() -> None:
    today = date(2026, 7, 1)
    RecurringScheduleFactory(
        schedule_kind="monthly",
        day_of_month=1,
        next_dispatch_at=today,
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 30),
    )
    stdout = StringIO()
    call_command("tick_recurring", "--date", today.isoformat(), stdout=stdout)
    assert Transaction.objects.count() == 0
    assert PushQueueItem.objects.count() == 0


@pytest.mark.django_db
def test_tick_command_ignores_future_schedules() -> None:
    """A schedule whose next_dispatch_at is tomorrow should not fire today."""
    today = date(2026, 7, 1)
    RecurringScheduleFactory(
        schedule_kind="monthly",
        day_of_month=15,
        next_dispatch_at=date(2026, 7, 15),
    )
    call_command("tick_recurring", "--date", today.isoformat(), stdout=StringIO())
    assert Transaction.objects.count() == 0


@pytest.mark.django_db
def test_tick_command_runs_with_default_date() -> None:
    """Without --date the command uses today; smoke-tests the default path."""
    stdout = StringIO()
    call_command("tick_recurring", stdout=stdout)
    # No schedules → nothing happens, but the command exits cleanly.
    assert "tick_recurring" in stdout.getvalue()


@pytest.mark.django_db
def test_tick_command_handles_february_boundary_in_next_advance() -> None:
    """Day-31 monthly on Jan 31 → fires Jan 31, next advances to Feb 28."""
    schedule = RecurringScheduleFactory(
        schedule_kind="monthly",
        day_of_month=31,
        next_dispatch_at=date(2026, 1, 31),
    )
    call_command("tick_recurring", "--date", "2026-01-31", stdout=StringIO())
    schedule.refresh_from_db()
    assert schedule.last_dispatched_on == date(2026, 1, 31)
    assert schedule.next_dispatch_at == date(2026, 2, 28)


@pytest.mark.django_db
def test_tick_command_rejects_bad_date_flag() -> None:
    from django.core.management.base import CommandError

    with pytest.raises(CommandError):
        call_command("tick_recurring", "--date", "not-a-date")
