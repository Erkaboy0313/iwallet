"""Domain exceptions for the currencies app (Epic 5)."""

from __future__ import annotations


class CbuUnavailableError(RuntimeError):
    """Raised when CBU.uz cannot be reached / parsed after retries."""


class MissingRateError(RuntimeError):
    """Raised when a conversion is requested and no usable rate exists at all."""
