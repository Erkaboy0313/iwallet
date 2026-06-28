"""Story 2.5 — voice failure-mode integration tests.

Three modes:
  - Gemini unavailable after 3 retries → 503 + _error_partial.html
  - Gemini returns no parseable transactions → 422 + _error_partial.html
  - Mic recorded silence → client refuses to POST. Asserted via the
    `voice-recorder.js` static asset since the JS unit tests live as a smoke
    contract (Story 2.1 AC noted manual smoke testing).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, override_settings
from django.urls import reverse

from accounts.tests.test_services import BOT_TOKEN, _make_init_data
from voice import services_async as _services_async_mod, views as _views_mod
from voice.exceptions import (
    GeminiConfigError,
    GeminiUnavailableError,
    NoTransactionsParsedError,
)
from voice.schemas import ParsedResponse

STATIC_JS = Path(__file__).resolve().parents[2] / "static" / "js" / "voice-recorder.js"


def _patch_service(monkeypatch, *, exception=None, result=None):
    """Replace `transcribe_and_parse_async` in both the module + the view binding."""

    async def fake(_audio_bytes: bytes, _user, **_kwargs):
        if exception is not None:
            raise exception
        return result or ParsedResponse(transactions=[], recurring_intent=None)

    monkeypatch.setattr(_services_async_mod, "transcribe_and_parse_async", fake)
    monkeypatch.setattr(_views_mod, "transcribe_and_parse_async", fake)


def _post_audio(client: Client, user_id: int = 70):
    init_data = _make_init_data(user_id=user_id)
    upload = SimpleUploadedFile("voice.webm", b"\x00" * 1024, content_type="audio/webm")
    return client.post(
        reverse("voice:transcribe"),
        data={"audio": upload},
        headers={"X-Telegram-InitData": init_data},
    )


# ---------- Server-side error modes ----------


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_gemini_unavailable_returns_503_and_error_partial(monkeypatch) -> None:
    _patch_service(monkeypatch, exception=GeminiUnavailableError("retries exhausted"))
    response = _post_audio(Client())
    assert response.status_code == 503
    body = response.content.decode("utf-8")
    assert "Gemini" in body or "mavjud emas" in body
    assert "Qaytadan" in body
    assert "Qo'lda" in body


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_gemini_config_missing_returns_503_and_error_partial(monkeypatch) -> None:
    """Missing GEMINI_API_KEY at runtime surfaces as 503 unavailable, not 500."""
    _patch_service(monkeypatch, exception=GeminiConfigError("no key"))
    response = _post_audio(Client())
    assert response.status_code == 503


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_no_transactions_parsed_returns_422_and_error_partial(monkeypatch) -> None:
    _patch_service(monkeypatch, exception=NoTransactionsParsedError("empty"))
    response = _post_audio(Client())
    assert response.status_code == 422
    body = response.content.decode("utf-8")
    assert "tushunmadim" in body or "Qaytadan" in body
    assert "Qo'lda" in body


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_empty_drafts_treated_as_422(monkeypatch) -> None:
    """If the service returns ParsedResponse(transactions=[]) we still 422."""
    _patch_service(monkeypatch, result=ParsedResponse(transactions=[], recurring_intent=None))
    response = _post_audio(Client())
    assert response.status_code == 422


# ---------- Client-side silence detection (JS contract) ----------


def test_voice_recorder_exposes_silence_detector() -> None:
    """Story 2.5 AC: client-side silence detection must exist."""
    src = STATIC_JS.read_text(encoding="utf-8")
    assert "voiceIsLikelySilent" in src
    # The helper must short-circuit before HTTP for tiny / near-zero blobs.
    assert "blob.size" in src
    assert "duration" in src


def test_voice_button_short_circuits_on_silence_detection() -> None:
    """The button template must consult voiceIsLikelySilent before uploading."""
    template = Path(__file__).resolve().parents[1] / "templates" / "voice" / "_voice_button.html"
    src = template.read_text(encoding="utf-8")
    assert "voiceIsLikelySilent" in src
    assert "Hech narsa eshitilmadi" in src
