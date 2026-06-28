"""Template helpers for the voice confirm screen (Story 2.4).

Serializes a `VoiceDraft` into a JSON object literal suitable for embedding
inside an Alpine `x-data` attribute, with category emoji/name attached so the
client doesn't need a second round-trip just to render the pill.
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


def _category_display(user, draft: VoiceDraft) -> tuple[str, str]:
    if draft.type not in {"income", "expense"} or not draft.category_slug:
        return "📁", "Kategoriya"
    if user is None or not getattr(user, "is_authenticated", False):
        return "📁", draft.category_slug
    cat = match_slug(user, slug=draft.category_slug, type=draft.type)
    if cat is None:
        return "📁", draft.category_slug
    return cat.emoji, cat.name


@register.simple_tag(takes_context=True)
def draft_payload_json(context, draft: VoiceDraft):  # pragma: no cover - thin glue
    return _serialize_draft(context.get("request"), draft)


@register.filter(name="draft_payload_json")
def draft_payload_json_filter(draft: VoiceDraft, user=None):
    return _serialize_draft(_RequestStub(user), draft)


class _RequestStub:
    def __init__(self, user) -> None:
        self.user = user


def _serialize_draft(request, draft: VoiceDraft) -> str:
    user = getattr(request, "user", None) if request is not None else None
    emoji, category_name = _category_display(user, draft)

    payload = {
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
