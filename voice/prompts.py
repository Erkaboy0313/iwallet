"""Prompt templates for the Gemini voice pipeline (Story 2.3).

Kept here so it's trivial to A/B different phrasings, and so the client module
stays focused on HTTP. The prompt is bilingual (Uzbek + English) because the
model handles instructions in English more reliably while users speak Uzbek.
"""

from __future__ import annotations

VOICE_PARSE_PROMPT_TEMPLATE = """\
You are a financial assistant that listens to a short voice note in Uzbek
(possibly mixed with Russian or English) and extracts the financial
transaction(s) the speaker is recording.

User's default currency: {default_currency}
Today's date: {today_iso}

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
