"""Domain exceptions for the voice app (Epic 2)."""

from __future__ import annotations


class GeminiUnavailableError(RuntimeError):
    """Raised when Gemini cannot be reached / parsed after retries."""


class NoTransactionsParsedError(RuntimeError):
    """Gemini responded but no transactions could be extracted from the audio."""


class GeminiConfigError(RuntimeError):
    """GEMINI_API_KEY is missing at runtime — surfaced as 503 to the user."""
