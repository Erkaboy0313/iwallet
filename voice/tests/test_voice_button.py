"""Story 2.1 — VoiceButton template + Home enablement smoke tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from django.template.loader import render_to_string
from django.test import Client, override_settings
from django.urls import reverse

from accounts.tests.test_services import BOT_TOKEN, _make_init_data

STATIC_JS = Path(__file__).resolve().parents[2] / "static" / "js" / "voice-recorder.js"


def test_voice_button_partial_renders_all_states() -> None:
    """All four button states (idle/recording/processing/error) are present in the markup."""
    html = render_to_string("voice/_voice_button.html")
    assert "🎤" in html  # idle/error glyph
    assert "⏹" in html  # recording glyph
    assert "vb-pulse" in html  # recording animation
    assert "vb-shake" in html  # error animation
    assert "vb-bounce" in html  # processing dots
    # ARIA contract
    assert "aria-pressed" in html
    assert "Ovoz bilan tranzaksiya" in html
    # Sticks the URL of the async transcribe endpoint into the Alpine component.
    assert "/app/voice/transcribe/" in html


def test_voice_recorder_js_module_exports_expected_surface() -> None:
    """Unit-testable JS module — Story 2.1 AC: exports VoiceRecorder + start/stop/cancel."""
    src = STATIC_JS.read_text(encoding="utf-8")
    assert "class VoiceRecorder" in src
    assert "start()" in src or "async start()" in src
    assert "stop()" in src
    assert "cancel()" in src
    assert "onStateChange" in src
    # Browser support detection per AC.
    assert "audio/mp4" in src
    assert "audio/webm" in src
    assert "UnsupportedError" in src
    # Silence detection wired
    assert "silence" in src.lower()


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_add_page_includes_voice_button() -> None:
    """Voice moved off Home (Eric's spec) into the Add transaction page so
    the mic is reachable when the user starts entering a transaction."""
    from django.utils import timezone

    from accounts.models import User

    client = Client()
    init_data = _make_init_data(user_id=42)
    client.get(reverse("core:home_content"), headers={"X-Telegram-InitData": init_data})
    User.objects.filter(telegram_id=42).update(onboarded_at=timezone.now())
    response = client.get(
        reverse("transactions:add"),
        headers={"X-Telegram-InitData": init_data},
    )
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    assert "Ovoz bilan tranzaksiya qo'shish" in body
    assert "voice-confirm-area" in body
