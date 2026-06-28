"""Voice domain dataclasses (Story 2.3 + 6.1/6.3).

`VoiceDraft` mirrors the schema documented in `docs/project-context.md`. It is
the in-process contract between the Gemini-facing parser and the confirm-screen
template. `ParsedResponse` wraps drafts plus an optional recurring intent so
Epic 6 / Story 6.3 (recurring) can wire in without a second round-trip.

`RecurringHint` is the optional cadence hint attached to `recurring_intent`.
It carries the structured cadence the parser inferred from phrases like
"har oy 1-sanasida", "har dushanba" or "har 3 kunda". The hint maps cleanly
onto :func:`recurring.services.create_recurring`'s `schedule_kind` /
`day_of_month` / `day_of_week` parameters so Story 6.3's confirm screen can
hand it straight through without a second normalize step.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date as _date_type
from decimal import Decimal


@dataclass
class RecurringHint:
    """Cadence + bookkeeping inferred for a `recurring_intent` draft.

    `schedule_kind` is one of "monthly" / "weekly" / "every_n_days" — the first
    two map directly onto `recurring.models.ScheduleKind`, the third is parsed
    only so we can show the user a polite "har N kunda" string on the confirm
    card. Epic 7's RecurringSchedule doesn't model every-N-days yet (AC), so
    Story 6.3 falls back to `weekly` (with `every_n_days == 7`) or surfaces an
    inline note when N is something else.
    """

    schedule_kind: str
    day_of_month: int | None = None
    day_of_week: int | None = None
    every_n_days: int | None = None


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
    recurring_hint: RecurringHint | None = None

    @property
    def is_uncertain(self) -> bool:
        """UX-DR uncertainty styling trigger — Story 2.4."""
        return bool(self.ambiguous_fields) or self.confidence < 0.7


@dataclass
class ParsedResponse:
    """Top-level shape returned by `transcribe_and_parse_async`."""

    transactions: list[VoiceDraft] = field(default_factory=list)
    recurring_intent: VoiceDraft | None = None
