"""Epic 3 — selector behavior: per-user hide + usage-frequency ordering."""

from decimal import Decimal

import pytest
from django.core.management import call_command

from categories.models import Category, CategoryHide
from categories.selectors import categories_for, categories_for_settings
from categories.tests.factories import CategoryFactory
from transactions.models import Transaction
from transactions.tests.factories import UserFactory


@pytest.mark.django_db
def test_categories_for_excludes_user_hidden_preset() -> None:
    """A preset hidden by user A is excluded for A but visible to B."""
    call_command("loaddata", "categories/fixtures/preset_categories.json", verbosity=0)
    a = UserFactory()
    b = UserFactory()
    # The fixture + migration both seed presets — hide ALL matching preset rows
    # for user A so the assertion is unambiguous.
    presets = Category.objects.filter(user__isnull=True, slug="taxi", type="expense")
    for preset in presets:
        CategoryHide.objects.create(user=a, category=preset)

    a_qs = categories_for(a, "expense")
    b_qs = categories_for(b, "expense")
    assert not a_qs.filter(slug="taxi", user__isnull=True).exists()
    assert b_qs.filter(slug="taxi", user__isnull=True).exists()


@pytest.mark.django_db
def test_categories_for_orders_by_usage_frequency_descending() -> None:
    """Most-used category should appear first; ties broken alphabetically."""
    call_command("loaddata", "categories/fixtures/preset_categories.json", verbosity=0)
    user = UserFactory()
    taxi = Category.objects.filter(user__isnull=True, slug="taxi", type="expense").first()
    food = Category.objects.filter(user__isnull=True, slug="oziq_ovqat", type="expense").first()
    # 5 taxi uses, 2 food uses.
    for _ in range(5):
        Transaction.objects.create(
            user=user,
            type="expense",
            amount=Decimal("1000"),
            currency="UZS",
            date="2026-06-25",
            category=taxi,
        )
    for _ in range(2):
        Transaction.objects.create(
            user=user,
            type="expense",
            amount=Decimal("1000"),
            currency="UZS",
            date="2026-06-25",
            category=food,
        )

    ordered = list(categories_for(user, "expense"))
    assert ordered[0].id == taxi.id
    # food is second among the categories with usage
    food_idx = next(i for i, c in enumerate(ordered) if c.id == food.id)
    taxi_idx = next(i for i, c in enumerate(ordered) if c.id == taxi.id)
    assert taxi_idx < food_idx


@pytest.mark.django_db
def test_categories_for_ignores_other_users_usage() -> None:
    """Frequency must be scoped to the requesting user only."""
    call_command("loaddata", "categories/fixtures/preset_categories.json", verbosity=0)
    a = UserFactory()
    b = UserFactory()
    taxi = Category.objects.filter(user__isnull=True, slug="taxi", type="expense").first()
    # Bob uses taxi a lot.
    for _ in range(10):
        Transaction.objects.create(
            user=b,
            type="expense",
            amount=Decimal("1000"),
            currency="UZS",
            date="2026-06-25",
            category=taxi,
        )
    # Alice never used it — so for Alice, taxi has usage_count=0.
    a_ordered = list(categories_for(a, "expense"))
    taxi_for_alice = next(c for c in a_ordered if c.id == taxi.id)
    assert taxi_for_alice.usage_count == 0


@pytest.mark.django_db
def test_categories_for_ignores_soft_deleted_transactions() -> None:
    call_command("loaddata", "categories/fixtures/preset_categories.json", verbosity=0)
    user = UserFactory()
    taxi = Category.objects.filter(user__isnull=True, slug="taxi", type="expense").first()
    Transaction.objects.create(
        user=user,
        type="expense",
        amount=Decimal("1000"),
        currency="UZS",
        date="2026-06-25",
        category=taxi,
        is_deleted=True,
    )
    qs = list(categories_for(user, "expense"))
    taxi_row = next(c for c in qs if c.id == taxi.id)
    assert taxi_row.usage_count == 0


@pytest.mark.django_db
def test_categories_for_settings_marks_hidden_for_user() -> None:
    """Settings selector keeps hidden rows visible but flags them."""
    call_command("loaddata", "categories/fixtures/preset_categories.json", verbosity=0)
    user = UserFactory()
    preset = Category.objects.filter(user__isnull=True, slug="taxi", type="expense").first()
    CategoryHide.objects.create(user=user, category=preset)

    rows = categories_for_settings(user, "expense")
    taxi_row = next((c for c in rows if c.id == preset.id), None)
    assert taxi_row is not None  # Still listed — settings UI lets user unhide.
    assert taxi_row.is_hidden_for_user is True


@pytest.mark.django_db
def test_categories_for_settings_includes_custom_and_marks_unhidden() -> None:
    user = UserFactory()
    cat = CategoryFactory(user=user, type="expense", slug="trening", name="Trening")
    rows = categories_for_settings(user, "expense")
    custom_row = next((c for c in rows if c.id == cat.id), None)
    assert custom_row is not None
    assert custom_row.is_hidden_for_user is False
