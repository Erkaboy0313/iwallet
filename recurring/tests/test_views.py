"""View-layer integration tests for recurring CRUD + prompt resolution."""

from datetime import date
from decimal import Decimal

import pytest
from django.test import Client, override_settings
from django.urls import reverse

from accounts.tests.test_services import BOT_TOKEN, _make_init_data
from recurring.models import RecurringSchedule
from recurring.tests.factories import RecurringScheduleFactory
from transactions.models import Transaction
from transactions.tests.factories import UserFactory


def _init_data(user_id: int = 7) -> str:
    return _make_init_data(user_id=user_id)


# ---------- list ----------


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_list_view_empty_state_when_no_schedules() -> None:
    response = Client().get(
        reverse("recurring:list"),
        headers={"X-Telegram-InitData": _init_data(user_id=42)},
    )
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    assert "Hozircha takrorlanuvchi yo'q" in body
    assert "Yangi takrorlanuvchi" in body


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_list_view_renders_user_schedules() -> None:
    user = UserFactory(telegram_id=7)
    RecurringScheduleFactory(user=user, name="Ijara")
    response = Client().get(
        reverse("recurring:list"),
        headers={"X-Telegram-InitData": _init_data()},
    )
    assert response.status_code == 200
    assert "Ijara" in response.content.decode("utf-8")


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_list_view_only_shows_own_schedules() -> None:
    user_a = UserFactory(telegram_id=7)
    user_b = UserFactory(telegram_id=99)
    RecurringScheduleFactory(user=user_a, name="MineAaa")
    RecurringScheduleFactory(user=user_b, name="TheirsBbb")
    body = (
        Client()
        .get(
            reverse("recurring:list"),
            headers={"X-Telegram-InitData": _init_data(user_id=7)},
        )
        .content.decode("utf-8")
    )
    assert "MineAaa" in body
    assert "TheirsBbb" not in body


@pytest.mark.django_db
def test_list_view_requires_auth() -> None:
    assert Client().get(reverse("recurring:list")).status_code == 401


# ---------- create ----------


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_create_view_get_renders_form() -> None:
    response = Client().get(
        reverse("recurring:create"),
        headers={"X-Telegram-InitData": _init_data()},
    )
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    assert "Yangi takrorlanuvchi" in body
    assert 'name="name"' in body
    assert 'name="amount"' in body


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_create_view_post_redirects_to_list_and_persists() -> None:
    response = Client().post(
        reverse("recurring:create"),
        data={
            "type": "expense",
            "name": "Ijara",
            "amount": "2000000",
            "currency": "UZS",
            "schedule_kind": "monthly",
            "day_of_month": "1",
        },
        headers={"X-Telegram-InitData": _init_data(user_id=42)},
    )
    assert response.status_code == 302
    assert response["Location"] == reverse("recurring:list")
    s = RecurringSchedule.objects.get(user__telegram_id=42)
    assert s.name == "Ijara"
    assert s.schedule_kind == "monthly"
    assert s.day_of_month == 1


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_create_view_post_daily_schedule() -> None:
    response = Client().post(
        reverse("recurring:create"),
        data={
            "type": "expense",
            "name": "Metro",
            "amount": "2000",
            "currency": "UZS",
            "schedule_kind": "daily",
        },
        headers={"X-Telegram-InitData": _init_data(user_id=42)},
    )
    assert response.status_code == 302
    s = RecurringSchedule.objects.get(user__telegram_id=42)
    assert s.schedule_kind == "daily"
    assert s.day_of_month is None
    assert s.day_of_week is None


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_create_view_post_invalid_amount_returns_422() -> None:
    response = Client().post(
        reverse("recurring:create"),
        data={
            "type": "expense",
            "name": "Ijara",
            "amount": "0",
            "currency": "UZS",
            "schedule_kind": "monthly",
            "day_of_month": "1",
        },
        headers={"X-Telegram-InitData": _init_data()},
    )
    assert response.status_code == 422
    assert RecurringSchedule.objects.count() == 0


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_create_view_post_weekly_without_dow_returns_422() -> None:
    response = Client().post(
        reverse("recurring:create"),
        data={
            "type": "expense",
            "name": "Sport",
            "amount": "50000",
            "currency": "UZS",
            "schedule_kind": "weekly",
        },
        headers={"X-Telegram-InitData": _init_data()},
    )
    assert response.status_code == 422


# ---------- edit ----------


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_edit_view_get_prefills_form() -> None:
    user = UserFactory(telegram_id=7)
    schedule = RecurringScheduleFactory(user=user, name="Ijara")
    response = Client().get(
        reverse("recurring:edit", kwargs={"schedule_id": schedule.id}),
        headers={"X-Telegram-InitData": _init_data()},
    )
    assert response.status_code == 200
    assert "Ijara" in response.content.decode("utf-8")


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_edit_view_post_updates_and_redirects() -> None:
    user = UserFactory(telegram_id=7)
    schedule = RecurringScheduleFactory(user=user, name="Ijara")
    response = Client().post(
        reverse("recurring:edit", kwargs={"schedule_id": schedule.id}),
        data={
            "type": "expense",
            "name": "Yangi Ijara",
            "amount": "2500000",
            "currency": "UZS",
            "schedule_kind": "monthly",
            "day_of_month": "5",
        },
        headers={"X-Telegram-InitData": _init_data()},
    )
    assert response.status_code == 302
    schedule.refresh_from_db()
    assert schedule.name == "Yangi Ijara"
    assert schedule.day_of_month == 5


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_edit_view_404_for_other_users_schedule() -> None:
    other = UserFactory(telegram_id=99)
    schedule = RecurringScheduleFactory(user=other)
    response = Client().get(
        reverse("recurring:edit", kwargs={"schedule_id": schedule.id}),
        headers={"X-Telegram-InitData": _init_data(user_id=7)},
    )
    assert response.status_code == 404


# ---------- delete ----------


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_delete_view_get_renders_confirmation() -> None:
    user = UserFactory(telegram_id=7)
    schedule = RecurringScheduleFactory(user=user, name="Ijara")
    response = Client().get(
        reverse("recurring:delete", kwargs={"schedule_id": schedule.id}),
        headers={"X-Telegram-InitData": _init_data()},
    )
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    assert "Ijara" in body
    assert "o'chir" in body.lower()


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_delete_view_post_removes_and_redirects() -> None:
    user = UserFactory(telegram_id=7)
    schedule = RecurringScheduleFactory(user=user)
    response = Client().post(
        reverse("recurring:delete", kwargs={"schedule_id": schedule.id}),
        headers={"X-Telegram-InitData": _init_data()},
    )
    assert response.status_code == 302
    assert not RecurringSchedule.objects.filter(pk=schedule.pk).exists()


# ---------- toggle ----------


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_toggle_view_pauses_active_schedule() -> None:
    user = UserFactory(telegram_id=7)
    schedule = RecurringScheduleFactory(user=user, is_active=True)
    response = Client().post(
        reverse("recurring:toggle", kwargs={"schedule_id": schedule.id}),
        headers={"X-Telegram-InitData": _init_data(), "HX-Request": "true"},
    )
    assert response.status_code == 200
    schedule.refresh_from_db()
    assert schedule.is_active is False


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_toggle_view_resumes_paused_schedule() -> None:
    user = UserFactory(telegram_id=7)
    schedule = RecurringScheduleFactory(user=user, is_active=False)
    response = Client().post(
        reverse("recurring:toggle", kwargs={"schedule_id": schedule.id}),
        headers={"X-Telegram-InitData": _init_data(), "HX-Request": "true"},
    )
    assert response.status_code == 200
    schedule.refresh_from_db()
    assert schedule.is_active is True


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_toggle_view_404_on_other_user() -> None:
    other = UserFactory(telegram_id=99)
    schedule = RecurringScheduleFactory(user=other)
    response = Client().post(
        reverse("recurring:toggle", kwargs={"schedule_id": schedule.id}),
        headers={"X-Telegram-InitData": _init_data(user_id=7)},
    )
    assert response.status_code == 404


# ---------- prompt resolution ----------


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_prompt_confirm_creates_transaction_and_advances() -> None:
    user = UserFactory(telegram_id=7)
    schedule = RecurringScheduleFactory(
        user=user,
        schedule_kind="daily",
        day_of_month=None,
        day_of_week=None,
        amount=Decimal("2000"),
    )
    response = Client().post(
        reverse("recurring:prompt_confirm", kwargs={"schedule_id": schedule.id}),
        headers={"X-Telegram-InitData": _init_data()},
    )
    assert response.status_code == 302
    assert Transaction.objects.filter(user=user).count() == 1
    schedule.refresh_from_db()
    assert schedule.last_dispatched_on is not None


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_prompt_confirm_with_edited_amount_uses_override() -> None:
    user = UserFactory(telegram_id=7)
    schedule = RecurringScheduleFactory(
        user=user,
        schedule_kind="monthly",
        day_of_month=1,
        amount=Decimal("100000"),
    )
    Client().post(
        reverse("recurring:prompt_confirm", kwargs={"schedule_id": schedule.id}),
        data={"amount": "110000", "save_amount": "1"},
        headers={"X-Telegram-InitData": _init_data()},
    )
    tx = Transaction.objects.get(user=user)
    assert tx.amount == Decimal("110000")
    schedule.refresh_from_db()
    assert schedule.amount == Decimal("110000")  # persisted as new default


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_prompt_skip_advances_without_transaction() -> None:
    user = UserFactory(telegram_id=7)
    schedule = RecurringScheduleFactory(
        user=user,
        schedule_kind="daily",
        day_of_month=None,
        day_of_week=None,
    )
    response = Client().post(
        reverse("recurring:prompt_skip", kwargs={"schedule_id": schedule.id}),
        headers={"X-Telegram-InitData": _init_data()},
    )
    assert response.status_code == 302
    assert Transaction.objects.count() == 0
    schedule.refresh_from_db()
    assert schedule.last_dispatched_on is not None


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_prompt_defer_sets_defer_until_tomorrow() -> None:
    user = UserFactory(telegram_id=7)
    today = date.today()
    schedule = RecurringScheduleFactory(
        user=user,
        schedule_kind="daily",
        day_of_month=None,
        day_of_week=None,
        next_dispatch_at=today,
    )
    response = Client().post(
        reverse("recurring:prompt_defer", kwargs={"schedule_id": schedule.id}),
        headers={"X-Telegram-InitData": _init_data()},
    )
    assert response.status_code == 302
    schedule.refresh_from_db()
    assert schedule.defer_until is not None
    assert schedule.next_dispatch_at == today  # cursor not advanced


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_prompt_confirm_404_on_other_user() -> None:
    other = UserFactory(telegram_id=99)
    schedule = RecurringScheduleFactory(user=other)
    response = Client().post(
        reverse("recurring:prompt_confirm", kwargs={"schedule_id": schedule.id}),
        headers={"X-Telegram-InitData": _init_data(user_id=7)},
    )
    assert response.status_code == 404


# ---------- home integration ----------


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_home_renders_prompt_card_for_due_schedule() -> None:
    user = UserFactory(telegram_id=7, onboarded_at=date(2026, 1, 1))
    schedule = RecurringScheduleFactory(
        user=user,
        name="Metro",
        schedule_kind="daily",
        day_of_month=None,
        day_of_week=None,
        next_dispatch_at=date.today(),
    )
    response = Client().get(
        reverse("core:home_content"),
        headers={"X-Telegram-InitData": _init_data()},
    )
    body = response.content.decode("utf-8")
    assert response.status_code == 200
    assert "Metro" in body
    assert "Bugun" in body
    assert reverse("recurring:prompt_confirm", kwargs={"schedule_id": schedule.id}) in body


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_home_hides_prompt_for_future_dispatch() -> None:
    user = UserFactory(telegram_id=7, onboarded_at=date(2026, 1, 1))
    RecurringScheduleFactory(
        user=user,
        name="Future",
        schedule_kind="monthly",
        day_of_month=28,
        next_dispatch_at=date(2099, 12, 31),
    )
    response = Client().get(
        reverse("core:home_content"),
        headers={"X-Telegram-InitData": _init_data()},
    )
    body = response.content.decode("utf-8")
    assert "Future" not in body
