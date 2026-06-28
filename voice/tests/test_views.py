"""Story 2.2 — async voice endpoint integration tests."""

from __future__ import annotations

import io
from datetime import date as _date_type
from decimal import Decimal

import pytest
from django.test import Client, override_settings
from django.urls import reverse

from accounts.tests.test_services import BOT_TOKEN, _make_init_data
from voice import services_async as _services_async_mod
from voice.schemas import ParsedResponse, VoiceDraft


@pytest.fixture
def mock_pipeline(monkeypatch):
    """Replace `transcribe_and_parse_async` with a configurable async stub.

    Returns a controller object so tests can swap result/exception per case
    without re-monkeypatching.
    """

    class _Controller:
        def __init__(self) -> None:
            self.result: ParsedResponse | None = ParsedResponse(
                transactions=[], recurring_intent=None
            )
            self.exception: BaseException | None = None
            self.calls: list[tuple[bytes, object]] = []

    ctrl = _Controller()

    async def fake(audio_bytes: bytes, user, **_kwargs):
        ctrl.calls.append((audio_bytes, user))
        if ctrl.exception is not None:
            raise ctrl.exception
        return ctrl.result

    monkeypatch.setattr(_services_async_mod, "transcribe_and_parse_async", fake)
    # Also patch the binding the view imported at module load.
    from voice import views as _views_mod

    monkeypatch.setattr(_views_mod, "transcribe_and_parse_async", fake)
    return ctrl


def _draft(**overrides):
    base = {
        "type": "expense",
        "amount": Decimal("25000.00"),
        "currency": "UZS",
        "category_slug": "food",
        "counterparty": None,
        "date": _date_type.today(),
        "note": None,
        "confidence": 0.92,
        "ambiguous_fields": [],
    }
    base.update(overrides)
    return VoiceDraft(**base)


def _audio_upload(content_type: str = "audio/webm", size: int = 1024):
    """Build a tiny in-memory audio upload mimicking a recorded blob."""
    payload = b"\x00" * size
    fh = io.BytesIO(payload)
    fh.name = "voice.webm"
    return fh, content_type


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_get_returns_method_not_allowed() -> None:
    client = Client()
    init_data = _make_init_data(user_id=70)
    response = client.get(
        reverse("voice:transcribe"),
        headers={"X-Telegram-InitData": init_data},
    )
    assert response.status_code == 405


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_post_without_audio_returns_400() -> None:
    client = Client()
    init_data = _make_init_data(user_id=70)
    response = client.post(
        reverse("voice:transcribe"),
        data={},
        headers={"X-Telegram-InitData": init_data},
    )
    assert response.status_code == 400


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_post_with_unsupported_content_type_returns_415() -> None:
    """audio/wav is rejected — Story 2.2 AC."""
    from django.core.files.uploadedfile import SimpleUploadedFile

    client = Client()
    init_data = _make_init_data(user_id=70)
    upload = SimpleUploadedFile("voice.wav", b"\x00" * 1024, content_type="audio/wav")
    response = client.post(
        reverse("voice:transcribe"),
        data={"audio": upload},
        headers={"X-Telegram-InitData": init_data},
    )
    assert response.status_code == 415


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_post_oversized_audio_returns_413() -> None:
    """Files over 2 MB are rejected — Story 2.2 AC."""
    client = Client()
    init_data = _make_init_data(user_id=70)
    big = io.BytesIO(b"\x00" * (2 * 1024 * 1024 + 100))
    big.name = "voice.webm"
    from django.core.files.uploadedfile import SimpleUploadedFile

    upload = SimpleUploadedFile(
        "voice.webm",
        big.getvalue(),
        content_type="audio/webm",
    )
    response = client.post(
        reverse("voice:transcribe"),
        data={"audio": upload},
        headers={"X-Telegram-InitData": init_data},
    )
    assert response.status_code == 413


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_post_valid_audio_returns_confirm_partial(mock_pipeline) -> None:
    """Story 2.2 happy path: posting a small valid webm reaches the service."""
    from django.core.files.uploadedfile import SimpleUploadedFile

    mock_pipeline.result = ParsedResponse(transactions=[_draft()], recurring_intent=None)
    client = Client()
    init_data = _make_init_data(user_id=70)
    upload = SimpleUploadedFile("voice.webm", b"\x00" * 1024, content_type="audio/webm")
    response = client.post(
        reverse("voice:transcribe"),
        data={"audio": upload},
        headers={"X-Telegram-InitData": init_data},
    )
    assert response.status_code == 200
    assert len(mock_pipeline.calls) == 1


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_post_valid_audio_with_codec_parameter_accepted(mock_pipeline) -> None:
    """`audio/webm;codecs=opus` is allowed alongside the bare type."""
    from django.core.files.uploadedfile import SimpleUploadedFile

    mock_pipeline.result = ParsedResponse(transactions=[_draft()], recurring_intent=None)
    client = Client()
    init_data = _make_init_data(user_id=70)
    upload = SimpleUploadedFile(
        "voice.webm",
        b"\x00" * 1024,
        content_type="audio/webm;codecs=opus",
    )
    response = client.post(
        reverse("voice:transcribe"),
        data={"audio": upload},
        headers={"X-Telegram-InitData": init_data},
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_post_rejects_anonymous_caller() -> None:
    client = Client()
    response = client.post(reverse("voice:transcribe"))
    assert response.status_code == 401
