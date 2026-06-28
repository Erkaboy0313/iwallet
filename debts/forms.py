"""Forms for debt-related screens (Stories 4.3 + 4.4)."""

from datetime import date as _date_type
from decimal import Decimal

from django import forms

from accounts.models import CURRENCY_CHOICES

from .models import DebtDirection


class DebtCreateForm(forms.Form):
    """Manual debt creation — used as a fallback to voice (Story 4.2 placeholder)."""

    direction = forms.ChoiceField(
        choices=DebtDirection.choices,
        widget=forms.RadioSelect,
        label="Yo'nalish",
    )
    counterparty = forms.CharField(max_length=64, label="Kim bilan")
    amount = forms.DecimalField(
        max_digits=15,
        decimal_places=2,
        min_value=Decimal("0.01"),
        label="Summa",
        error_messages={
            "required": "Summani kiriting.",
            "min_value": "Summa musbat bo'lishi kerak.",
        },
    )
    currency = forms.ChoiceField(choices=CURRENCY_CHOICES, initial="UZS", label="Valyuta")
    expected_return_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
        label="Qaytarish kuni",
    )
    note = forms.CharField(
        max_length=500,
        required=False,
        widget=forms.Textarea(attrs={"rows": 2}),
        label="Izoh",
    )

    def clean_counterparty(self) -> str:
        value = (self.cleaned_data.get("counterparty") or "").strip()
        if not value:
            raise forms.ValidationError("Kim bilan ekanini yozing.")
        return value


class DebtRepayForm(forms.Form):
    """Bottom-sheet form for partial repay or full closeout (Story 4.4)."""

    amount = forms.DecimalField(
        max_digits=15,
        decimal_places=2,
        min_value=Decimal("0.01"),
        label="Summa",
        error_messages={
            "required": "Summani kiriting.",
            "min_value": "Summa musbat bo'lishi kerak.",
        },
    )
    note = forms.CharField(
        max_length=500,
        required=False,
        widget=forms.Textarea(attrs={"rows": 2}),
        label="Izoh",
    )
    repaid_on = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
        label="Qaytarilgan kun",
        initial=_date_type.today,
    )
