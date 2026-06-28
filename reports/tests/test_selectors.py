"""Story 8.1 — reports selectors aggregation tests.

Pinning behavior is the goal: every shape returned by ``weekly_summary``,
``monthly_summary``, and ``yearly_summary`` must remain stable so the view +
template layers can keep their thin context-mapping shape.

Coverage targets the AC checklist: empty period, single tx, multi-currency
present (with + without rates), include_debts toggle, partial yearly, Boshqalar
collapsing, and "fewer than 5 queries" via ``django_assert_max_num_queries``.
"""

from datetime import date
from decimal import Decimal

import pytest

from currencies.models import ExchangeRate
from reports.selectors import (
    monthly_summary,
    weekly_summary,
    yearly_summary,
)
from transactions.tests.factories import TransactionFactory, UserFactory


def _seed_rates(today: date) -> None:
    ExchangeRate.objects.create(currency="USD", rate_to_uzs=Decimal("12500.00"), date=today)
    ExchangeRate.objects.create(currency="RUB", rate_to_uzs=Decimal("125.00"), date=today)


# ---------- weekly_summary ----------


@pytest.mark.django_db
def test_weekly_empty_user_returns_zeros() -> None:
    user = UserFactory()
    anchor = date(2026, 6, 17)  # Wednesday
    summary = weekly_summary(user, anchor, "UZS", today=anchor)
    assert summary.start == date(2026, 6, 15)  # Monday of that week
    assert summary.end == date(2026, 6, 21)
    assert summary.total_income == Decimal("0.00")
    assert summary.total_expense == Decimal("0.00")
    assert summary.by_category == []
    assert summary.transaction_count == 0
    assert summary.is_empty is True
    # 7 day points always emitted, even if empty.
    assert len(summary.by_day) == 7
    assert all(p.total == Decimal("0.00") for p in summary.by_day)


@pytest.mark.django_db
def test_weekly_window_is_monday_to_sunday() -> None:
    user = UserFactory()
    # Sunday — week_bounds should snap back to the preceding Monday.
    anchor = date(2026, 6, 21)
    summary = weekly_summary(user, anchor, "UZS", today=anchor)
    assert summary.start == date(2026, 6, 15)
    assert summary.end == date(2026, 6, 21)


@pytest.mark.django_db
def test_weekly_includes_inside_excludes_outside() -> None:
    user = UserFactory()
    TransactionFactory(user=user, type="expense", amount=Decimal("100"), date=date(2026, 6, 14))
    TransactionFactory(user=user, type="expense", amount=Decimal("200"), date=date(2026, 6, 15))
    TransactionFactory(user=user, type="expense", amount=Decimal("300"), date=date(2026, 6, 21))
    TransactionFactory(user=user, type="expense", amount=Decimal("400"), date=date(2026, 6, 22))
    summary = weekly_summary(user, date(2026, 6, 17), "UZS", today=date(2026, 6, 17))
    assert summary.total_expense == Decimal("500.00")  # only 15 and 21
    assert summary.transaction_count == 2


@pytest.mark.django_db
def test_weekly_top_categories_with_boshqalar_collapse() -> None:
    from categories.models import Category

    user = UserFactory()
    expense_cats = list(
        Category.objects.filter(user__isnull=True, type="expense").order_by("name")[:8]
    )
    assert len(expense_cats) >= 7, "preset fixtures must seed at least 7 expense categories"
    # 7 distinct categories, descending amounts.
    for i, cat in enumerate(expense_cats[:7]):
        TransactionFactory(
            user=user,
            type="expense",
            amount=Decimal(700 - i * 100),
            category=cat,
            date=date(2026, 6, 17),
        )
    summary = weekly_summary(user, date(2026, 6, 17), "UZS", today=date(2026, 6, 17))
    # Top 6 + Boshqalar.
    assert len(summary.by_category) == 7
    assert summary.by_category[-1].slug == "__other__"
    assert summary.by_category[-1].name == "Boshqalar"
    # Percentages should sum to ~100.
    pct_sum = sum((c.percent for c in summary.by_category), Decimal("0"))
    assert abs(pct_sum - Decimal("100.0")) <= Decimal("0.5")


@pytest.mark.django_db
def test_weekly_include_debts_toggles_lent_into_expense() -> None:
    user = UserFactory()
    anchor = date(2026, 6, 17)
    TransactionFactory(user=user, type="expense", amount=Decimal("100"), date=anchor)
    TransactionFactory(
        user=user,
        type="debt_lent",
        amount=Decimal("500"),
        counterparty="Akram",
        date=anchor,
    )
    plain = weekly_summary(user, anchor, "UZS", today=anchor)
    with_debts = weekly_summary(user, anchor, "UZS", include_debts=True, today=anchor)
    assert plain.total_expense == Decimal("100.00")
    assert with_debts.total_expense == Decimal("600.00")


@pytest.mark.django_db
def test_weekly_multi_currency_conversion() -> None:
    user = UserFactory()
    anchor = date(2026, 6, 17)
    _seed_rates(anchor)
    TransactionFactory(
        user=user, type="expense", amount=Decimal("100"), currency="USD", date=anchor
    )
    TransactionFactory(
        user=user, type="expense", amount=Decimal("10000"), currency="RUB", date=anchor
    )
    summary = weekly_summary(user, anchor, "UZS", today=anchor)
    # 100 * 12500 + 10000 * 125 = 1_250_000 + 1_250_000 = 2_500_000
    assert summary.total_expense == Decimal("2500000.00")
    assert summary.is_fully_supported is True


@pytest.mark.django_db
def test_weekly_missing_rate_marks_not_fully_supported() -> None:
    user = UserFactory()
    anchor = date(2026, 6, 17)
    TransactionFactory(
        user=user, type="expense", amount=Decimal("100"), currency="USD", date=anchor
    )
    summary = weekly_summary(user, anchor, "UZS", today=anchor)
    assert summary.is_fully_supported is False


@pytest.mark.django_db
def test_weekly_user_isolation() -> None:
    a = UserFactory()
    b = UserFactory()
    anchor = date(2026, 6, 17)
    TransactionFactory(user=a, type="expense", amount=Decimal("100"), date=anchor)
    summary = weekly_summary(b, anchor, "UZS", today=anchor)
    assert summary.transaction_count == 0


@pytest.mark.django_db
def test_weekly_query_budget(django_assert_max_num_queries) -> None:
    user = UserFactory()
    anchor = date(2026, 6, 17)
    for _ in range(10):
        TransactionFactory(user=user, type="expense", amount=Decimal("10"), date=anchor)
    # period_totals + category breakdown + daily points + count = 4 SELECTs.
    with django_assert_max_num_queries(5):
        weekly_summary(user, anchor, "UZS", today=anchor)


# ---------- monthly_summary ----------


@pytest.mark.django_db
def test_monthly_empty_returns_zeros() -> None:
    user = UserFactory()
    summary = monthly_summary(user, 2026, 6, "UZS", today=date(2026, 6, 1))
    assert summary.year == 2026
    assert summary.month == 6
    assert summary.total_expense == Decimal("0.00")
    assert summary.is_empty is True
    assert summary.top_5_expenses == []


@pytest.mark.django_db
def test_monthly_totals_and_top_5() -> None:
    from categories.models import Category

    user = UserFactory()
    cats = list(Category.objects.filter(user__isnull=True, type="expense").order_by("name")[:5])
    for i, cat in enumerate(cats):
        TransactionFactory(
            user=user,
            type="expense",
            amount=Decimal(500 - i * 50),
            category=cat,
            date=date(2026, 6, 5 + i),
        )
    TransactionFactory(user=user, type="income", amount=Decimal("5000"), date=date(2026, 6, 1))
    summary = monthly_summary(user, 2026, 6, "UZS", today=date(2026, 6, 15))
    assert summary.total_income == Decimal("5000.00")
    # 500+450+400+350+300 = 2000
    assert summary.total_expense == Decimal("2000.00")
    assert len(summary.top_5_expenses) == 5
    # Top must be the 500 row.
    assert summary.top_5_expenses[0].amount == Decimal("500.00")


@pytest.mark.django_db
def test_monthly_per_currency_split_present_when_multi_currency() -> None:
    user = UserFactory()
    today = date(2026, 6, 15)
    _seed_rates(today)
    TransactionFactory(
        user=user, type="income", amount=Decimal("1000000"), currency="UZS", date=date(2026, 6, 5)
    )
    TransactionFactory(
        user=user, type="income", amount=Decimal("100"), currency="USD", date=date(2026, 6, 6)
    )
    summary = monthly_summary(user, 2026, 6, "UZS", today=today)
    codes = {row.currency for row in summary.per_currency}
    assert codes == {"UZS", "USD"}


@pytest.mark.django_db
def test_monthly_query_budget(django_assert_max_num_queries) -> None:
    user = UserFactory()
    for d in range(1, 28):
        TransactionFactory(user=user, type="expense", amount=Decimal("10"), date=date(2026, 6, d))
    with django_assert_max_num_queries(5):
        monthly_summary(user, 2026, 6, "UZS", today=date(2026, 6, 28))


# ---------- yearly_summary ----------


@pytest.mark.django_db
def test_yearly_emits_12_months_always() -> None:
    user = UserFactory()
    summary = yearly_summary(user, 2026, "UZS", today=date(2026, 6, 15))
    assert len(summary.by_month) == 12
    assert all(p.has_data is False for p in summary.by_month)
    assert summary.is_empty is True
    assert summary.is_partial is True
    assert summary.most_expensive_month is None


@pytest.mark.django_db
def test_yearly_partial_under_three_months() -> None:
    user = UserFactory()
    TransactionFactory(user=user, type="expense", amount=Decimal("100"), date=date(2026, 1, 5))
    TransactionFactory(user=user, type="expense", amount=Decimal("200"), date=date(2026, 2, 5))
    summary = yearly_summary(user, 2026, "UZS", today=date(2026, 6, 15))
    assert summary.months_with_data == 2
    assert summary.is_partial is True
    assert summary.is_empty is False


@pytest.mark.django_db
def test_yearly_six_months_not_partial_and_most_expensive_month_correct() -> None:
    user = UserFactory()
    # April is the spike month.
    spends = {1: 100, 2: 200, 3: 150, 4: 9000, 5: 300, 6: 400}
    for m, amt in spends.items():
        TransactionFactory(user=user, type="expense", amount=Decimal(amt), date=date(2026, m, 5))
    summary = yearly_summary(user, 2026, "UZS", today=date(2026, 6, 30))
    assert summary.months_with_data == 6
    assert summary.is_partial is False
    assert summary.most_expensive_month is not None
    assert summary.most_expensive_month.month == 4
    assert summary.most_expensive_month.expense == Decimal("9000.00")


@pytest.mark.django_db
def test_yearly_previous_year_comparison_when_data_exists() -> None:
    user = UserFactory()
    TransactionFactory(user=user, type="expense", amount=Decimal("1000"), date=date(2025, 5, 5))
    TransactionFactory(user=user, type="expense", amount=Decimal("2000"), date=date(2026, 5, 5))
    summary = yearly_summary(user, 2026, "UZS", today=date(2026, 6, 1))
    assert summary.previous_year_total_expense == Decimal("1000.00")


@pytest.mark.django_db
def test_yearly_previous_year_none_when_no_prev_data() -> None:
    user = UserFactory()
    TransactionFactory(user=user, type="expense", amount=Decimal("2000"), date=date(2026, 5, 5))
    summary = yearly_summary(user, 2026, "UZS", today=date(2026, 6, 1))
    assert summary.previous_year_total_expense is None


@pytest.mark.django_db
def test_yearly_full_12_months_complete() -> None:
    user = UserFactory()
    for m in range(1, 13):
        TransactionFactory(
            user=user, type="expense", amount=Decimal(100 * m), date=date(2026, m, 5)
        )
    summary = yearly_summary(user, 2026, "UZS", today=date(2026, 12, 31))
    assert summary.months_with_data == 12
    # 100 + 200 + ... + 1200 = 7800
    assert summary.total_expense == Decimal("7800.00")
    assert summary.most_expensive_month.month == 12
