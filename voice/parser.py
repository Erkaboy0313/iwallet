"""Normalize raw Gemini JSON into `ParsedResponse` (Story 2.3).

Defensive: Gemini's structured output occasionally drops fields or returns
amounts as numbers, dates as "bugun"/"kecha", or whole malformed transactions.
We cope with each of these rather than 500ing — invalid rows are dropped, soft
issues add the field to `ambiguous_fields`, and the final result is always a
well-typed `ParsedResponse`.
"""

from __future__ import annotations

import logging
import re
from datetime import date as _date_type, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

from accounts.models import User
from categories.selectors import match_slug

from .schemas import ParsedResponse, VoiceDraft

logger = logging.getLogger(__name__)

VALID_TYPES = {"expense", "income", "debt_lent", "debt_borrowed"}
VALID_CURRENCIES = {"UZS", "RUB", "USD"}
DEBT_TYPES = {"debt_lent", "debt_borrowed"}
CATEGORY_TYPES = {"expense", "income"}
FALLBACK_CATEGORY_SLUG = "boshqa"
LOW_CONFIDENCE_THRESHOLD = 0.7

# "15k", "15 ming", "yarim mln" — let Gemini do the heavy lifting, but cope with
# the cases where the model echoes the spoken phrase verbatim. Order matters:
# longest tokens first so "mln"/"million" beats "ming".
_AMOUNT_UNIT_MULTIPLIERS: list[tuple[str, Decimal]] = [
    ("mlrd", Decimal("1000000000")),
    ("milliard", Decimal("1000000000")),
    ("billion", Decimal("1000000000")),
    ("million", Decimal("1000000")),
    ("mln", Decimal("1000000")),
    ("ming", Decimal("1000")),
    ("k", Decimal("1000")),
]
_HALF_TOKENS = ("yarim", "half")

_REL_DATE_MAP = {
    "bugun": 0,
    "today": 0,
    "kecha": -1,
    "yesterday": -1,
    "ertaga": 1,
    "tomorrow": 1,
}


def _coerce_amount(raw: Any) -> Decimal | None:
    """Parse Gemini's amount into a positive Decimal or None on failure."""
    if raw is None:
        return None
    if isinstance(raw, int | float):
        try:
            value = Decimal(str(raw))
        except (InvalidOperation, ValueError):
            return None
        return value if value > 0 else None
    if not isinstance(raw, str):
        return None

    text = raw.strip().lower().replace(",", ".")
    if not text:
        return None

    # Direct decimal first — covers Gemini's "15000.00" happy path.
    try:
        value = Decimal(text)
    except InvalidOperation:
        value = None

    if value is None:
        # Spoken-form fallback: "15 ming", "yarim mln", "15k".
        multiplier = Decimal("1")
        cleaned = text
        for token, mult in _AMOUNT_UNIT_MULTIPLIERS:
            if re.search(rf"(^|\s|\d){re.escape(token)}\b", cleaned):
                multiplier = mult
                cleaned = re.sub(rf"\s*{re.escape(token)}\b", "", cleaned).strip()
                break
        base: Decimal | None = None
        for half_token in _HALF_TOKENS:
            if half_token in cleaned:
                base = Decimal("0.5")
                cleaned = cleaned.replace(half_token, "").strip()
                break
        if base is None:
            cleaned = re.sub(r"[^0-9.]+", "", cleaned)
            if not cleaned or cleaned == ".":
                return None
            try:
                base = Decimal(cleaned)
            except InvalidOperation:
                return None
        value = base * multiplier

    if value is None or value <= 0:
        return None
    return value.quantize(Decimal("0.01"))


def _coerce_date(raw: Any, today: _date_type) -> tuple[_date_type, bool]:
    """Return (date, is_ambiguous). Falls back to today on any failure."""
    if isinstance(raw, _date_type):
        return raw, False
    if not isinstance(raw, str) or not raw.strip():
        return today, True
    text = raw.strip().lower()
    if text in _REL_DATE_MAP:
        return today + timedelta(days=_REL_DATE_MAP[text]), False
    try:
        parsed = _date_type.fromisoformat(text)
    except ValueError:
        # Try DD.MM.YYYY
        try:
            day, month, year = (int(p) for p in text.split("."))
            parsed = _date_type(year, month, day)
        except (ValueError, TypeError):
            return today, True
    # Future-date clamp per docs/project-context.md.
    if parsed > today:
        return today, True
    return parsed, False


def _coerce_confidence(raw: Any) -> float:
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return 0.5
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def _coerce_string(raw: Any) -> str:
    if raw is None:
        return ""
    if isinstance(raw, str):
        return raw.strip()
    return str(raw).strip()


def _normalize_draft(raw: dict[str, Any], user: User, today: _date_type) -> VoiceDraft | None:
    type_ = _coerce_string(raw.get("type")).lower()
    if type_ not in VALID_TYPES:
        logger.info("voice.parser: drop draft — invalid type=%r", raw.get("type"))
        return None

    amount = _coerce_amount(raw.get("amount"))
    ambiguous_fields = list(
        dict.fromkeys(_coerce_string(f) for f in raw.get("ambiguous_fields") or [])
    )
    ambiguous_fields = [f for f in ambiguous_fields if f]

    if amount is None:
        # Without an amount the row is useless — drop it.
        logger.info("voice.parser: drop draft — invalid amount=%r", raw.get("amount"))
        return None

    currency = _coerce_string(raw.get("currency")).upper() or "UZS"
    if currency not in VALID_CURRENCIES:
        currency = "UZS"
        if "currency" not in ambiguous_fields:
            ambiguous_fields.append("currency")

    category_slug = _coerce_string(raw.get("category_slug")).lower()
    if type_ in CATEGORY_TYPES and category_slug:
        match = match_slug(user, slug=category_slug, type=type_)
        if match is None:
            category_slug = FALLBACK_CATEGORY_SLUG
            if "category_slug" not in ambiguous_fields:
                ambiguous_fields.append("category_slug")
        else:
            category_slug = match.slug
    elif type_ in CATEGORY_TYPES:
        category_slug = FALLBACK_CATEGORY_SLUG
        if "category_slug" not in ambiguous_fields:
            ambiguous_fields.append("category_slug")
    else:
        category_slug = ""

    counterparty = _coerce_string(raw.get("counterparty"))
    if type_ in DEBT_TYPES and not counterparty and "counterparty" not in ambiguous_fields:
        ambiguous_fields.append("counterparty")

    tx_date, date_ambiguous = _coerce_date(raw.get("date"), today)
    if date_ambiguous and "date" not in ambiguous_fields:
        ambiguous_fields.append("date")

    confidence = _coerce_confidence(raw.get("confidence"))
    # Mark fields explicitly listed by Gemini as low-confidence even if the
    # overall score is high, and bubble up the low overall score by flagging
    # everything (matches UX-DR uncertainty styling).
    if confidence < LOW_CONFIDENCE_THRESHOLD and not ambiguous_fields:
        ambiguous_fields.append("confidence")

    note = _coerce_string(raw.get("note"))

    return VoiceDraft(
        type=type_,
        amount=amount,
        currency=currency,
        category_slug=category_slug,
        counterparty=counterparty or None,
        date=tx_date,
        note=note or None,
        confidence=confidence,
        ambiguous_fields=ambiguous_fields,
    )


def normalize(
    raw: dict[str, Any], user: User, *, today: _date_type | None = None
) -> ParsedResponse:
    """Turn raw Gemini JSON into a validated `ParsedResponse`."""
    today = today or _date_type.today()
    raw = raw or {}
    raw_txs = raw.get("transactions") or []
    drafts: list[VoiceDraft] = []
    for item in raw_txs:
        if not isinstance(item, dict):
            continue
        draft = _normalize_draft(item, user, today)
        if draft is not None:
            drafts.append(draft)

    recurring = None
    recurring_raw = raw.get("recurring_intent")
    if isinstance(recurring_raw, dict):
        recurring = _normalize_draft(recurring_raw, user, today)

    return ParsedResponse(transactions=drafts, recurring_intent=recurring)
