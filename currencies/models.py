"""ExchangeRate cache for CBU.uz daily rates (Story 5.2).

Storage model: one row per (currency, date). `rate_to_uzs` is how many UZS one
unit of `currency` is worth — the canonical pivot. We never store UZS→UZS;
that's an identity handled by the converter.
"""

from __future__ import annotations

from django.db import models

from currencies.constants import CURRENCY_CODES

# Sources of truth for currency rates. CBU.uz today, more later (NBU/parallel).
SOURCE_CBU = "cbu.uz"

SOURCE_CHOICES = [
    (SOURCE_CBU, "CBU.uz"),
]

# Rates can be in the millions of UZS per unit if some exotic currency ever
# sneaks in, and we want 6 decimal places for accuracy on RUB/USD conversion.
RATE_MAX_DIGITS = 15
RATE_DECIMAL_PLACES = 6


class ExchangeRate(models.Model):
    """A single CBU.uz daily rate for one currency-vs-UZS pair.

    Conversions through non-UZS pairs are computed via UZS as a pivot at runtime
    by the `currencies.services.convert_for_display` helper — we never persist a
    USD↔RUB row.
    """

    id = models.BigAutoField(primary_key=True)
    currency = models.CharField(max_length=3, choices=[(c, c) for c in CURRENCY_CODES])
    rate_to_uzs = models.DecimalField(
        max_digits=RATE_MAX_DIGITS,
        decimal_places=RATE_DECIMAL_PLACES,
    )
    date = models.DateField()
    source = models.CharField(max_length=16, choices=SOURCE_CHOICES, default=SOURCE_CBU)
    fetched_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "currencies_exchangerate"
        ordering = ["-date", "currency"]
        constraints = [
            models.UniqueConstraint(
                fields=["currency", "date"],
                name="currencies_rate_unique_currency_date",
            ),
            models.CheckConstraint(
                condition=models.Q(rate_to_uzs__gt=0),
                name="currencies_rate_positive",
            ),
        ]
        indexes = [
            models.Index(fields=["currency", "-date"]),
        ]

    def __str__(self) -> str:
        return f"1 {self.currency} = {self.rate_to_uzs} UZS @ {self.date}"
