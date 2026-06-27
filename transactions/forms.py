"""Manual transaction entry form (Story 1.4)."""

from datetime import date as _date_type
from decimal import Decimal

from django import forms

from accounts.models import CURRENCY_CHOICES
from categories.selectors import categories_for, match_slug

from .models import TransactionType

DEBT_TYPES = {TransactionType.DEBT_LENT.value, TransactionType.DEBT_BORROWED.value}
CATEGORY_TYPES = {TransactionType.INCOME.value, TransactionType.EXPENSE.value}


class ManualTransactionForm(forms.Form):
    """User-facing form for manual entry.

    Kept as a plain Form (not ModelForm) so we can compose with services.py
    (project-context — business logic stays in services).
    """

    type = forms.ChoiceField(
        choices=TransactionType.choices,
        widget=forms.RadioSelect,
        label="Turi",
    )
    category_slug = forms.CharField(
        max_length=64,
        required=False,
        label="Kategoriya",
    )
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
    currency = forms.ChoiceField(
        choices=CURRENCY_CHOICES,
        initial="UZS",
        label="Valyuta",
    )
    date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
        label="Sana",
    )
    note = forms.CharField(
        max_length=500,
        required=False,
        widget=forms.Textarea(attrs={"rows": 2}),
        label="Izoh",
    )
    counterparty = forms.CharField(
        max_length=64,
        required=False,
        label="Kim bilan",
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        if "date" in self.initial and self.initial["date"] is None:
            self.initial["date"] = _date_type.today()

    def clean(self) -> dict:
        cleaned = super().clean()
        type_ = cleaned.get("type")
        counterparty = (cleaned.get("counterparty") or "").strip()

        if type_ in DEBT_TYPES and not counterparty:
            self.add_error("counterparty", "Kim bilan ekanini yozing (masalan: Akram).")

        # Resolve category_slug to a Category instance if applicable.
        category_slug = (cleaned.get("category_slug") or "").strip()
        if type_ in CATEGORY_TYPES and category_slug and self.user is not None:
            cleaned["category"] = match_slug(self.user, slug=category_slug, type=type_)
        else:
            cleaned["category"] = None

        return cleaned

    def category_choices_for_type(self, type_: str):
        """Helper used by template to render the category picker."""
        if type_ not in CATEGORY_TYPES or self.user is None:
            return []
        return categories_for(self.user, type_)
