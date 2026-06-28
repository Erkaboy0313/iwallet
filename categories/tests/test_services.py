"""Epic 3 / Story 3.1 — category service-layer invariants."""

from decimal import Decimal

import pytest
from django.core.management import call_command

from categories.exceptions import (
    CannotEditPresetError,
    CannotHideCustomError,
    DuplicateCategoryError,
    InvalidCategoryNameError,
)
from categories.models import Category, CategoryHide
from categories.services import (
    create_category,
    delete_category,
    toggle_hide_preset,
    update_category,
)
from categories.tests.factories import CategoryFactory
from transactions.models import Transaction
from transactions.tests.factories import UserFactory

# ---------- create_category ----------


@pytest.mark.django_db
def test_create_category_persists_with_slugified_name() -> None:
    user = UserFactory()
    cat = create_category(user=user, type_="expense", name="Trening", emoji="🏋")
    assert cat.user == user
    assert cat.type == "expense"
    assert cat.name == "Trening"
    assert cat.slug == "trening"
    assert cat.emoji == "🏋"


@pytest.mark.django_db
def test_create_category_strips_whitespace_from_name() -> None:
    user = UserFactory()
    cat = create_category(user=user, type_="expense", name="  Sport  ")
    assert cat.name == "Sport"


@pytest.mark.django_db
def test_create_category_rejects_empty_name() -> None:
    user = UserFactory()
    with pytest.raises(InvalidCategoryNameError):
        create_category(user=user, type_="expense", name="   ")


@pytest.mark.django_db
def test_create_category_rejects_too_long_name() -> None:
    user = UserFactory()
    with pytest.raises(InvalidCategoryNameError):
        create_category(user=user, type_="expense", name="x" * 200)


@pytest.mark.django_db
def test_create_category_rejects_duplicate_name_same_type() -> None:
    user = UserFactory()
    create_category(user=user, type_="expense", name="Trening")
    with pytest.raises(DuplicateCategoryError):
        create_category(user=user, type_="expense", name="trening")


@pytest.mark.django_db
def test_create_category_allows_same_name_in_different_types() -> None:
    user = UserFactory()
    a = create_category(user=user, type_="expense", name="Boshqa narsa")
    b = create_category(user=user, type_="income", name="Boshqa narsa")
    assert a.id != b.id


@pytest.mark.django_db
def test_create_category_disambiguates_slug_collisions() -> None:
    """slug() of two different names can collide — service must suffix."""
    user = UserFactory()
    CategoryFactory(user=user, type="expense", slug="trening", name="X")
    cat = create_category(user=user, type_="expense", name="Trening")
    assert cat.slug.startswith("trening")
    assert cat.slug != "trening"


@pytest.mark.django_db
def test_create_category_default_emoji_used_when_empty() -> None:
    user = UserFactory()
    cat = create_category(user=user, type_="expense", name="Sport", emoji="")
    assert cat.emoji == "📌"


# ---------- update_category ----------


@pytest.mark.django_db
def test_update_category_changes_name_and_slug() -> None:
    user = UserFactory()
    cat = create_category(user=user, type_="expense", name="Trening")
    updated = update_category(category=cat, name="Yangi nom", emoji=cat.emoji)
    assert updated.name == "Yangi nom"
    assert updated.slug == "yangi-nom"


@pytest.mark.django_db
def test_update_category_refuses_to_edit_preset() -> None:
    call_command("loaddata", "categories/fixtures/preset_categories.json", verbosity=0)
    preset = Category.objects.filter(user__isnull=True).first()
    with pytest.raises(CannotEditPresetError):
        update_category(category=preset, name="x", emoji="📌")


@pytest.mark.django_db
def test_update_category_rejects_duplicate_against_other_row() -> None:
    user = UserFactory()
    create_category(user=user, type_="expense", name="Trening")
    cat = create_category(user=user, type_="expense", name="Sport")
    with pytest.raises(DuplicateCategoryError):
        update_category(category=cat, name="Trening", emoji=cat.emoji)


@pytest.mark.django_db
def test_update_category_allows_no_op() -> None:
    user = UserFactory()
    cat = create_category(user=user, type_="expense", name="Trening", emoji="🏋")
    updated = update_category(category=cat, name="Trening", emoji="🏋")
    assert updated.name == "Trening"
    assert updated.slug == "trening"


# ---------- delete_category ----------


@pytest.mark.django_db
def test_delete_category_migrates_transactions_to_boshqa() -> None:
    call_command("loaddata", "categories/fixtures/preset_categories.json", verbosity=0)
    user = UserFactory()
    cat = create_category(user=user, type_="expense", name="Trening")
    tx = Transaction.objects.create(
        user=user,
        type="expense",
        amount=Decimal("1000"),
        currency="UZS",
        date="2026-06-25",
        category=cat,
    )
    delete_category(category=cat)
    tx.refresh_from_db()
    assert tx.category is not None
    assert tx.category.slug == "boshqa"
    assert tx.category.type == "expense"
    assert not Category.objects.filter(id=cat.id).exists()


@pytest.mark.django_db
def test_delete_category_falls_back_to_user_custom_boshqa() -> None:
    """If user has a custom Boshqa for that type, prefer it over the preset."""
    call_command("loaddata", "categories/fixtures/preset_categories.json", verbosity=0)
    user = UserFactory()
    my_boshqa = CategoryFactory(user=user, type="expense", slug="boshqa", name="Boshqa")
    cat = create_category(user=user, type_="expense", name="Sport")
    tx = Transaction.objects.create(
        user=user,
        type="expense",
        amount=Decimal("500"),
        currency="UZS",
        date="2026-06-25",
        category=cat,
    )
    delete_category(category=cat)
    tx.refresh_from_db()
    assert tx.category_id == my_boshqa.id


@pytest.mark.django_db
def test_delete_category_refuses_preset() -> None:
    call_command("loaddata", "categories/fixtures/preset_categories.json", verbosity=0)
    preset = Category.objects.filter(user__isnull=True).first()
    with pytest.raises(CannotEditPresetError):
        delete_category(category=preset)


@pytest.mark.django_db
def test_delete_category_does_not_touch_other_users_transactions() -> None:
    call_command("loaddata", "categories/fixtures/preset_categories.json", verbosity=0)
    alice = UserFactory()
    bob = UserFactory()
    alice_cat = create_category(user=alice, type_="expense", name="Sport")
    bob_cat = create_category(user=bob, type_="expense", name="Sport")
    bob_tx = Transaction.objects.create(
        user=bob,
        type="expense",
        amount=Decimal("1000"),
        currency="UZS",
        date="2026-06-25",
        category=bob_cat,
    )
    delete_category(category=alice_cat)
    bob_tx.refresh_from_db()
    # Bob's data untouched.
    assert bob_tx.category_id == bob_cat.id


# ---------- toggle_hide_preset ----------


@pytest.mark.django_db
def test_toggle_hide_preset_creates_hide_row_first_call() -> None:
    call_command("loaddata", "categories/fixtures/preset_categories.json", verbosity=0)
    user = UserFactory()
    preset = Category.objects.filter(user__isnull=True, slug="taxi", type="expense").first()
    hidden = toggle_hide_preset(user=user, category=preset)
    assert hidden is True
    assert CategoryHide.objects.filter(user=user, category=preset).exists()


@pytest.mark.django_db
def test_toggle_hide_preset_unhides_on_second_call() -> None:
    call_command("loaddata", "categories/fixtures/preset_categories.json", verbosity=0)
    user = UserFactory()
    preset = Category.objects.filter(user__isnull=True, slug="taxi", type="expense").first()
    toggle_hide_preset(user=user, category=preset)
    hidden = toggle_hide_preset(user=user, category=preset)
    assert hidden is False
    assert not CategoryHide.objects.filter(user=user, category=preset).exists()


@pytest.mark.django_db
def test_toggle_hide_preset_is_per_user() -> None:
    """User A hiding a preset must not affect user B."""
    call_command("loaddata", "categories/fixtures/preset_categories.json", verbosity=0)
    a = UserFactory()
    b = UserFactory()
    preset = Category.objects.filter(user__isnull=True, slug="taxi", type="expense").first()
    toggle_hide_preset(user=a, category=preset)
    assert CategoryHide.objects.filter(user=a, category=preset).exists()
    assert not CategoryHide.objects.filter(user=b, category=preset).exists()


@pytest.mark.django_db
def test_toggle_hide_preset_refuses_custom() -> None:
    user = UserFactory()
    custom = create_category(user=user, type_="expense", name="Sport")
    with pytest.raises(CannotHideCustomError):
        toggle_hide_preset(user=user, category=custom)
