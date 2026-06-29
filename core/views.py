"""Home shell + auth-tolerant content endpoint (Story 1.5 + post-deploy fix).

Two-phase render: the shell at /app/home/ is public; /app/home/content/ is also
public but tries to authenticate via the X-Telegram-InitData header. Missing or
invalid initData falls back to an anonymous welcome card so the WebApp renders
under any Telegram launch context (Menu Button on Desktop can ship empty
initData; mobile + inline buttons are reliable).
"""

import logging

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from accounts.exceptions import InvalidInitDataError
from accounts.middleware import SESSION_KEY
from accounts.models import User
from accounts.services import get_or_create_user_from_init_data, validate_init_data
from currencies.constants import CURRENCY_CHOICES, CURRENCY_CODES
from currencies.selectors import aggregated_month_summary, current_rates_stale_days
from currencies.services import update_rates_if_stale
from currencies.views import SESSION_DISPLAY_CURRENCY
from debts.selectors import debt_status_summary
from quotes.models import QuoteDismissal
from quotes.selectors import quote_of_the_day
from quotes.services import SESSION_HIDE_TODAY, dismiss_forever, reenable
from transactions.selectors import daily_flow_series, month_over_month_delta, month_summary

logger = logging.getLogger(__name__)
INIT_DATA_HEADER = "X-Telegram-InitData"


@require_GET
def home(request):
    """Render the public shell. JS in base.html attaches initData on the htmx call."""
    return render(request, "core/home.html")


@require_GET
def home_content(request):
    """Render BalanceHero if authed; otherwise an anonymous welcome fallback."""
    init_data = request.headers.get(INIT_DATA_HEADER, "")
    user = _try_authenticate(init_data)
    if user is None:
        cached_id = request.session.get(SESSION_KEY)
        if cached_id is not None:
            user = User.objects.filter(telegram_id=cached_id).first()

    if user is None:
        return render(request, "core/_home_anonymous.html")

    request.session[SESSION_KEY] = user.telegram_id

    if user.onboarded_at is None:
        response = HttpResponse(status=200)
        response.headers["HX-Redirect"] = reverse("accounts:onboarding")
        return response

    # Display currency is purely for the balance hero's aggregated total.
    # Transactions, top-categories, history, reports all stay in source
    # currency (user.default_currency drives the per-source summary below).
    display_currency = _resolve_display_currency(request, user)
    source_currency = user.default_currency or "UZS"
    summary = month_summary(user, currency=source_currency)
    debts = debt_status_summary(user)

    # On-demand refresh of CBU.uz rates if today's row is missing.
    if current_rates_stale_days() != 0:
        update_rates_if_stale()

    # Pre-compute the aggregated balance in every currency so the switcher
    # can flip the displayed amount client-side without a page reload.
    balance_by_currency = {}
    aggregated = None
    fully_supported = True
    rate_date = None
    for ccy in CURRENCY_CODES:
        agg = aggregated_month_summary(user, ccy)
        balance_by_currency[ccy] = agg.cash_balance
        if ccy == display_currency:
            aggregated = agg
        if not agg.is_fully_supported:
            fully_supported = False
        if agg.rate_date is not None and (rate_date is None or agg.rate_date < rate_date):
            rate_date = agg.rate_date

    rates_stale_days = current_rates_stale_days()
    rates_stale_date = rate_date
    forced_raw_no_rates = not fully_supported

    # Per-source-currency balance breakdown — shown beneath the hero when the
    # user actually holds more than one source currency, so the strip never
    # repeats what's already in the headline.
    per_currency_balances = []
    for ccy in CURRENCY_CODES:
        per = month_summary(user, currency=ccy)
        if per.transaction_count:
            per_currency_balances.append(
                {
                    "currency": ccy,
                    "cash_balance": per.cash_balance,
                    "is_display": ccy == display_currency,
                },
            )

    quote = None if request.session.get(SESSION_HIDE_TODAY) else quote_of_the_day(user)

    inflow_series, outflow_series = daily_flow_series(user, source_currency)
    mom_delta = month_over_month_delta(user, source_currency)

    return render(
        request,
        "core/_balance_hero.html",
        {
            "summary": summary,
            "user": user,
            "debts": debts,
            "aggregated": aggregated,
            "display_currency": display_currency,
            "source_currency": source_currency,
            "currency_choices": CURRENCY_CHOICES,
            "balance_by_currency": balance_by_currency,
            "per_currency_balances": per_currency_balances,
            "rates_stale_days": rates_stale_days,
            "rates_stale_date": rates_stale_date,
            "forced_raw_no_rates": forced_raw_no_rates,
            "quote": quote,
            "inflow_series": inflow_series,
            "outflow_series": outflow_series,
            "mom_delta": mom_delta,
        },
    )


def _resolve_display_currency(request, user: User) -> str:
    """Pick the balance-display currency from session > user default > UZS."""
    currency = request.session.get(SESSION_DISPLAY_CURRENCY) or user.default_currency
    if currency not in CURRENCY_CODES:
        currency = "UZS"
    return currency


def _try_authenticate(init_data: str):
    """Best-effort: returns a User on success, None when initData is missing/invalid.

    Logs key signal (length + reason) without leaking the raw header so we can
    diagnose from server logs without exposing user data.
    """
    if not init_data:
        logger.info("home_content auth: init_data header empty")
        return None
    logger.info("home_content auth: received init_data length=%d", len(init_data))
    try:
        user_dict = validate_init_data(init_data, settings.TELEGRAM_BOT_TOKEN)
    except InvalidInitDataError as e:
        logger.info("home_content auth: validation failed reason=%s", e)
        return None
    logger.info("home_content auth: ok user_id=%s", user_dict.get("id"))
    return get_or_create_user_from_init_data(user_dict)


@require_GET
def settings_hub(request):
    """Sprint v0.5 Phase 4 — Settings hub at /app/settings/.

    Profil + Pul + Tartib + Maxfiylik. Sub-pages already exist
    (categories, recurring) — this just gives them a stable landing.
    """
    user = request.user
    return render(
        request,
        "core/settings.html",
        {
            "user": user,
            "currency_choices": CURRENCY_CHOICES,
            "quote_enabled": not QuoteDismissal.objects.filter(user=user).exists(),
        },
    )


@require_POST
def toggle_quote_feature(request):
    """Flip the per-user quote opt-out from the Settings hub."""
    enable = request.POST.get("enabled") == "1"
    if enable:
        reenable(request.user)
        request.session.pop("iw_quote_hidden_today", None)
    else:
        dismiss_forever(request.user)
        request.session["iw_quote_hidden_today"] = True
    response = HttpResponse(status=200)
    response.headers["HX-Redirect"] = reverse("core:settings_hub")
    return response


@require_GET
def healthz(_request):
    """Anonymous healthcheck endpoint (Caddy + GitHub Actions deploy smoke test)."""
    return HttpResponse("ok", content_type="text/plain")
