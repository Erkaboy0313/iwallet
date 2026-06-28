"""Write-side business logic for Category (Epic 3).

Per project-context: services own invariants, views only orchestrate. All writes
are atomic; raises domain exceptions (never bare Exception).
"""

from django.db import transaction as db_transaction
from django.utils.text import slugify

from accounts.models import User

from .exceptions import (
    CannotEditPresetError,
    CannotHideCustomError,
    DuplicateCategoryError,
    InvalidCategoryNameError,
)
from .models import Category, CategoryHide
from .selectors import match_slug

# Slug fallback used when slugify() returns an empty string (e.g., emoji-only name).
_EMPTY_SLUG_FALLBACK = "kategoriya"
# The "Boshqa" preset slug — used as the migration target for deleted custom categories.
BOSHQA_SLUG = "boshqa"


def _make_slug(user: User, *, type_: str, name: str, exclude_id: int | None = None) -> str:
    """Build a unique-per-(user, type) slug from `name`.

    `slugify` strips diacritics and lowercases — for o'zbek text we keep it
    simple and disambiguate with a numeric suffix when collisions happen.
    """
    base = slugify(name) or _EMPTY_SLUG_FALLBACK
    candidate = base
    suffix = 2
    while True:
        qs = Category.objects.filter(user=user, type=type_, slug=candidate)
        if exclude_id is not None:
            qs = qs.exclude(id=exclude_id)
        if not qs.exists():
            return candidate
        candidate = f"{base}-{suffix}"
        suffix += 1


@db_transaction.atomic
def create_category(
    *,
    user: User,
    type_: str,
    name: str,
    emoji: str = "📌",
) -> Category:
    """Create a custom category for the user.

    Slug auto-generated; duplicate (case-insensitive) name within the same
    (user, type) raises DuplicateCategoryError so the form can show a clean
    inline error.
    """
    name = (name or "").strip()
    if not name:
        raise InvalidCategoryNameError("Kategoriya nomini kiriting.")
    if len(name) > 64:
        raise InvalidCategoryNameError("Kategoriya nomi juda uzun (64 belgidan ortiq).")

    duplicate = Category.objects.filter(user=user, type=type_, name__iexact=name).first()
    if duplicate is not None:
        raise DuplicateCategoryError("Bu nom bilan kategoriya allaqachon mavjud.")

    slug = _make_slug(user, type_=type_, name=name)
    return Category.objects.create(
        user=user,
        type=type_,
        slug=slug,
        name=name,
        emoji=emoji or "📌",
    )


@db_transaction.atomic
def update_category(
    *,
    category: Category,
    name: str,
    emoji: str,
    type_: str | None = None,
) -> Category:
    """Update a custom category. Presets are immutable per user."""
    if category.is_preset:
        raise CannotEditPresetError("Preset kategoriyani o'zgartirib bo'lmaydi.")
    name = (name or "").strip()
    if not name:
        raise InvalidCategoryNameError("Kategoriya nomini kiriting.")
    if len(name) > 64:
        raise InvalidCategoryNameError("Kategoriya nomi juda uzun (64 belgidan ortiq).")

    new_type = type_ or category.type
    duplicate = (
        Category.objects.filter(user=category.user, type=new_type, name__iexact=name)
        .exclude(id=category.id)
        .first()
    )
    if duplicate is not None:
        raise DuplicateCategoryError("Bu nom bilan kategoriya allaqachon mavjud.")

    changed_fields: list[str] = []
    if category.name != name:
        category.name = name
        category.slug = _make_slug(category.user, type_=new_type, name=name, exclude_id=category.id)
        changed_fields.extend(["name", "slug"])
    if category.emoji != emoji:
        category.emoji = emoji or "📌"
        changed_fields.append("emoji")
    if category.type != new_type:
        category.type = new_type
        changed_fields.append("type")
    if changed_fields:
        changed_fields.append("updated_at")
        category.save(update_fields=changed_fields)
    return category


@db_transaction.atomic
def delete_category(*, category: Category) -> None:
    """Delete a custom category, migrating attached transactions to "Boshqa".

    The user's own "Boshqa" custom row is preferred; falls back to the preset.
    If no Boshqa exists for the type at all (shouldn't happen since fixture
    seeds it), transactions are simply detached (`category=NULL`).
    """
    if category.is_preset:
        raise CannotEditPresetError("Preset kategoriyani o'chirib bo'lmaydi.")

    fallback = match_slug(category.user, slug=BOSHQA_SLUG, type=category.type)
    # Avoid migrating onto ourselves (shouldn't happen, but defensive).
    if fallback is not None and fallback.id == category.id:
        fallback = None

    # Lazy import — services live above the model dependency chain so we can't
    # import Transaction at module load without creating a cycle.
    from transactions.models import Transaction

    Transaction.objects.filter(user=category.user, category=category).update(
        category=fallback,
    )
    category.delete()


@db_transaction.atomic
def toggle_hide_preset(*, user: User, category: Category) -> bool:
    """Toggle hide/show for a preset category for this user.

    Returns the new "hidden" state. Custom categories are never hidden
    (delete them instead) — raises CannotHideCustomError.
    """
    if not category.is_preset:
        raise CannotHideCustomError("Faqat preset kategoriyani yashirish mumkin.")

    existing = CategoryHide.objects.filter(user=user, category=category).first()
    if existing is not None:
        existing.delete()
        return False
    CategoryHide.objects.create(user=user, category=category)
    return True
