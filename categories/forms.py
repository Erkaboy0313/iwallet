"""Category CRUD form (Epic 3 — Story 3.1)."""

from django import forms

from .models import CategoryType


class CategoryForm(forms.Form):
    """Create / edit form for a custom category.

    Plain Form (not ModelForm) so we compose with services.py — services own
    invariants, this form only validates shape.
    """

    type = forms.ChoiceField(
        choices=CategoryType.choices,
        widget=forms.RadioSelect,
        label="Turi",
    )
    name = forms.CharField(
        max_length=64,
        label="Nom",
        error_messages={
            "required": "Kategoriya nomini kiriting.",
            "max_length": "Kategoriya nomi juda uzun (64 belgidan ortiq).",
        },
    )
    emoji = forms.CharField(
        max_length=8,
        required=False,
        initial="📌",
        label="Belgi",
    )

    def clean_name(self) -> str:
        name = (self.cleaned_data.get("name") or "").strip()
        if not name:
            raise forms.ValidationError("Kategoriya nomini kiriting.")
        return name

    def clean_emoji(self) -> str:
        emoji = (self.cleaned_data.get("emoji") or "").strip()
        return emoji or "📌"
