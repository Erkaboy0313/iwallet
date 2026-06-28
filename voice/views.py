"""Story 2.2+ — async voice endpoint.

`transcribe` accepts an audio blob (multipart) and returns the confirm partial.
`save` persists the user-confirmed draft via transactions.services.create_transaction.
ORM access from inside async views is wrapped in `sync_to_async`.

Story 6.2 adds `save_multi` which atomically creates N Transactions from a
single batch payload. Story 6.3 extends it to optionally co-create a
RecurringSchedule when the payload's `recurring` slot is populated. The view
never touches the ORM directly — it composes existing services so per-app
invariants stay owned by the services they belong to.
"""

from __future__ import annotations

import json
import logging
from datetime import date as _date_type
from decimal import Decimal, InvalidOperation

from asgiref.sync import sync_to_async
from django.db import transaction as db_transaction
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.models import CURRENCY_CHOICES
from categories.selectors import match_slug
from recurring.exceptions import (
    InvalidAmountError as RecurringInvalidAmountError,
    InvalidNameError,
    InvalidScheduleError,
)
from recurring.models import ScheduleKind
from recurring.services import create_recurring
from transactions.exceptions import InvalidAmountError
from transactions.models import TransactionType
from transactions.services import create_transaction

from .exceptions import GeminiConfigError, GeminiUnavailableError, NoTransactionsParsedError
from .schemas import ParsedResponse
from .services_async import transcribe_and_parse_async

logger = logging.getLogger(__name__)

MAX_AUDIO_BYTES = 2 * 1024 * 1024  # 2 MB — Story 2.2 AC
ALLOWED_CONTENT_TYPES = ("audio/mp4", "audio/webm")

VALID_TYPES = {t.value for t in TransactionType}
VALID_CURRENCIES = {code for code, _label in CURRENCY_CHOICES}


def _content_type_allowed(value: str) -> bool:
    if not value:
        return False
    base = value.split(";", 1)[0].strip().lower()
    return base in ALLOWED_CONTENT_TYPES


async def transcribe(request: HttpRequest) -> HttpResponse:
    """Accept an audio blob, call Gemini, render the confirm partial."""
    if request.method != "POST":
        return HttpResponse(status=405)

    audio_file = request.FILES.get("audio") if request.FILES else None
    if audio_file is None:
        return JsonResponse({"error": "missing_audio"}, status=400)

    if not _content_type_allowed(getattr(audio_file, "content_type", "") or ""):
        return JsonResponse({"error": "unsupported_content_type"}, status=415)

    audio_bytes = await sync_to_async(audio_file.read)()
    if len(audio_bytes) > MAX_AUDIO_BYTES:
        return JsonResponse({"error": "payload_too_large"}, status=413)

    try:
        parsed: ParsedResponse = await transcribe_and_parse_async(audio_bytes, request.user)
    except (GeminiUnavailableError, GeminiConfigError):
        logger.warning("voice.transcribe: Gemini unavailable")
        response = await sync_to_async(render)(
            request, "voice/_error_partial.html", {"reason": "unavailable"}
        )
        response.status_code = 503
        return response
    except NoTransactionsParsedError:
        logger.info("voice.transcribe: no transactions parsed")
        response = await sync_to_async(render)(
            request, "voice/_error_partial.html", {"reason": "empty"}
        )
        response.status_code = 422
        return response

    if not parsed.transactions:
        response = await sync_to_async(render)(
            request, "voice/_error_partial.html", {"reason": "empty"}
        )
        response.status_code = 422
        return response

    # Template tags do ORM (categories.match_slug) — wrap the sync render so it
    # doesn't trip Django's async-safety check.
    return await sync_to_async(render)(
        request,
        "voice/_confirm_partial.html",
        {
            "drafts": parsed.transactions,
            "recurring": parsed.recurring_intent,
            "valid_currencies": sorted(VALID_CURRENCIES),
        },
    )


@require_POST
def save(request: HttpRequest) -> HttpResponse:
    """Persist a single voice-confirmed transaction. Story 2.4."""
    try:
        payload = _coerce_save_payload(request)
    except _SaveValidationError as exc:
        response = HttpResponse(status=422)
        response.headers["HX-Trigger"] = json.dumps(
            {"toast": {"type": "error", "message": str(exc)}}
        )
        return response

    category = None
    if payload["type"] in {"income", "expense"} and payload["category_slug"]:
        category = match_slug(request.user, slug=payload["category_slug"], type=payload["type"])

    try:
        create_transaction(
            user=request.user,
            type=payload["type"],
            amount=payload["amount"],
            currency=payload["currency"],
            date=payload["date"],
            category=category,
            counterparty=payload["counterparty"],
            note=payload["note"],
        )
    except InvalidAmountError as exc:
        response = HttpResponse(status=422)
        response.headers["HX-Trigger"] = json.dumps(
            {"toast": {"type": "error", "message": str(exc)}}
        )
        return response

    response = HttpResponse(status=200)
    response.headers["HX-Redirect"] = reverse("core:home")
    response.headers["HX-Trigger"] = json.dumps(
        {"toast": {"type": "success", "message": "Tranzaksiya saqlandi"}}
    )
    return response


class _SaveValidationError(ValueError):
    """Surface a polite Uzbek error string back to the user via toast."""


def _coerce_save_payload(request: HttpRequest) -> dict:
    raw = request.POST.get("payload")
    if raw:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise _SaveValidationError("Ma'lumot noto'g'ri") from exc
    else:
        data = request.POST.dict()

    type_ = (data.get("type") or "").strip()
    if type_ not in VALID_TYPES:
        raise _SaveValidationError("Tranzaksiya turi noto'g'ri")

    currency = (data.get("currency") or "UZS").strip().upper()
    if currency not in VALID_CURRENCIES:
        raise _SaveValidationError("Valyuta noto'g'ri")

    try:
        amount = Decimal(str(data.get("amount") or "0"))
    except (InvalidOperation, ValueError) as exc:
        raise _SaveValidationError("Summa noto'g'ri") from exc
    if amount <= 0:
        raise _SaveValidationError("Summa musbat bo'lishi kerak")

    date_raw = (data.get("date") or "").strip()
    try:
        tx_date = _date_type.fromisoformat(date_raw) if date_raw else _date_type.today()
    except ValueError as exc:
        raise _SaveValidationError("Sana noto'g'ri") from exc

    counterparty = (data.get("counterparty") or "").strip()
    if type_ in {"debt_lent", "debt_borrowed"} and not counterparty:
        raise _SaveValidationError("Kim bilan ekanini yozing")

    return {
        "type": type_,
        "amount": amount,
        "currency": currency,
        "date": tx_date,
        "category_slug": (data.get("category_slug") or "").strip(),
        "counterparty": counterparty,
        "note": (data.get("note") or "").strip(),
    }


# ---------- Story 6.2 — multi-draft batch save ----------


# Keep in sync with voice.parser.MAX_DRAFTS_PER_UTTERANCE.
MAX_BATCH_DRAFTS = 10


@require_POST
def save_multi(request: HttpRequest) -> HttpResponse:
    """Persist N voice-confirmed Transactions atomically.

    Optionally also creates a RecurringSchedule when the payload's
    `recurring` slot is populated (Story 6.3 confirm path). The whole thing
    is one `db_transaction.atomic` block so a single failed insert rolls
    back the entire batch — matching FR25 ("all-or-nothing" multi-tx save).
    """
    try:
        payload = _coerce_multi_save_payload(request)
    except _SaveValidationError as exc:
        return _error_response(str(exc))

    drafts = payload["drafts"]
    recurring = payload.get("recurring")

    try:
        with db_transaction.atomic():
            for draft in drafts:
                category = _resolve_category_for(
                    request.user,
                    type_=draft["type"],
                    slug=draft["category_slug"],
                )
                create_transaction(
                    user=request.user,
                    type=draft["type"],
                    amount=draft["amount"],
                    currency=draft["currency"],
                    date=draft["date"],
                    category=category,
                    counterparty=draft["counterparty"],
                    note=draft["note"],
                )
            if recurring is not None:
                _create_recurring_from_payload(request.user, recurring)
    except InvalidAmountError as exc:
        return _error_response(str(exc))
    except (
        RecurringInvalidAmountError,
        InvalidNameError,
        InvalidScheduleError,
    ) as exc:
        return _error_response(str(exc))

    count = len(drafts)
    message = "Tranzaksiya saqlandi" if count == 1 else f"{count} ta tranzaksiya saqlandi"
    if recurring is not None:
        message += " · takror sozlandi"

    response = HttpResponse(status=200)
    response.headers["HX-Redirect"] = reverse("core:home")
    response.headers["HX-Trigger"] = json.dumps({"toast": {"type": "success", "message": message}})
    return response


def _error_response(message: str) -> HttpResponse:
    response = HttpResponse(status=422)
    response.headers["HX-Trigger"] = json.dumps({"toast": {"type": "error", "message": message}})
    return response


def _resolve_category_for(user, *, type_: str, slug: str):
    if type_ not in {"income", "expense"} or not slug:
        return None
    return match_slug(user, slug=slug, type=type_)


def _coerce_multi_save_payload(request: HttpRequest) -> dict:
    raw = request.POST.get("payload")
    if not raw:
        raise _SaveValidationError("Ma'lumot noto'g'ri")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise _SaveValidationError("Ma'lumot noto'g'ri") from exc

    raw_drafts = data.get("drafts")
    if not isinstance(raw_drafts, list) or not raw_drafts:
        raise _SaveValidationError("Saqlash uchun tranzaksiya yo'q")
    if len(raw_drafts) > MAX_BATCH_DRAFTS:
        raise _SaveValidationError(f"Bir vaqtda {MAX_BATCH_DRAFTS} tadan ortiq saqlab bo'lmaydi")

    drafts: list[dict] = []
    for item in raw_drafts:
        if not isinstance(item, dict):
            raise _SaveValidationError("Ma'lumot noto'g'ri")
        drafts.append(_coerce_one_draft(item))

    recurring = data.get("recurring")
    parsed_recurring: dict | None = None
    if recurring is not None:
        if not isinstance(recurring, dict):
            raise _SaveValidationError("Takror ma'lumoti noto'g'ri")
        parsed_recurring = _coerce_recurring_payload(recurring)

    return {"drafts": drafts, "recurring": parsed_recurring}


def _coerce_one_draft(data: dict) -> dict:
    type_ = (data.get("type") or "").strip()
    if type_ not in VALID_TYPES:
        raise _SaveValidationError("Tranzaksiya turi noto'g'ri")

    currency = (data.get("currency") or "UZS").strip().upper()
    if currency not in VALID_CURRENCIES:
        raise _SaveValidationError("Valyuta noto'g'ri")

    try:
        amount = Decimal(str(data.get("amount") or "0"))
    except (InvalidOperation, ValueError) as exc:
        raise _SaveValidationError("Summa noto'g'ri") from exc
    if amount <= 0:
        raise _SaveValidationError("Summa musbat bo'lishi kerak")

    date_raw = (data.get("date") or "").strip()
    try:
        tx_date = _date_type.fromisoformat(date_raw) if date_raw else _date_type.today()
    except ValueError as exc:
        raise _SaveValidationError("Sana noto'g'ri") from exc

    counterparty = (data.get("counterparty") or "").strip()
    if type_ in {"debt_lent", "debt_borrowed"} and not counterparty:
        raise _SaveValidationError("Kim bilan ekanini yozing")

    return {
        "type": type_,
        "amount": amount,
        "currency": currency,
        "date": tx_date,
        "category_slug": (data.get("category_slug") or "").strip(),
        "counterparty": counterparty,
        "note": (data.get("note") or "").strip(),
    }


# ---------- Story 6.3 — recurring intent co-creation ----------


def _coerce_recurring_payload(raw: dict) -> dict:
    """Project the recurring intent draft + hint into create_recurring kwargs."""
    base = _coerce_one_draft(raw)
    hint = raw.get("recurring_hint") or {}
    if not isinstance(hint, dict):
        raise _SaveValidationError("Takror jadvali noto'g'ri")
    kind = (hint.get("schedule_kind") or "").strip().lower()
    if kind == "every_n_days":
        # Epic 7's RecurringSchedule only models monthly / weekly; map every-7
        # to weekly with day_of_week == today's weekday, otherwise refuse the
        # auto path (the deep-link UI lets the user pick manually).
        n = hint.get("every_n_days")
        if isinstance(n, int) and n == 7:
            kind = "weekly"
            hint = {**hint, "day_of_week": timezone.localdate().weekday()}
        else:
            raise _SaveValidationError("Bu davriylik hozircha qo'lda sozlanadi")
    if kind not in {k.value for k in ScheduleKind}:
        raise _SaveValidationError("Takror turi noto'g'ri")

    day_of_month = hint.get("day_of_month")
    day_of_week = hint.get("day_of_week")
    try:
        day_of_month = int(day_of_month) if day_of_month not in (None, "") else None
    except (TypeError, ValueError) as exc:
        raise _SaveValidationError("Oy kuni noto'g'ri") from exc
    try:
        day_of_week = int(day_of_week) if day_of_week not in (None, "") else None
    except (TypeError, ValueError) as exc:
        raise _SaveValidationError("Hafta kuni noto'g'ri") from exc

    return {
        "type": base["type"],
        "amount": base["amount"],
        "currency": base["currency"],
        "category_slug": base["category_slug"],
        "note": base["note"],
        "schedule_kind": kind,
        "day_of_month": day_of_month,
        "day_of_week": day_of_week,
    }


def _create_recurring_from_payload(user, recurring: dict) -> None:
    category = _resolve_category_for(user, type_=recurring["type"], slug=recurring["category_slug"])
    # Name defaults to the spoken note (or a polite fallback) — the user can
    # rename later from /app/settings/recurring/. Truncate at the model's
    # 64-char limit so we never bounce on `InvalidNameError`.
    name = (recurring["note"] or "Ovozli takror")[:64]
    create_recurring(
        user=user,
        type_=recurring["type"],
        name=name,
        amount=recurring["amount"],
        currency=recurring["currency"],
        category=category,
        schedule_kind=recurring["schedule_kind"],
        day_of_month=recurring["day_of_month"],
        day_of_week=recurring["day_of_week"],
    )
