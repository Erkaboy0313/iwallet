"""Story 2.2+ — async voice endpoint.

`transcribe` accepts an audio blob (multipart) and returns the confirm partial.
`save` persists the user-confirmed draft via transactions.services.create_transaction.
ORM access from inside async views is wrapped in `sync_to_async`.
"""

from __future__ import annotations

import json
import logging
from datetime import date as _date_type
from decimal import Decimal, InvalidOperation

from asgiref.sync import sync_to_async
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_POST

from accounts.models import CURRENCY_CHOICES
from categories.selectors import match_slug
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
