"""Read-side queries for Category (Story 1.3, Epic 3)."""

from django.db.models import Count, Q, QuerySet

from accounts.models import User

from .models import Category, CategoryHide


def _hidden_preset_ids(user: User) -> list[int]:
    """Preset ids that this user has chosen to hide."""
    return list(
        CategoryHide.objects.filter(user=user, category__user__isnull=True).values_list(
            "category_id", flat=True
        )
    )


def categories_for(user: User, type_: str) -> "QuerySet[Category]":
    """Return the user's visible categories of a given type.

    Includes presets (user=NULL) not globally hidden AND not hidden by this user,
    plus the user's own custom rows. Ordered by usage frequency (descending) then
    alphabetical by name, so the picker shows frequently used categories first
    (Story 3.2 AC).
    """
    hidden_ids = _hidden_preset_ids(user)
    qs = Category.objects.filter(
        Q(user=user) | Q(user__isnull=True),
        type=type_,
        is_hidden=False,
    ).exclude(id__in=hidden_ids)
    qs = qs.annotate(
        usage_count=Count(
            "transactions",
            filter=Q(transactions__user=user, transactions__is_deleted=False),
        ),
    )
    return qs.order_by("-usage_count", "name")


def categories_for_settings(user: User, type_: str) -> "QuerySet[Category]":
    """Return ALL categories visible OR hidden for the settings management page.

    Settings shows everything (so the user can unhide presets); the picker
    used during entry hides what the user has hidden. Returns rows annotated
    with `is_hidden_for_user` so the template can render the toggle state.
    """
    hidden_ids = _hidden_preset_ids(user)
    qs = Category.objects.filter(
        Q(user=user) | Q(user__isnull=True),
        type=type_,
        is_hidden=False,
    )
    # Tag each row with its visibility-for-this-user flag.
    rows = list(qs.order_by("name"))
    for row in rows:
        row.is_hidden_for_user = row.id in hidden_ids
    return rows


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
