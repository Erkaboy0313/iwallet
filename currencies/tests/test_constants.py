"""Story 5.1 — currency constants single-source-of-truth tests."""

from currencies.constants import (
    CURRENCY_CHOICES,
    CURRENCY_CODES,
    CURRENCY_LABELS,
    currency_label,
)


def test_choices_contain_three_supported_currencies() -> None:
    codes = {code for code, _ in CURRENCY_CHOICES}
    assert codes == {"UZS", "RUB", "USD"}


def test_codes_tuple_matches_choices() -> None:
    assert CURRENCY_CODES == ("UZS", "RUB", "USD")


def test_labels_are_uzbek() -> None:
    assert CURRENCY_LABELS["UZS"] == "so'm"
    assert CURRENCY_LABELS["RUB"] == "rubl"
    assert CURRENCY_LABELS["USD"] == "dollar"


def test_currency_label_helper_returns_label() -> None:
    assert currency_label("UZS") == "so'm"
    assert currency_label("RUB") == "rubl"
    assert currency_label("USD") == "dollar"


def test_currency_label_helper_falls_back_to_code() -> None:
    assert currency_label("EUR") == "EUR"
    assert currency_label("") == ""


def test_accounts_alias_reuses_currencies_constants() -> None:
    from accounts.models import CURRENCY_CHOICES as accounts_choices

    assert accounts_choices is CURRENCY_CHOICES
