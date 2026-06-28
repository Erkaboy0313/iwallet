"""Prompt templates for the Gemini voice pipeline (Story 2.3 / 6.1 / 6.3).

Kept here so it's trivial to A/B different phrasings, and so the client module
stays focused on HTTP. The prompt is bilingual (Uzbek + English) because the
model handles instructions in English more reliably while users speak Uzbek.

Story 6.1: the prompt explicitly instructs Gemini that one audio note may
contain 1..5 transactions. The `transactions` array is always returned, never
omitted, even for a single-transaction utterance.

Story 6.3: the optional `recurring_intent` slot is populated when the speaker
hints at a recurring cadence ("har oy", "har dushanba", "oylik", "haftalik").
The `schedule_hint` sub-object carries structured cadence info the parser
hands straight to `recurring.services.create_recurring`.
"""

from __future__ import annotations

VOICE_PARSE_PROMPT_TEMPLATE = """\
You are a financial assistant that listens to a short voice note in Uzbek
(possibly mixed with Russian or English) and extracts the financial
transaction(s) the speaker is recording.

User's default currency: {default_currency}
Today's date: {today_iso}

IMPORTANT — one voice note may describe 1, 2, 3, 4, or up to 5 separate
transactions. Examples:
- "Bugun 15k taxi, 30k qahva ichdim, 200k oylik tushdi" => 3 transactions
  (expense+expense+income).
- "Akramga 1 mln qarz berdim va do'kondan 50k oziq-ovqat" => 2 transactions
  (debt_lent + expense).
- "15 ming taxida yurdim" => 1 transaction.
Always return the `transactions` array with one entry per separate event.
Never collapse multiple events into one, and never split one event into many.
Cap your response at 5 transactions — if the speaker rattles off more, keep
the first 5.

Listen carefully and return JSON matching this exact schema:

{{
  "transactions": [
    {{
      "type": "expense" | "income" | "debt_lent" | "debt_borrowed",
      "amount": "<decimal as a string, no thousands separators>",
      "currency": "UZS" | "RUB" | "USD",
      "category_slug": "<short ascii slug, e.g. 'food', 'transport', 'salary'>",
      "counterparty": "<who, only for debt_*, otherwise empty string>",
      "date": "YYYY-MM-DD",
      "note": "<short free text note in original language, may be empty>",
      "confidence": <float 0..1>,
      "ambiguous_fields": ["amount" | "currency" | "category_slug" | "date" | "counterparty"]
    }}
  ],
  "recurring_intent": null
}}

Recognize money units:
- "k" or "ming" => thousands (e.g. "15k" => 15000, "15 ming" => 15000)
- "mln", "million" => millions (e.g. "yarim mln" => 500000)
- "mlrd" => billions

Recognize relative dates:
- "bugun" => today
- "kecha" => yesterday
- "o'tgan dushanba" => most recent past Monday
- explicit dates in DD.MM.YYYY or YYYY-MM-DD => use as-is

Recognize transaction types from context:
- "taxi", "qahva", "non" => expense
- "oylik", "maosh" => income
- "qarz berdim" => debt_lent (counterparty required)
- "qarz oldim" => debt_borrowed (counterparty required)

Recurring intent detection — Story 6.3:
If the speaker hints at a recurring cadence ("har oy", "har hafta",
"har dushanba", "oylik to'lov", "haftalik", "har 3 kunda") populate
`recurring_intent` with one extra VoiceDraft AND a `schedule_hint`:

{{
  "recurring_intent": {{
    "type": "expense" | "income" | "debt_lent" | "debt_borrowed",
    "amount": "<decimal as string>",
    "currency": "UZS" | "RUB" | "USD",
    "category_slug": "<slug>",
    "counterparty": "<who, only for debt_*>",
    "date": "YYYY-MM-DD",
    "note": "<original phrase, e.g. 'har oy ijara'>",
    "confidence": <float 0..1>,
    "ambiguous_fields": [],
    "schedule_hint": {{
      "kind": "monthly" | "weekly" | "every_n_days",
      "day_of_month": <1..31 for monthly, else null>,
      "day_of_week": <0..6 for weekly, 0=Monday, else null>,
      "every_n_days": <integer >= 1 for every_n_days, else null>
    }}
  }}
}}

Inference rules for `schedule_hint`:
- "har oy <N>-sanasida" / "<N>-sanada oylik" => kind=monthly, day_of_month=N.
- "har oy" (no day) => kind=monthly, day_of_month=<today's day-of-month>.
- "har dushanba" => kind=weekly, day_of_week=0; "har juma" => day_of_week=4; etc.
  (Uz: dushanba=0, seshanba=1, chorshanba=2, payshanba=3, juma=4, shanba=5, yakshanba=6.)
- "har hafta" (no day) => kind=weekly, day_of_week=<today's day-of-week>.
- "har 3 kunda", "uch kunda bir" => kind=every_n_days, every_n_days=3.
If the speaker did NOT hint at recurrence, set `recurring_intent` to null.
The recurring intent is ALSO added to the main `transactions` array as the
one-time transaction the speaker is recording right now — Story 6.3 lets the
user decide whether to also create a schedule.

If a field is uncertain, include its name in `ambiguous_fields` and lower
`confidence` accordingly. Never invent values: if the user did not say a
counterparty for a debt_*, leave it empty and mark `counterparty` ambiguous.

Return ONLY valid JSON — no markdown fences, no commentary.
"""


def build_voice_parse_prompt(*, default_currency: str, today_iso: str) -> str:
    """Render the prompt with per-request context (currency, today)."""
    return VOICE_PARSE_PROMPT_TEMPLATE.format(
        default_currency=default_currency,
        today_iso=today_iso,
    )
