"""Story 1.4 — ManualTransactionForm validation."""

from datetime import date
from decimal import Decimal

import pytest
from django.core.management import call_command

from transactions.forms import ManualTransactionForm
from transactions.tests.factories import UserFactory


def _baseline(type_: str = "expense", **overrides) -> dict:
    data = {
        "type": type_,
        "amount": "25000.00",
        "currency": "UZS",
        "date": date.today().isoformat(),
        "note": "",
        "category_slug": "",
        "counterparty": "",
    }
    data.update(overrides)
    return data


@pytest.mark.django_db
def test_form_valid_with_minimum_fields() -> None:
    user = UserFactory()
    form = ManualTransactionForm(_baseline(), user=user)
    assert form.is_valid(), form.errors
    assert form.cleaned_data["amount"] == Decimal("25000.00")
    assert form.cleaned_data["currency"] == "UZS"


@pytest.mark.django_db
def test_form_rejects_zero_amount() -> None:
    user = UserFactory()
    form = ManualTransactionForm(_baseline(amount="0"), user=user)
    assert not form.is_valid()
    assert "amount" in form.errors


@pytest.mark.django_db
def test_form_rejects_negative_amount() -> None:
    user = UserFactory()
    form = ManualTransactionForm(_baseline(amount="-100"), user=user)
    assert not form.is_valid()


@pytest.mark.django_db
def test_form_requires_counterparty_for_debt_lent() -> None:
    user = UserFactory()
    form = ManualTransactionForm(_baseline(type_="debt_lent"), user=user)
    assert not form.is_valid()
    assert "counterparty" in form.errors


@pytest.mark.django_db
def test_form_requires_counterparty_for_debt_borrowed() -> None:
    user = UserFactory()
    form = ManualTransactionForm(_baseline(type_="debt_borrowed"), user=user)
    assert not form.is_valid()
    assert "counterparty" in form.errors


@pytest.mark.django_db
def test_form_accepts_debt_with_counterparty() -> None:
    user = UserFactory()
    form = ManualTransactionForm(
        _baseline(type_="debt_lent", counterparty="Akram"),
        user=user,
    )
    assert form.is_valid(), form.errors
    assert form.cleaned_data["counterparty"] == "Akram"


@pytest.mark.django_db
def test_form_resolves_known_category_slug_to_instance() -> None:
    call_command("loaddata", "categories/fixtures/preset_categories.json", verbosity=0)
    user = UserFactory()
    form = ManualTransactionForm(
        _baseline(category_slug="taxi"),
        user=user,
    )
    assert form.is_valid(), form.errors
    cat = form.cleaned_data["category"]
    assert cat is not None
    assert cat.slug == "taxi"


@pytest.mark.django_db
def test_form_category_resolves_to_none_when_slug_unknown() -> None:
    user = UserFactory()
    form = ManualTransactionForm(
        _baseline(category_slug="does-not-exist"),
        user=user,
    )
    assert form.is_valid()
    assert form.cleaned_data["category"] is None


@pytest.mark.django_db
def test_form_category_helper_returns_user_categories_for_expense() -> None:
    call_command("loaddata", "categories/fixtures/preset_categories.json", verbosity=0)
    user = UserFactory()
    form = ManualTransactionForm(user=user)
    choices = list(form.category_choices_for_type("expense"))
    assert any(c.slug == "taxi" for c in choices)
    assert all(c.type == "expense" for c in choices)


@pytest.mark.django_db
def test_form_category_helper_returns_empty_for_debt_types() -> None:
    user = UserFactory()
    form = ManualTransactionForm(user=user)
    assert list(form.category_choices_for_type("debt_lent")) == []
    assert list(form.category_choices_for_type("debt_borrowed")) == []
