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

from .schemas import ParsedResponse, RecurringHint, VoiceDraft

logger = logging.getLogger(__name__)

VALID_TYPES = {"expense", "income", "debt_lent", "debt_borrowed"}
VALID_CURRENCIES = {"UZS", "RUB", "USD"}
DEBT_TYPES = {"debt_lent", "debt_borrowed"}
CATEGORY_TYPES = {"expense", "income"}
FALLBACK_CATEGORY_SLUG = "boshqa"
LOW_CONFIDENCE_THRESHOLD = 0.7
MAX_DRAFTS_PER_UTTERANCE = 5  # Story 6.1 AC — cap a single utterance at 5 drafts.
VALID_SCHEDULE_KINDS = {"monthly", "weekly", "every_n_days"}

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


def _normalize_schedule_hint(raw: Any) -> RecurringHint | None:
    """Parse Gemini's schedule_hint into a structured `RecurringHint`.

    Accepts either a dict (preferred) like ``{"kind": "monthly", "day_of_month": 1}``
    or a string shorthand ``"monthly:day=1"`` / ``"weekly:dow=0"`` /
    ``"every_n_days:n=3"`` / ``"monthly"`` / ``"weekly"``. Returns None on any
    unrecognized shape so Story 6.3 can fall back to a "no cadence inferred"
    UX path without 500ing.
    """
    if raw is None:
        return None

    kind: str | None = None
    day_of_month: int | None = None
    day_of_week: int | None = None
    every_n_days: int | None = None

    if isinstance(raw, dict):
        kind = _coerce_string(raw.get("kind") or raw.get("schedule_kind")).lower() or None
        try:
            dom_raw = raw.get("day_of_month")
            if dom_raw is not None and dom_raw != "":
                day_of_month = int(dom_raw)
        except (TypeError, ValueError):
            day_of_month = None
        try:
            dow_raw = raw.get("day_of_week")
            if dow_raw is not None and dow_raw != "":
                day_of_week = int(dow_raw)
        except (TypeError, ValueError):
            day_of_week = None
        try:
            n_raw = raw.get("every_n_days") or raw.get("n")
            if n_raw is not None and n_raw != "":
                every_n_days = int(n_raw)
        except (TypeError, ValueError):
            every_n_days = None
    elif isinstance(raw, str):
        text = raw.strip().lower()
        if not text:
            return None
        head, _, tail = text.partition(":")
        kind = head.strip() or None
        for chunk in tail.split(","):
            chunk = chunk.strip()
            if not chunk:
                continue
            key, _, value = chunk.partition("=")
            key = key.strip()
            value = value.strip()
            try:
                if key in {"day", "dom", "day_of_month"}:
                    day_of_month = int(value)
                elif key in {"dow", "day_of_week"}:
                    day_of_week = int(value)
                elif key in {"n", "every", "every_n_days"}:
                    every_n_days = int(value)
            except ValueError:
                continue
    else:
        return None

    if kind not in VALID_SCHEDULE_KINDS:
        return None

    # Defensive clamping — invariants for the create_recurring service.
    if kind == "monthly":
        if day_of_month is None or not 1 <= day_of_month <= 31:
            return None
        day_of_week = None
        every_n_days = None
    elif kind == "weekly":
        if day_of_week is None or not 0 <= day_of_week <= 6:
            return None
        day_of_month = None
        every_n_days = None
    elif kind == "every_n_days":
        if every_n_days is None or every_n_days < 1:
            return None
        day_of_month = None
        day_of_week = None

    return RecurringHint(
        schedule_kind=kind,
        day_of_month=day_of_month,
        day_of_week=day_of_week,
        every_n_days=every_n_days,
    )


def normalize(
    raw: dict[str, Any], user: User, *, today: _date_type | None = None
) -> ParsedResponse:
    """Turn raw Gemini JSON into a validated `ParsedResponse`.

    Story 6.1: cap multi-transaction utterances at `MAX_DRAFTS_PER_UTTERANCE`
    so a runaway model can't flood the confirm screen.
    Story 6.3: the optional `recurring_intent` slot carries a `RecurringHint`
    parsed from the model's `schedule_hint` field.
    """
    today = today or _date_type.today()
    raw = raw or {}
    raw_txs = raw.get("transactions") or []
    drafts: list[VoiceDraft] = []
    seen_fingerprints: set[tuple] = set()
    for item in raw_txs:
        if not isinstance(item, dict):
            continue
        if len(drafts) >= MAX_DRAFTS_PER_UTTERANCE:
            logger.info(
                "voice.parser: drop draft — cap of %d reached",
                MAX_DRAFTS_PER_UTTERANCE,
            )
            break
        draft = _normalize_draft(item, user, today)
        if draft is None:
            continue
        # Safety net: Gemini occasionally echoes the last transaction multiple
        # times. If a normalized draft is byte-identical to one we already
        # kept, drop the duplicate instead of forcing the user to delete it.
        fp = (
            draft.type,
            draft.amount,
            draft.currency,
            draft.category_slug,
            draft.counterparty or "",
            draft.date,
            draft.note or "",
        )
        if fp in seen_fingerprints:
            logger.info("voice.parser: drop duplicate draft (fingerprint=%s)", fp)
            continue
        seen_fingerprints.add(fp)
        drafts.append(draft)

    recurring = None
    recurring_raw = raw.get("recurring_intent")
    if isinstance(recurring_raw, dict):
        recurring = _normalize_draft(recurring_raw, user, today)
        if recurring is not None:
            hint = _normalize_schedule_hint(recurring_raw.get("schedule_hint"))
            recurring.recurring_hint = hint

    return ParsedResponse(transactions=drafts, recurring_intent=recurring)
