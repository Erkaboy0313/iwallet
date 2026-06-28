"""Story 2.1 scaffolding — endpoints exist so the VoiceButton include can
resolve `{% url 'voice:transcribe' %}` and `{% url 'voice:save' %}`. Real
async-pipeline behavior lands in Story 2.2 (transcribe) and 2.4 (save).
"""

from __future__ import annotations

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST


def transcribe(request: HttpRequest) -> HttpResponse:
    """Placeholder — Story 2.2 turns this into an async endpoint."""
    if request.method != "POST":
        return HttpResponse(status=405)
    return render(request, "voice/_confirm_partial.html", {"drafts": []})


@require_POST
def save(_request: HttpRequest) -> HttpResponse:
    """Placeholder — Story 2.4 wires this to transactions.services.create_transaction."""
    return HttpResponse(status=204)
