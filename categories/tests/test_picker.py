"""Epic 3 / Story 3.2 — category picker bottom-sheet partial."""

from decimal import Decimal

import pytest
from django.core.management import call_command
from django.test import Client, override_settings
from django.urls import reverse

from accounts.models import User
from accounts.tests.test_services import BOT_TOKEN, _make_init_data
from categories.models import Category, CategoryHide
from transactions.models import Transaction
from transactions.tests.factories import UserFactory


def _init_data(user_id: int = 7) -> str:
    return _make_init_data(user_id=user_id)


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_picker_renders_grid_of_chips() -> None:
    call_command("loaddata", "categories/fixtures/preset_categories.json", verbosity=0)
    response = Client().get(
        reverse("categories:picker") + "?type=expense",
        headers={"X-Telegram-InitData": _init_data()},
    )
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    # 4-col grid for mobile.
    assert "grid-cols-4" in body
    # A preset chip is rendered with its emoji.
    assert "Taxi" in body
    assert "🚕" in body


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_picker_defaults_to_expense_when_type_missing() -> None:
    call_command("loaddata", "categories/fixtures/preset_categories.json", verbosity=0)
    response = Client().get(
        reverse("categories:picker"),
        headers={"X-Telegram-InitData": _init_data()},
    )
    body = response.content.decode("utf-8")
    assert response.status_code == 200
    # Income-only "Oylik" should NOT be present.
    assert "Oylik" not in body


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_picker_renders_income_categories_when_requested() -> None:
    call_command("loaddata", "categories/fixtures/preset_categories.json", verbosity=0)
    response = Client().get(
        reverse("categories:picker") + "?type=income",
        headers={"X-Telegram-InitData": _init_data()},
    )
    body = response.content.decode("utf-8")
    assert response.status_code == 200
    assert "Oylik" in body


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_picker_orders_by_user_frequency_descending() -> None:
    """Most-used category should render before less-used ones (AC 3.2)."""
    call_command("loaddata", "categories/fixtures/preset_categories.json", verbosity=0)
    user = UserFactory(telegram_id=7)
    taxi = Category.objects.filter(user__isnull=True, slug="taxi", type="expense").first()
    for _ in range(5):
        Transaction.objects.create(
            user=user,
            type="expense",
            amount=Decimal("1000"),
            currency="UZS",
            date="2026-06-25",
            category=taxi,
        )
    response = Client().get(
        reverse("categories:picker") + "?type=expense",
        headers={"X-Telegram-InitData": _init_data()},
    )
    body = response.content.decode("utf-8")
    # "Taxi" should appear earlier in the rendered HTML than other expense names.
    taxi_pos = body.find("Taxi")
    food_pos = body.find("Oziq")
    assert taxi_pos != -1 and food_pos != -1
    assert taxi_pos < food_pos


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_picker_places_boshqa_last() -> None:
    """'Boshqa' is rendered last regardless of frequency."""
    call_command("loaddata", "categories/fixtures/preset_categories.json", verbosity=0)
    user = UserFactory(telegram_id=7)
    boshqa = Category.objects.filter(user__isnull=True, slug="boshqa", type="expense").first()
    # Use Boshqa heavily — it would otherwise jump to top.
    for _ in range(20):
        Transaction.objects.create(
            user=user,
            type="expense",
            amount=Decimal("1000"),
            currency="UZS",
            date="2026-06-25",
            category=boshqa,
        )
    response = Client().get(
        reverse("categories:picker") + "?type=expense",
        headers={"X-Telegram-InitData": _init_data()},
    )
    body = response.content.decode("utf-8")
    boshqa_pos = body.rfind('data-slug="boshqa"')
    # No other slug should appear AFTER Boshqa.
    after_boshqa = body[boshqa_pos:]
    assert 'data-slug="taxi"' not in after_boshqa


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_picker_excludes_user_hidden_presets() -> None:
    call_command("loaddata", "categories/fixtures/preset_categories.json", verbosity=0)
    client = Client()
    # First request provisions the user via middleware; then we hide a preset
    # for that exact user before requesting the picker.
    client.get(
        reverse("categories:picker") + "?type=expense",
        headers={"X-Telegram-InitData": _init_data()},
    )
    user = User.objects.get(telegram_id=7)
    taxis = Category.objects.filter(user__isnull=True, slug="taxi", type="expense")
    for taxi in taxis:
        CategoryHide.objects.create(user=user, category=taxi)
    response = client.get(
        reverse("categories:picker") + "?type=expense",
        headers={"X-Telegram-InitData": _init_data()},
    )
    assert 'data-slug="taxi"' not in response.content.decode("utf-8")


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_picker_target_field_threaded_into_template() -> None:
    """Caller passes target=<field-id>; picker chip handlers write into it."""
    call_command("loaddata", "categories/fixtures/preset_categories.json", verbosity=0)
    response = Client().get(
        reverse("categories:picker") + "?type=expense&target=id_custom_target",
        headers={"X-Telegram-InitData": _init_data()},
    )
    body = response.content.decode("utf-8")
    assert "getElementById('id_custom_target')" in body
