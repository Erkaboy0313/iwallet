"""Story 1.5 — month_summary selector tests."""

from datetime import date
from decimal import Decimal

import pytest

from transactions.selectors import all_time_cash_balance, all_time_totals, month_summary
from transactions.tests.factories import TransactionFactory, UserFactory


@pytest.mark.django_db
def test_empty_user_returns_zero_balance() -> None:
    user = UserFactory()
    summary = month_summary(user, "UZS", today=date(2026, 6, 15))
    assert summary.cash_balance == Decimal("0")
    assert summary.is_empty is True
    assert summary.top_categories == []


@pytest.mark.django_db
def test_cash_balance_is_income_minus_expense() -> None:
    user = UserFactory()
    TransactionFactory(user=user, type="income", amount=Decimal("1000000"), date=date(2026, 6, 5))
    TransactionFactory(user=user, type="expense", amount=Decimal("250000"), date=date(2026, 6, 10))

    summary = month_summary(user, "UZS", today=date(2026, 6, 15))
    assert summary.total_income == Decimal("1000000")
    assert summary.total_expense == Decimal("250000")
    assert summary.cash_balance == Decimal("750000")
    assert summary.is_empty is False


@pytest.mark.django_db
def test_other_months_excluded() -> None:
    user = UserFactory()
    TransactionFactory(user=user, type="expense", amount=Decimal("9999"), date=date(2026, 5, 31))
    TransactionFactory(user=user, type="expense", amount=Decimal("100"), date=date(2026, 6, 15))
    summary = month_summary(user, "UZS", today=date(2026, 6, 15))
    assert summary.total_expense == Decimal("100")
    assert summary.transaction_count == 1


@pytest.mark.django_db
def test_other_currency_excluded() -> None:
    user = UserFactory()
    TransactionFactory(
        user=user,
        type="income",
        amount=Decimal("1000"),
        currency="USD",
        date=date(2026, 6, 5),
    )
    TransactionFactory(
        user=user,
        type="income",
        amount=Decimal("500"),
        currency="UZS",
        date=date(2026, 6, 5),
    )
    summary = month_summary(user, "UZS", today=date(2026, 6, 15))
    assert summary.total_income == Decimal("500")


@pytest.mark.django_db
def test_cash_balance_includes_debts_sprint_v0_5() -> None:
    """Borrow → cash in. Lend → cash out. The standing obligation is tracked
    separately by debts.selectors.debt_status_summary; this selector only
    describes the cash flow for the month.
    """
    user = UserFactory()
    TransactionFactory(user=user, type="income", amount=Decimal("100"), date=date(2026, 6, 1))
    TransactionFactory(user=user, type="expense", amount=Decimal("50"), date=date(2026, 6, 2))
    TransactionFactory(
        user=user,
        type="debt_lent",
        amount=Decimal("999"),
        counterparty="X",
        date=date(2026, 6, 3),
    )
    TransactionFactory(
        user=user,
        type="debt_borrowed",
        amount=Decimal("888"),
        counterparty="Y",
        date=date(2026, 6, 4),
    )
    summary = month_summary(user, "UZS", today=date(2026, 6, 15))
    # 100 (income) + 888 (borrowed) - 50 (expense) - 999 (lent) = -61
    assert summary.cash_balance == Decimal("-61")
    assert summary.inflow_total == Decimal("988")
    assert summary.outflow_total == Decimal("1049")
    assert summary.total_debt_borrowed == Decimal("888")
    assert summary.total_debt_lent == Decimal("999")


@pytest.mark.django_db
def test_top_categories_orders_by_total_desc_and_caps_at_three() -> None:
    # Preset categories are seeded by the data migration; no fixture load needed.
    from categories.models import Category

    user = UserFactory()
    taxi = Category.objects.filter(user__isnull=True, type="expense", slug="taxi").first()
    qahva = Category.objects.filter(user__isnull=True, type="expense", slug="qahva_kafe").first()
    oziq = Category.objects.filter(user__isnull=True, type="expense", slug="oziq_ovqat").first()
    transport = Category.objects.filter(user__isnull=True, type="expense", slug="transport").first()

    TransactionFactory(
        user=user, type="expense", amount=Decimal("400"), category=taxi, date=date(2026, 6, 1)
    )
    TransactionFactory(
        user=user, type="expense", amount=Decimal("300"), category=qahva, date=date(2026, 6, 2)
    )
    TransactionFactory(
        user=user, type="expense", amount=Decimal("200"), category=oziq, date=date(2026, 6, 3)
    )
    TransactionFactory(
        user=user, type="expense", amount=Decimal("100"), category=transport, date=date(2026, 6, 4)
    )

    summary = month_summary(user, "UZS", today=date(2026, 6, 15))
    assert len(summary.top_categories) == 3
    assert [c.slug for c in summary.top_categories] == ["taxi", "qahva_kafe", "oziq_ovqat"]
    assert summary.top_categories[0].total == Decimal("400")


@pytest.mark.django_db
def test_all_time_totals_splits_operating_receivable_payable() -> None:
    """Sprint v0.8 hero split — debts must not be conflated with operating cash."""
    user = UserFactory()
    # Operating side: income minus expense = 800.
    TransactionFactory(user=user, type="income", amount=Decimal("1000"), date=date(2026, 5, 10))
    TransactionFactory(user=user, type="expense", amount=Decimal("200"), date=date(2026, 5, 12))
    # Debt side: two open positions, kept separate from operating.
    TransactionFactory(
        user=user,
        type="debt_lent",
        amount=Decimal("300"),
        counterparty="Karim",
        date=date(2026, 5, 14),
    )
    TransactionFactory(
        user=user,
        type="debt_lent",
        amount=Decimal("50"),
        counterparty="Ali",
        date=date(2026, 5, 15),
    )
    TransactionFactory(
        user=user,
        type="debt_borrowed",
        amount=Decimal("400"),
        counterparty="Sardor",
        date=date(2026, 5, 16),
    )

    totals = all_time_totals(user, "UZS")
    assert totals.operating == Decimal("800")
    assert totals.receivable == Decimal("350")
    assert totals.payable == Decimal("400")


@pytest.mark.django_db
def test_all_time_totals_empty_user_is_zero() -> None:
    user = UserFactory()
    totals = all_time_totals(user, "UZS")
    assert totals.operating == Decimal("0")
    assert totals.receivable == Decimal("0")
    assert totals.payable == Decimal("0")


@pytest.mark.django_db
def test_all_time_totals_isolates_by_currency() -> None:
    user = UserFactory()
    TransactionFactory(
        user=user, type="income", amount=Decimal("1000"), currency="UZS", date=date(2026, 5, 1)
    )
    TransactionFactory(
        user=user, type="income", amount=Decimal("500"), currency="USD", date=date(2026, 5, 1)
    )
    TransactionFactory(
        user=user,
        type="debt_lent",
        amount=Decimal("100"),
        counterparty="X",
        currency="USD",
        date=date(2026, 5, 2),
    )
    totals_uzs = all_time_totals(user, "UZS")
    totals_usd = all_time_totals(user, "USD")
    assert totals_uzs.operating == Decimal("1000")
    assert totals_uzs.receivable == Decimal("0")
    assert totals_usd.operating == Decimal("500")
    assert totals_usd.receivable == Decimal("100")


# ---------- Sprint v0.8.1 — partial-repayment types ----------


@pytest.mark.django_db
def test_all_time_totals_reduces_receivable_when_debt_repaid_to_me() -> None:
    """Lent 500k, counterparty paid me back 200k → receivable 300k, cash +200k."""
    user = UserFactory()
    TransactionFactory(
        user=user,
        type="debt_lent",
        amount=Decimal("500000"),
        counterparty="Karim",
        date=date(2026, 5, 10),
    )
    TransactionFactory(
        user=user,
        type="debt_repaid_to_me",
        amount=Decimal("200000"),
        counterparty="Karim",
        date=date(2026, 5, 20),
    )
    totals = all_time_totals(user, "UZS")
    assert totals.receivable == Decimal("300000")
    assert totals.payable == Decimal("0")
    # debt_lent -500k, debt_repaid_to_me +200k = net -300k cash flow. The
    # story's headline "cash=+200k" describes the repayment leg on its own;
    # the net position stays negative because the original lend already left
    # the wallet.
    assert all_time_cash_balance(user, "UZS") == Decimal("-300000")


@pytest.mark.django_db
def test_all_time_totals_reduces_payable_when_debt_repaid_by_me() -> None:
    """Borrowed 500k, paid 200k back → payable 300k, net cash +300k."""
    user = UserFactory()
    TransactionFactory(
        user=user,
        type="debt_borrowed",
        amount=Decimal("500000"),
        counterparty="Sardor",
        date=date(2026, 5, 10),
    )
    TransactionFactory(
        user=user,
        type="debt_repaid_by_me",
        amount=Decimal("200000"),
        counterparty="Sardor",
        date=date(2026, 5, 20),
    )
    totals = all_time_totals(user, "UZS")
    assert totals.payable == Decimal("300000")
    assert totals.receivable == Decimal("0")
    # debt_borrowed +500k (cash in), debt_repaid_by_me -200k (cash out) = +300k.
    assert all_time_cash_balance(user, "UZS") == Decimal("300000")


@pytest.mark.django_db
def test_all_time_totals_never_negative_when_overpaid() -> None:
    """Repaid > lent → receivable clamps at 0, but cash still reflects the overage."""
    user = UserFactory()
    TransactionFactory(
        user=user,
        type="debt_lent",
        amount=Decimal("100000"),
        counterparty="Karim",
        date=date(2026, 5, 10),
    )
    TransactionFactory(
        user=user,
        type="debt_repaid_to_me",
        amount=Decimal("150000"),
        counterparty="Karim",
        date=date(2026, 5, 20),
    )
    totals = all_time_totals(user, "UZS")
    assert totals.receivable == Decimal("0")
    assert totals.payable == Decimal("0")
    # Cash: -100k (lent) + 150k (repaid_to_me) = +50k. Overpayment visible.
    assert all_time_cash_balance(user, "UZS") == Decimal("50000")


@pytest.mark.django_db
def test_all_time_totals_payable_never_negative_when_overpaid_by_me() -> None:
    user = UserFactory()
    TransactionFactory(
        user=user,
        type="debt_borrowed",
        amount=Decimal("100000"),
        counterparty="Sardor",
        date=date(2026, 5, 10),
    )
    TransactionFactory(
        user=user,
        type="debt_repaid_by_me",
        amount=Decimal("150000"),
        counterparty="Sardor",
        date=date(2026, 5, 20),
    )
    totals = all_time_totals(user, "UZS")
    assert totals.payable == Decimal("0")


@pytest.mark.django_db
def test_month_summary_includes_repayment_types_in_flow_totals() -> None:
    """Repayments land in inflow/outflow like other debt types."""
    user = UserFactory()
    TransactionFactory(
        user=user,
        type="debt_repaid_to_me",
        amount=Decimal("200000"),
        counterparty="Karim",
        date=date(2026, 6, 5),
    )
    TransactionFactory(
        user=user,
        type="debt_repaid_by_me",
        amount=Decimal("150000"),
        counterparty="Sardor",
        date=date(2026, 6, 6),
    )
    TransactionFactory(user=user, type="income", amount=Decimal("50000"), date=date(2026, 6, 7))

    summary = month_summary(user, "UZS", today=date(2026, 6, 15))
    assert summary.inflow_total == Decimal("250000")  # income + repaid_to_me
    assert summary.outflow_total == Decimal("150000")  # repaid_by_me
    assert summary.cash_balance == Decimal("100000")
    assert summary.transaction_count == 3
