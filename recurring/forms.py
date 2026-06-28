"""Form for create/edit of a RecurringSchedule (Epic 7 / Story 7.2).

Plain Form (not ModelForm) so we compose with services.py — services own
invariants, this form only validates shape.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django import forms

from currencies.constants import CURRENCY_CHOICES
from recurring.models import RecurringType, ScheduleKind

WEEKDAY_CHOICES = [
    (0, "Dushanba"),
    (1, "Seshanba"),
    (2, "Chorshanba"),
    (3, "Payshanba"),
    (4, "Juma"),
    (5, "Shanba"),
    (6, "Yakshanba"),
]


class RecurringForm(forms.Form):
    """Create / edit a recurring schedule.

    `category_slug` is the picker output (matches Story 3.2 picker contract).
    Numeric inputs come in as strings from the htmx POST and get coerced here.
    """

    type = forms.ChoiceField(
        choices=RecurringType.choices,
        label="Turi",
    )
    name = forms.CharField(
        max_length=64,
        label="Nom",
        error_messages={
            "required": "Nomni kiriting.",
            "max_length": "Nom juda uzun (64 belgidan ortiq).",
        },
    )
    amount = forms.CharField(
        label="Summa",
        error_messages={"required": "Summani kiriting."},
    )
    currency = forms.ChoiceField(
        choices=CURRENCY_CHOICES,
        initial="UZS",
        label="Valyuta",
    )
    category_slug = forms.CharField(required=False, max_length=64)

    schedule_kind = forms.ChoiceField(
        choices=ScheduleKind.choices,
        initial=ScheduleKind.MONTHLY.value,
        label="Davriylik",
    )
    day_of_month = forms.IntegerField(
        min_value=1,
        max_value=31,
        required=False,
        label="Oy kuni",
    )
    day_of_week = forms.TypedChoiceField(
        choices=[("", "—"), *[(str(v), label) for v, label in WEEKDAY_CHOICES]],
        coerce=lambda v: int(v) if v not in (None, "") else None,
        required=False,
        empty_value=None,
        label="Hafta kuni",
    )

    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
        label="Tugash sanasi (ixtiyoriy)",
    )

    def clean_name(self) -> str:
        name = (self.cleaned_data.get("name") or "").strip()
        if not name:
            raise forms.ValidationError("Nomni kiriting.")
        return name

    def clean_amount(self) -> Decimal:
        raw = (self.cleaned_data.get("amount") or "").strip().replace(" ", "").replace(",", ".")
        if not raw:
            raise forms.ValidationError("Summani kiriting.")
        try:
            value = Decimal(raw)
        except InvalidOperation as exc:
            raise forms.ValidationError("Summa noto'g'ri.") from exc
        if value <= 0:
            raise forms.ValidationError("Summa musbat bo'lishi kerak.")
        return value

    def clean(self) -> dict:
        cleaned = super().clean()
        kind = cleaned.get("schedule_kind")
        if kind == ScheduleKind.MONTHLY.value and not cleaned.get("day_of_month"):
            self.add_error("day_of_month", "Oylik takror uchun kunni (1-31) tanlang.")
        if kind == ScheduleKind.WEEKLY.value and cleaned.get("day_of_week") is None:
            self.add_error("day_of_week", "Haftalik takror uchun hafta kunini tanlang.")
        return cleaned
