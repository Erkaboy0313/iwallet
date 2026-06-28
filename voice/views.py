"""Story 2.2+ — async voice endpoint.

`transcribe` accepts an audio blob (multipart) and renders the confirm partial.
`save` (Story 2.4) persists the user-confirmed draft via the transactions
service. ORM access from inside async views goes through `sync_to_async`.
"""

from __future__ import annotations

import logging

from asgiref.sync import sync_to_async
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from .exceptions import (
    GeminiConfigError,
    GeminiUnavailableError,
    NoTransactionsParsedError,
)
from .services_async import transcribe_and_parse_async

logger = logging.getLogger(__name__)

MAX_AUDIO_BYTES = 2 * 1024 * 1024  # Story 2.2 AC — 2 MB cap
ALLOWED_CONTENT_TYPES = ("audio/mp4", "audio/webm")


def _content_type_allowed(value: str) -> bool:
    """Accept 'audio/webm' as well as 'audio/webm;codecs=opus'."""
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
        parsed = await transcribe_and_parse_async(audio_bytes, request.user)
    except (GeminiUnavailableError, GeminiConfigError):
        logger.warning("voice.transcribe: Gemini unavailable")
        response = render(request, "voice/_error_partial.html", {"reason": "unavailable"})
        response.status_code = 503
        return response
    except NoTransactionsParsedError:
        logger.info("voice.transcribe: no transactions parsed")
        response = render(request, "voice/_error_partial.html", {"reason": "empty"})
        response.status_code = 422
        return response

    return render(
        request,
        "voice/_confirm_partial.html",
        {
            "drafts": parsed.transactions,
            "recurring": parsed.recurring_intent,
        },
    )


@require_POST
def save(_request: HttpRequest) -> HttpResponse:
    """Placeholder — Story 2.4 wires this to transactions.services.create_transaction."""
    return HttpResponse(status=204)
