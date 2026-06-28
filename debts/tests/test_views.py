"""Stories 4.3 + 4.4 — view integration tests."""

from decimal import Decimal

import pytest
from django.test import Client, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from accounts.tests.test_services import BOT_TOKEN, _make_init_data
from debts.models import Debt, DebtRepayment, DebtState
from debts.tests.factories import DebtFactory


def _user(telegram_id: int = 7) -> User:
    return User.objects.create(
        telegram_id=telegram_id, first_name="Eric", onboarded_at=timezone.now()
    )


def _init(user_id: int) -> str:
    return _make_init_data(user_id=user_id)


# ---------- debts_list_view ----------


@pytest.mark.django_db
def test_debts_list_requires_auth() -> None:
    client = Client()
    response = client.get(reverse("debts:list"))
    assert response.status_code == 401


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_debts_list_renders_both_tabs_with_active_only() -> None:
    user = _user(10)
    DebtFactory(user=user, direction="lent", counterparty="Akram", state=DebtState.OPEN.value)
    DebtFactory(
        user=user,
        direction="borrowed",
        counterparty="Karim",
        state=DebtState.OPEN.value,
    )
    DebtFactory(user=user, direction="lent", counterparty="Closed", state=DebtState.CLOSED.value)

    client = Client()
    response = client.get(
        reverse("debts:list"),
        headers={"X-Telegram-InitData": _init(10)},
    )
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    assert "Menga qarzdor" in body
    assert "Men qarzdorman" in body
    assert "Akram" in body  # Active lent shown in default tab
    assert "Closed" not in body  # Closed debt excluded


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_debts_list_default_tab_is_lent() -> None:
    user = _user(11)
    DebtFactory(user=user, direction="lent", counterparty="Akram")
    client = Client()
    response = client.get(reverse("debts:list"), headers={"X-Telegram-InitData": _init(11)})
    body = response.content.decode("utf-8")
    # 'Yopish' button appears for active debts on the visible tab.
    assert "Yopish" in body


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_debts_list_htmx_tab_returns_partial() -> None:
    user = _user(12)
    DebtFactory(user=user, direction="borrowed", counterparty="Karim")
    client = Client()
    response = client.get(
        reverse("debts:list") + "?tab=borrowed",
        headers={"X-Telegram-InitData": _init(12), "HX-Request": "true"},
    )
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    assert "Karim" in body
    # Page heading is absent from the partial.
    assert "Qarzlar</h1>" not in body


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_debts_list_empty_state() -> None:
    _user(13)
    client = Client()
    response = client.get(reverse("debts:list"), headers={"X-Telegram-InitData": _init(13)})
    body = response.content.decode("utf-8")
    assert "Hozircha qarz yo'q" in body


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_debts_list_shows_per_currency_total() -> None:
    user = _user(14)
    DebtFactory(
        user=user,
        direction="lent",
        currency="UZS",
        original_amount=Decimal("100000"),
        remaining_amount=Decimal("100000"),
    )
    DebtFactory(
        user=user,
        direction="lent",
        currency="UZS",
        original_amount=Decimal("50000"),
        remaining_amount=Decimal("50000"),
    )
    client = Client()
    response = client.get(reverse("debts:list"), headers={"X-Telegram-InitData": _init(14)})
    body = response.content.decode("utf-8")
    assert "Jami qoldiq" in body
    # 150 000 UZS total (rendered with thin-space grouping by smart_money filter)
    assert "150" in body


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_debts_list_isolates_users() -> None:
    owner = _user(20)
    intruder = User.objects.create(telegram_id=21, first_name="X", onboarded_at=timezone.now())
    DebtFactory(user=owner, direction="lent", counterparty="Akram")
    DebtFactory(user=intruder, direction="lent", counterparty="OtherPerson")
    client = Client()
    response = client.get(reverse("debts:list"), headers={"X-Telegram-InitData": _init(20)})
    body = response.content.decode("utf-8")
    assert "Akram" in body
    assert "OtherPerson" not in body


# ---------- debt_close_form_view ----------


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_close_form_renders_with_remaining_default() -> None:
    user = _user(30)
    debt = DebtFactory(
        user=user,
        original_amount=Decimal("100000"),
        remaining_amount=Decimal("70000"),
        state=DebtState.PARTIAL.value,
    )
    client = Client()
    response = client.get(
        reverse("debts:close_form", args=[debt.id]),
        headers={"X-Telegram-InitData": _init(30)},
    )
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    assert "Qoldiq" in body
    assert "70000" in body or "70 000" in body


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_close_form_404_for_other_user_debt() -> None:
    owner = _user(31)
    User.objects.create(telegram_id=32, first_name="X", onboarded_at=timezone.now())
    debt = DebtFactory(user=owner)
    client = Client()
    response = client.get(
        reverse("debts:close_form", args=[debt.id]),
        headers={"X-Telegram-InitData": _init(32)},
    )
    assert response.status_code == 404


# ---------- debt_repay_view ----------


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_repay_full_amount_closes_debt() -> None:
    user = _user(40)
    debt = DebtFactory(
        user=user,
        original_amount=Decimal("100000"),
        remaining_amount=Decimal("100000"),
        direction="lent",
    )
    client = Client()
    response = client.post(
        reverse("debts:repay", args=[debt.id]),
        data={"amount": "100000"},
        headers={"X-Telegram-InitData": _init(40)},
    )
    assert response.status_code == 200
    assert "HX-Redirect" in response.headers
    debt.refresh_from_db()
    assert debt.state == DebtState.CLOSED.value
    assert debt.remaining_amount == Decimal("0")
    assert DebtRepayment.objects.filter(debt=debt).count() == 1


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_repay_partial_amount_moves_to_partial_state() -> None:
    user = _user(41)
    debt = DebtFactory(
        user=user,
        original_amount=Decimal("100000"),
        remaining_amount=Decimal("100000"),
    )
    client = Client()
    response = client.post(
        reverse("debts:repay", args=[debt.id]),
        data={"amount": "30000"},
        headers={"X-Telegram-InitData": _init(41)},
    )
    assert response.status_code == 200
    debt.refresh_from_db()
    assert debt.state == DebtState.PARTIAL.value
    assert debt.remaining_amount == Decimal("70000")


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_repay_over_remaining_returns_422() -> None:
    user = _user(42)
    debt = DebtFactory(
        user=user,
        original_amount=Decimal("100000"),
        remaining_amount=Decimal("100000"),
    )
    client = Client()
    response = client.post(
        reverse("debts:repay", args=[debt.id]),
        data={"amount": "200000"},
        headers={"X-Telegram-InitData": _init(42)},
    )
    assert response.status_code == 422
    debt.refresh_from_db()
    assert debt.state == DebtState.OPEN.value
    body = response.content.decode("utf-8")
    assert "Qoldiqdan" in body


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_repay_zero_amount_rejected() -> None:
    user = _user(43)
    debt = DebtFactory(user=user)
    client = Client()
    response = client.post(
        reverse("debts:repay", args=[debt.id]),
        data={"amount": "0"},
        headers={"X-Telegram-InitData": _init(43)},
    )
    assert response.status_code == 422


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_repay_on_closed_debt_returns_422() -> None:
    user = _user(44)
    debt = DebtFactory(
        user=user,
        state=DebtState.CLOSED.value,
        remaining_amount=Decimal("0"),
        original_amount=Decimal("100"),
    )
    client = Client()
    response = client.post(
        reverse("debts:repay", args=[debt.id]),
        data={"amount": "10"},
        headers={"X-Telegram-InitData": _init(44)},
    )
    assert response.status_code == 422


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_repay_404_for_other_user_debt() -> None:
    owner = _user(45)
    User.objects.create(telegram_id=46, first_name="X", onboarded_at=timezone.now())
    debt = DebtFactory(user=owner)
    client = Client()
    response = client.post(
        reverse("debts:repay", args=[debt.id]),
        data={"amount": "10"},
        headers={"X-Telegram-InitData": _init(46)},
    )
    assert response.status_code == 404


# ---------- debt_cancel_view ----------


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_cancel_open_debt_marks_state_cancelled() -> None:
    user = _user(50)
    debt = DebtFactory(user=user, state=DebtState.OPEN.value)
    client = Client()
    response = client.post(
        reverse("debts:cancel", args=[debt.id]),
        data={"reason": "forgiven"},
        headers={"X-Telegram-InitData": _init(50)},
    )
    assert response.status_code == 200
    debt.refresh_from_db()
    assert debt.state == DebtState.CANCELLED.value
    assert debt.cancelled_reason == "forgiven"


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_cancel_closed_debt_returns_410() -> None:
    user = _user(51)
    debt = DebtFactory(
        user=user,
        state=DebtState.CLOSED.value,
        remaining_amount=Decimal("0"),
        original_amount=Decimal("100"),
    )
    client = Client()
    response = client.post(
        reverse("debts:cancel", args=[debt.id]),
        headers={"X-Telegram-InitData": _init(51)},
    )
    assert response.status_code == 410


# ---------- debt_detail_view ----------


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_detail_shows_timeline_with_repayments() -> None:
    user = _user(60)
    debt = DebtFactory(
        user=user,
        counterparty="Karim",
        original_amount=Decimal("100"),
        remaining_amount=Decimal("100"),
    )
    DebtRepayment.objects.create(debt=debt, amount=Decimal("30"), repaid_at=timezone.now())
    client = Client()
    response = client.get(
        reverse("debts:detail", args=[debt.id]),
        headers={"X-Telegram-InitData": _init(60)},
    )
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    assert "Karim" in body
    assert "Berildi" in body  # original line
    assert "Qaytarildi" in body  # repayment line


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_detail_closed_debt_shows_closed_label() -> None:
    user = _user(61)
    debt = DebtFactory(
        user=user,
        state=DebtState.CLOSED.value,
        remaining_amount=Decimal("0"),
        original_amount=Decimal("100"),
    )
    client = Client()
    response = client.get(
        reverse("debts:detail", args=[debt.id]),
        headers={"X-Telegram-InitData": _init(61)},
    )
    body = response.content.decode("utf-8")
    assert "Qarz to'liq yopildi" in body


# ---------- debt_create_view ----------


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_create_debt_via_form_persists() -> None:
    _user(70)
    client = Client()
    response = client.post(
        reverse("debts:create"),
        data={
            "direction": "lent",
            "counterparty": "Akram",
            "amount": "500000",
            "currency": "UZS",
        },
        headers={"X-Telegram-InitData": _init(70)},
    )
    assert response.status_code == 200
    assert response.headers.get("HX-Redirect") == reverse("debts:list")
    debt = Debt.objects.get(counterparty="Akram")
    assert debt.original_amount == Decimal("500000")
    assert debt.remaining_amount == Decimal("500000")
    assert debt.state == DebtState.OPEN.value


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_create_debt_empty_counterparty_returns_422() -> None:
    _user(71)
    client = Client()
    response = client.post(
        reverse("debts:create"),
        data={
            "direction": "lent",
            "counterparty": "",
            "amount": "1000",
            "currency": "UZS",
        },
        headers={"X-Telegram-InitData": _init(71)},
    )
    assert response.status_code == 422


# ---------- BalanceHero integration (Story 4.4 AC) ----------


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_home_balance_hero_does_not_show_debt_strip_after_v0_5() -> None:
    """Sprint v0.5 redesign removed the 3-stat (Naqd / Sof / Qarz) strip from
    Home — debts live on the dedicated /app/debts/ page now. We still surface
    the user-visible Sof balans, just without the debt sub-counts.
    """
    user = _user(80)
    DebtFactory(user=user, direction="lent", remaining_amount=Decimal("100"))
    DebtFactory(user=user, direction="borrowed", remaining_amount=Decimal("40"))
    client = Client()
    response = client.get(
        reverse("core:home_content"),
        headers={"X-Telegram-InitData": _init(80)},
    )
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    assert "Sof balans" in body
    assert "1 ta menga" not in body
    assert "1 ta menda" not in body
