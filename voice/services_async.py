"""Async voice pipeline orchestration (Story 2.2/2.3).

Glues the Gemini client to the parser. Story 2.2 introduced this with an empty
stub; Story 2.3 wires the real Gemini call. The view layer only ever talks to
this module — keeping the pipeline composable + mockable in tests.
"""

from __future__ import annotations

import logging

from asgiref.sync import sync_to_async
from django.conf import settings

from accounts.models import User

from .exceptions import GeminiConfigError, NoTransactionsParsedError
from .gemini_client import GeminiClient
from .parser import normalize
from .schemas import ParsedResponse

logger = logging.getLogger(__name__)


async def transcribe_and_parse_async(
    audio_bytes: bytes,
    user: User,
    *,
    client: GeminiClient | None = None,
) -> ParsedResponse:
    """Hand the audio bytes to Gemini and return a parsed, validated response.

    `client` is overridable so tests can inject an `httpx.MockTransport`-backed
    client without monkey-patching globals.
    """
    api_key = getattr(settings, "GEMINI_API_KEY", "") or ""
    owns_client = client is None
    if owns_client:
        if not api_key:
            raise GeminiConfigError("GEMINI_API_KEY is not configured")
        client = GeminiClient(api_key=api_key)

    try:
        default_currency = await sync_to_async(_get_default_currency)(user)
        expense_categories = await sync_to_async(_categories_for_prompt)(user, "expense")
        income_categories = await sync_to_async(_categories_for_prompt)(user, "income")
        raw = await client.transcribe_and_parse(
            audio_bytes,
            user_currency_default=default_currency,
            expense_categories=expense_categories,
            income_categories=income_categories,
        )
    finally:
        if owns_client:
            await client.aclose()

    parsed = await sync_to_async(normalize)(raw, user)
    if not parsed.transactions:
        raise NoTransactionsParsedError("No transactions returned by Gemini")
    return parsed


def _get_default_currency(user: User) -> str:
    """Pull the user's preferred currency for the Gemini prompt context."""
    return getattr(user, "default_currency", "UZS") or "UZS"


def _categories_for_prompt(user: User, type_: str) -> tuple[tuple[str, str], ...]:
    """Return ((slug, display_name), …) for Gemini's slug vocabulary."""
    # Local import — keeps the async surface independent of the categories app
    # boot order and matches the pattern used in currencies/selectors.
    from categories.selectors import categories_for

    return tuple((c.slug, c.name) for c in categories_for(user, type_))
