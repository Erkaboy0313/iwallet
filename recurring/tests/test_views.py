"""Epic 7 / Story 7.2 — view-layer integration tests for recurring CRUD."""

from datetime import date

import pytest
from django.test import Client, override_settings
from django.urls import reverse

from accounts.tests.test_services import BOT_TOKEN, _make_init_data
from recurring.models import RecurringSchedule
from recurring.tests.factories import RecurringScheduleFactory
from transactions.tests.factories import UserFactory


def _init_data(user_id: int = 7) -> str:
    return _make_init_data(user_id=user_id)


# ---------- list ----------


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_list_view_empty_state_when_no_schedules() -> None:
    client = Client()
    response = client.get(
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
    body = response.content.decode("utf-8")
    assert "Ijara" in body


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_list_view_only_shows_own_schedules() -> None:
    user_a = UserFactory(telegram_id=7)
    user_b = UserFactory(telegram_id=99)
    RecurringScheduleFactory(user=user_a, name="MineAaa")
    RecurringScheduleFactory(user=user_b, name="TheirsBbb")
    response = Client().get(
        reverse("recurring:list"),
        headers={"X-Telegram-InitData": _init_data(user_id=7)},
    )
    body = response.content.decode("utf-8")
    assert "MineAaa" in body
    assert "TheirsBbb" not in body


@pytest.mark.django_db
def test_list_view_requires_auth() -> None:
    response = Client().get(reverse("recurring:list"))
    assert response.status_code == 401


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_list_view_returns_partial_for_htmx() -> None:
    response = Client().get(
        reverse("recurring:list"),
        headers={"X-Telegram-InitData": _init_data(), "HX-Request": "true"},
    )
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    assert "<!DOCTYPE" not in body
    assert 'id="recurring-list"' in body


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
def test_create_view_post_persists_schedule() -> None:
    client = Client()
    response = client.post(
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
    assert response.status_code == 200
    schedules = RecurringSchedule.objects.filter(user__telegram_id=42)
    assert schedules.count() == 1
    s = schedules.first()
    assert s.name == "Ijara"
    assert s.schedule_kind == "monthly"
    assert s.day_of_month == 1
    assert "HX-Trigger" in response.headers
    assert "qo'shildi" in response.headers["HX-Trigger"]


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
    body = response.content.decode("utf-8")
    assert "Ijara" in body


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_edit_view_post_updates_schedule() -> None:
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
    assert response.status_code == 200
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
def test_delete_view_post_removes_schedule() -> None:
    user = UserFactory(telegram_id=7)
    schedule = RecurringScheduleFactory(user=user)
    response = Client().post(
        reverse("recurring:delete", kwargs={"schedule_id": schedule.id}),
        headers={"X-Telegram-InitData": _init_data()},
    )
    assert response.status_code == 200
    assert not RecurringSchedule.objects.filter(pk=schedule.pk).exists()


# ---------- toggle ----------


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_toggle_view_pauses_active_schedule() -> None:
    user = UserFactory(telegram_id=7)
    schedule = RecurringScheduleFactory(user=user, is_active=True)
    response = Client().post(
        reverse("recurring:toggle", kwargs={"schedule_id": schedule.id}),
        headers={"X-Telegram-InitData": _init_data()},
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
        headers={"X-Telegram-InitData": _init_data()},
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


# ---------- balance hero link discoverability ----------


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_balance_hero_does_not_render_recurring_link_after_v0_5() -> None:
    """Sprint v0.5 redesign moved Kategoriyalar/Takrorlanuvchi off Home — they
    live on the Settings hub at /app/settings/ (Phase 4). The recurring page
    is still reachable via direct URL; we just don't surface it on Home.
    """
    UserFactory(telegram_id=7, onboarded_at=date(2026, 1, 1))
    response = Client().get(
        reverse("core:home_content"),
        headers={"X-Telegram-InitData": _init_data()},
    )
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    assert reverse("recurring:list") not in body
    assert "Takrorlanuvchi" not in body
