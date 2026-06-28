"""Template helpers for the voice confirm screen (Story 2.4 + 6.2 + 6.3).

Serializes a `VoiceDraft` into a JSON object literal suitable for embedding
inside an Alpine `x-data` attribute, with category emoji/name attached so the
client doesn't need a second round-trip just to render the pill.

Story 6.2 adds `drafts_payload_json` so the parent Alpine component can
hydrate from the full list. Story 6.3 adds `recurring_payload_json` which
appends the structured `RecurringHint` so the recurring card can show
"har oy 1-sanasida" without a second round-trip, plus `hint_label` for
rendering the cadence into the amber prompt headline.
"""

from __future__ import annotations

import json
from datetime import date as _date_type
from decimal import Decimal

from django import template
from django.utils.safestring import mark_safe

from categories.selectors import match_slug

from ..schemas import VoiceDraft

register = template.Library()

TYPE_LABELS = {
    "expense": "Chiqim",
    "income": "Kirim",
    "debt_lent": "Qarz berdim",
    "debt_borrowed": "Qarz oldim",
}

WEEKDAY_LABELS = [
    "dushanba",
    "seshanba",
    "chorshanba",
    "payshanba",
    "juma",
    "shanba",
    "yakshanba",
]


def _category_display(user, draft: VoiceDraft) -> tuple[str, str]:
    if draft.type not in {"income", "expense"} or not draft.category_slug:
        return "📁", "Kategoriya"
    if user is None or not getattr(user, "is_authenticated", False):
        return "📁", draft.category_slug
    cat = match_slug(user, slug=draft.category_slug, type=draft.type)
    if cat is None:
        return "📁", draft.category_slug
    return cat.emoji, cat.name


def _payload_dict(request, draft: VoiceDraft) -> dict:
    user = getattr(request, "user", None) if request is not None else None
    emoji, category_name = _category_display(user, draft)
    return {
        "type": draft.type,
        "amount": _decimal_str(draft.amount),
        "currency": draft.currency,
        "category_slug": draft.category_slug,
        "category_name": category_name,
        "emoji": emoji,
        "counterparty": draft.counterparty or "",
        "date": _date_iso(draft.date),
        "note": draft.note or "",
        "confidence": float(draft.confidence),
        "ambiguous_fields": list(draft.ambiguous_fields or []),
        "type_label": TYPE_LABELS.get(draft.type, draft.type),
    }


@register.simple_tag(takes_context=True)
def draft_payload_json(context, draft: VoiceDraft):  # pragma: no cover - thin glue
    return _serialize_draft(context.get("request"), draft)


@register.simple_tag(takes_context=True)
def drafts_payload_json(context, drafts):
    """JS array literal of all drafts — Story 6.2 (multi-card x-data init)."""
    request = context.get("request")
    items = [_payload_dict(request, d) for d in (drafts or [])]
    encoded = json.dumps(items, ensure_ascii=True).replace('"', "&quot;")
    return mark_safe(encoded)


@register.simple_tag(takes_context=True)
def recurring_payload_json(context, recurring):
    """JS object literal for the recurring intent draft — Story 6.3.

    Returns `null` when there's no recurring intent so the consumer can keep
    its Alpine state simple (`recurring ? Object.assign({}, recurring) : null`).
    """
    if recurring is None:
        encoded = "null"
    else:
        payload = _payload_dict(context.get("request"), recurring)
        payload["recurring_hint"] = _serialize_hint(recurring)
        encoded = json.dumps(payload, ensure_ascii=True).replace('"', "&quot;")
    return mark_safe(encoded)


@register.simple_tag()
def hint_label(recurring):
    """Render the Uzbek cadence label for the recurring card header — Story 6.3."""
    if recurring is None:
        return ""
    hint = getattr(recurring, "recurring_hint", None)
    if hint is None:
        return ""
    return _hint_label(hint)


@register.filter(name="draft_payload_json")
def draft_payload_json_filter(draft: VoiceDraft, user=None):
    return _serialize_draft(_RequestStub(user), draft)


def _serialize_hint(draft: VoiceDraft) -> dict | None:
    hint = getattr(draft, "recurring_hint", None)
    if hint is None:
        return None
    return {
        "schedule_kind": hint.schedule_kind,
        "day_of_month": hint.day_of_month,
        "day_of_week": hint.day_of_week,
        "every_n_days": hint.every_n_days,
        "label": _hint_label(hint),
    }


def _hint_label(hint) -> str:
    """Polite Uzbek summary of the cadence — shown on the recurring card."""
    if hint.schedule_kind == "monthly" and hint.day_of_month is not None:
        return f"har oy {hint.day_of_month}-sanasida"
    if hint.schedule_kind == "weekly" and hint.day_of_week is not None:
        return f"har {WEEKDAY_LABELS[hint.day_of_week]}"
    if hint.schedule_kind == "every_n_days" and hint.every_n_days is not None:
        return f"har {hint.every_n_days} kunda"
    return "takrorlanib turadi"


class _RequestStub:
    def __init__(self, user) -> None:
        self.user = user


def _serialize_draft(request, draft: VoiceDraft) -> str:
    payload = _payload_dict(request, draft)
    # Render as an inline JS object literal inside an x-data="..." attribute.
    # ensure_ascii=True keeps non-ASCII chars (Uzbek apostrophes, emoji) escaped
    # so we never collide with the surrounding double quotes; we then turn the
    # remaining JSON " chars into &quot; so the browser decodes them back to
    # legal JS quotes inside the attribute.
    encoded = json.dumps(payload, ensure_ascii=True)
    encoded = encoded.replace('"', "&quot;")
    return mark_safe(encoded)


def _decimal_str(value: Decimal) -> str:
    if not isinstance(value, Decimal):
        try:
            value = Decimal(str(value))
        except Exception:  # pragma: no cover — defensive
            return str(value)
    return format(value.quantize(Decimal("0.01")), "f")


def _date_iso(value) -> str:
    if isinstance(value, _date_type):
        return value.isoformat()
    return str(value or "")
