"""Voice domain dataclasses (Story 2.3).

`VoiceDraft` mirrors the schema documented in `docs/project-context.md`. It is
the in-process contract between the Gemini-facing parser and the confirm-screen
template. `ParsedResponse` wraps drafts plus an optional recurring intent so
Story 4 (recurring) can wire in without a second round-trip.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date as _date_type
from decimal import Decimal


@dataclass
class VoiceDraft:
    """A single parsed transaction candidate from a voice clip."""

    type: str
    amount: Decimal
    currency: str
    category_slug: str
    counterparty: str | None
    date: _date_type
    note: str | None
    confidence: float
    ambiguous_fields: list[str] = field(default_factory=list)

    @property
    def is_uncertain(self) -> bool:
        """UX-DR uncertainty styling trigger — Story 2.4."""
        return bool(self.ambiguous_fields) or self.confidence < 0.7


@dataclass
class ParsedResponse:
    """Top-level shape returned by `transcribe_and_parse_async`."""

    transactions: list[VoiceDraft] = field(default_factory=list)
    recurring_intent: VoiceDraft | None = None
