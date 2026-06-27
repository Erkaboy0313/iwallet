"""Story 1.3 — Category model + preset seed + selectors."""

import pytest
from django.core.management import call_command
from django.db import IntegrityError, transaction as db_transaction

from categories.models import Category
from categories.selectors import categories_for, match_slug
from categories.tests.factories import CategoryFactory
from transactions.tests.factories import UserFactory

# ---------- Model invariants ----------


@pytest.mark.django_db
def test_user_null_means_preset() -> None:
    """user=NULL identifies a preset shipped via fixture."""
    preset = Category.objects.create(
        user=None, type="expense", slug="qahva_kafe", name="Qahva/kafe", emoji="☕"
    )
    assert preset.user_id is None
    assert preset.is_preset is True


@pytest.mark.django_db
def test_custom_category_belongs_to_user() -> None:
    user = UserFactory()
    cat = CategoryFactory(user=user, slug="trening", name="Trening")
    assert cat.user == user
    assert cat.is_preset is False


@pytest.mark.django_db
def test_slug_unique_per_user_and_type() -> None:
    user = UserFactory()
    CategoryFactory(user=user, type="expense", slug="taxi")
    with db_transaction.atomic(), pytest.raises(IntegrityError):
        CategoryFactory(user=user, type="expense", slug="taxi")


@pytest.mark.django_db
def test_same_slug_allowed_across_different_types() -> None:
    """`boshqa` can exist as both income and expense for the same user."""
    user = UserFactory()
    CategoryFactory(user=user, type="income", slug="boshqa")
    CategoryFactory(user=user, type="expense", slug="boshqa")
    assert Category.objects.filter(user=user, slug="boshqa").count() == 2


# ---------- Preset fixture ----------


@pytest.mark.django_db
def test_preset_fixture_loads_with_correct_counts() -> None:
    """Loading the fixture seeds the documented preset count."""
    call_command("loaddata", "categories/fixtures/preset_categories.json", verbosity=0)
    presets = Category.objects.filter(user__isnull=True)
    assert presets.filter(type="income").count() >= 5
    assert presets.filter(type="expense").count() >= 10
    # Every preset has a non-empty emoji + slug
    assert not presets.filter(emoji="").exists()
    assert not presets.filter(slug="").exists()


@pytest.mark.django_db
def test_preset_fixture_includes_canonical_slugs() -> None:
    call_command("loaddata", "categories/fixtures/preset_categories.json", verbosity=0)
    expected_expense = {"oziq_ovqat", "transport", "taxi", "qahva_kafe", "boshqa"}
    expected_income = {"oylik", "biznes", "boshqa"}
    expense_slugs = set(
        Category.objects.filter(user__isnull=True, type="expense").values_list("slug", flat=True)
    )
    income_slugs = set(
        Category.objects.filter(user__isnull=True, type="income").values_list("slug", flat=True)
    )
    assert expected_expense.issubset(expense_slugs)
    assert expected_income.issubset(income_slugs)


# ---------- categories_for selector ----------


@pytest.mark.django_db
def test_categories_for_returns_presets_plus_user_custom() -> None:
    call_command("loaddata", "categories/fixtures/preset_categories.json", verbosity=0)
    user = UserFactory()
    custom = CategoryFactory(user=user, type="expense", slug="qiziqarli", name="Qiziqarli")

    qs = categories_for(user, "expense")
    assert custom in qs
    # Presets included too
    assert qs.filter(user__isnull=True).count() >= 10


@pytest.mark.django_db
def test_categories_for_hides_user_hidden_presets() -> None:
    call_command("loaddata", "categories/fixtures/preset_categories.json", verbosity=0)
    user = UserFactory()
    preset = Category.objects.filter(user__isnull=True, type="expense", slug="taxi").first()
    assert preset is not None
    # User hides taxi via Hidden record (placeholder mechanism: hide via is_hidden on a copy)
    # For Story 1.3 we use a simple is_hidden flag on Category — preset's is_hidden is global,
    # so per-user hiding is done by creating a user-scoped hidden override OR via a separate
    # UserHiddenPreset table. Keep selector forgiving: filter on is_hidden=False.
    Category.objects.filter(slug="taxi", user__isnull=True).update(is_hidden=True)
    qs = categories_for(user, "expense")
    assert not qs.filter(slug="taxi", user__isnull=True).exists()


@pytest.mark.django_db
def test_categories_for_scope_is_per_type() -> None:
    call_command("loaddata", "categories/fixtures/preset_categories.json", verbosity=0)
    user = UserFactory()
    income_qs = categories_for(user, "income")
    expense_qs = categories_for(user, "expense")
    assert not income_qs.filter(type="expense").exists()
    assert not expense_qs.filter(type="income").exists()


# ---------- match_slug selector ----------


@pytest.mark.django_db
def test_match_slug_prefers_user_custom_over_preset() -> None:
    call_command("loaddata", "categories/fixtures/preset_categories.json", verbosity=0)
    user = UserFactory()
    custom = CategoryFactory(user=user, type="expense", slug="taxi", name="My Taxi")
    matched = match_slug(user, slug="taxi", type="expense")
    assert matched == custom


@pytest.mark.django_db
def test_match_slug_falls_back_to_preset() -> None:
    call_command("loaddata", "categories/fixtures/preset_categories.json", verbosity=0)
    user = UserFactory()
    matched = match_slug(user, slug="taxi", type="expense")
    assert matched is not None
    assert matched.user_id is None
    assert matched.slug == "taxi"


@pytest.mark.django_db
def test_match_slug_returns_none_when_unknown() -> None:
    user = UserFactory()
    matched = match_slug(user, slug="does-not-exist", type="expense")
    assert matched is None
