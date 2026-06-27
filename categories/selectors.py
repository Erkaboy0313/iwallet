"""Read-side queries for Category (Story 1.3)."""

from django.db.models import Q, QuerySet

from accounts.models import User

from .models import Category


def categories_for(user: User, type_: str) -> "QuerySet[Category]":
    """Return the user's visible categories of a given type.

    Includes presets (user=NULL) NOT hidden globally, plus the user's own custom
    rows. Ordered alphabetically by name for stable UI rendering.
    """
    return Category.objects.filter(
        Q(user=user) | Q(user__isnull=True),
        type=type_,
        is_hidden=False,
    ).order_by("name")


def match_slug(user: User, *, slug: str, type: str) -> Category | None:  # noqa: A002
    """Find a Category by slug. Prefers user's custom row over preset."""
    qs = Category.objects.filter(
        Q(user=user) | Q(user__isnull=True),
        slug=slug,
        type=type,
    )
    # User custom wins; fall back to preset.
    custom = qs.filter(user=user).first()
    if custom is not None:
        return custom
    return qs.filter(user__isnull=True).first()
