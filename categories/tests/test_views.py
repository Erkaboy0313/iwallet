"""Epic 3 — view-layer integration tests (Story 3.1 + Story 3.2)."""

from decimal import Decimal

import pytest
from django.core.management import call_command
from django.test import Client, override_settings
from django.urls import reverse

from accounts.tests.test_services import BOT_TOKEN, _make_init_data
from categories.models import Category, CategoryHide
from categories.tests.factories import CategoryFactory
from transactions.models import Transaction
from transactions.tests.factories import UserFactory


def _init_data(user_id: int = 7) -> str:
    return _make_init_data(user_id=user_id)


# ---------- list / management page ----------


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_list_view_renders_grouped_categories() -> None:
    call_command("loaddata", "categories/fixtures/preset_categories.json", verbosity=0)
    client = Client()
    response = client.get(
        reverse("categories:list"),
        headers={"X-Telegram-InitData": _init_data()},
    )
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    assert "Kirim kategoriyalari" in body
    assert "Chiqim kategoriyalari" in body
    # A preset slug should appear.
    assert "Taxi" in body
    assert "Yangi kategoriya" in body


@pytest.mark.django_db
def test_list_view_requires_auth() -> None:
    response = Client().get(reverse("categories:list"))
    assert response.status_code == 401


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_list_view_returns_partial_for_htmx() -> None:
    call_command("loaddata", "categories/fixtures/preset_categories.json", verbosity=0)
    client = Client()
    response = client.get(
        reverse("categories:list"),
        headers={"X-Telegram-InitData": _init_data(), "HX-Request": "true"},
    )
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    # Partial — no <html> shell.
    assert "<!DOCTYPE" not in body
    assert 'id="category-list"' in body


# ---------- create ----------


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_create_view_get_renders_form() -> None:
    response = Client().get(
        reverse("categories:create"),
        headers={"X-Telegram-InitData": _init_data()},
    )
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    assert "Yangi kategoriya" in body
    assert 'name="name"' in body


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_create_view_post_persists_and_returns_list_partial() -> None:
    call_command("loaddata", "categories/fixtures/preset_categories.json", verbosity=0)
    client = Client()
    response = client.post(
        reverse("categories:create"),
        data={"type": "expense", "name": "Trening", "emoji": "🏋"},
        headers={"X-Telegram-InitData": _init_data(user_id=42)},
    )
    assert response.status_code == 200
    assert Category.objects.filter(user__telegram_id=42, slug="trening").exists()
    assert "HX-Trigger" in response.headers
    assert "qo'shildi" in response.headers["HX-Trigger"]
    body = response.content.decode("utf-8")
    assert "Trening" in body


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_create_view_post_invalid_returns_422() -> None:
    client = Client()
    response = client.post(
        reverse("categories:create"),
        data={"type": "expense", "name": "", "emoji": "📌"},
        headers={"X-Telegram-InitData": _init_data()},
    )
    assert response.status_code == 422
    assert Category.objects.filter(user__telegram_id=7).count() == 0


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_create_view_post_duplicate_returns_422_with_error_message() -> None:
    client = Client()
    init = _init_data(user_id=42)
    client.post(
        reverse("categories:create"),
        data={"type": "expense", "name": "Sport", "emoji": "📌"},
        headers={"X-Telegram-InitData": init},
    )
    response = client.post(
        reverse("categories:create"),
        data={"type": "expense", "name": "Sport", "emoji": "📌"},
        headers={"X-Telegram-InitData": init},
    )
    assert response.status_code == 422
    body = response.content.decode("utf-8")
    assert "allaqachon mavjud" in body


# ---------- edit ----------


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_edit_view_get_prefills_form() -> None:
    user = UserFactory(telegram_id=7)
    cat = CategoryFactory(user=user, type="expense", slug="trening", name="Trening")
    response = Client().get(
        reverse("categories:edit", kwargs={"category_id": cat.id}),
        headers={"X-Telegram-InitData": _init_data()},
    )
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    assert "Trening" in body


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_edit_view_post_updates_category() -> None:
    user = UserFactory(telegram_id=7)
    cat = CategoryFactory(user=user, type="expense", slug="trening", name="Trening")
    response = Client().post(
        reverse("categories:edit", kwargs={"category_id": cat.id}),
        data={"type": "expense", "name": "Sport", "emoji": "🏀"},
        headers={"X-Telegram-InitData": _init_data()},
    )
    assert response.status_code == 200
    cat.refresh_from_db()
    assert cat.name == "Sport"
    assert cat.emoji == "🏀"


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_edit_view_404_for_other_users_category() -> None:
    other = UserFactory(telegram_id=99)
    cat = CategoryFactory(user=other, type="expense", slug="trening", name="Trening")
    response = Client().get(
        reverse("categories:edit", kwargs={"category_id": cat.id}),
        headers={"X-Telegram-InitData": _init_data(user_id=7)},
    )
    assert response.status_code == 404


# ---------- delete ----------


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_delete_view_get_renders_confirmation() -> None:
    user = UserFactory(telegram_id=7)
    cat = CategoryFactory(user=user, type="expense", slug="trening", name="Trening")
    response = Client().get(
        reverse("categories:delete", kwargs={"category_id": cat.id}),
        headers={"X-Telegram-InitData": _init_data()},
    )
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    assert "o'chirasizmi" in body
    assert "Boshqa" in body


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_delete_view_post_deletes_and_migrates_transactions() -> None:
    call_command("loaddata", "categories/fixtures/preset_categories.json", verbosity=0)
    user = UserFactory(telegram_id=7)
    cat = CategoryFactory(user=user, type="expense", slug="trening", name="Trening")
    tx = Transaction.objects.create(
        user=user,
        type="expense",
        amount=Decimal("1000"),
        currency="UZS",
        date="2026-06-25",
        category=cat,
    )
    response = Client().post(
        reverse("categories:delete", kwargs={"category_id": cat.id}),
        headers={"X-Telegram-InitData": _init_data()},
    )
    assert response.status_code == 200
    assert not Category.objects.filter(id=cat.id).exists()
    tx.refresh_from_db()
    assert tx.category is not None and tx.category.slug == "boshqa"


# ---------- toggle hide ----------


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_toggle_hide_view_hides_preset_for_user() -> None:
    call_command("loaddata", "categories/fixtures/preset_categories.json", verbosity=0)
    preset = Category.objects.filter(user__isnull=True, slug="taxi", type="expense").first()
    response = Client().post(
        reverse("categories:toggle_hide", kwargs={"category_id": preset.id}),
        headers={"X-Telegram-InitData": _init_data(user_id=42)},
    )
    assert response.status_code == 200
    assert CategoryHide.objects.filter(user__telegram_id=42, category=preset).exists()


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_toggle_hide_view_404_on_custom_category() -> None:
    """View only matches user__isnull=True — custom categories shouldn't hit it."""
    user = UserFactory(telegram_id=7)
    custom = CategoryFactory(user=user, type="expense", slug="trening", name="Trening")
    response = Client().post(
        reverse("categories:toggle_hide", kwargs={"category_id": custom.id}),
        headers={"X-Telegram-InitData": _init_data()},
    )
    assert response.status_code == 404
