"""Telegram WebApp initData validation + user provisioning.

Spec: https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
"""

import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

from django.db import transaction as db_transaction

from .exceptions import InvalidInitDataError
from .models import User

MAX_AUTH_AGE_SECONDS = 24 * 60 * 60  # 24 hours per project-context


def validate_init_data(init_data: str, bot_token: str) -> dict:
    """Validate Telegram WebApp initData HMAC + freshness; return parsed user dict.

    Raises InvalidInitDataError on any failure (bad HMAC, expired, malformed).
    """
    if not init_data:
        raise InvalidInitDataError("init_data is empty")
    if not bot_token:
        raise InvalidInitDataError("bot_token not configured")

    parsed = dict(parse_qsl(init_data, strict_parsing=True))
    received_hash = parsed.pop("hash", None)
    if not received_hash:
        raise InvalidInitDataError("hash field missing")

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    expected_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected_hash, received_hash):
        raise InvalidInitDataError("HMAC mismatch")

    auth_date_raw = parsed.get("auth_date")
    if not auth_date_raw:
        raise InvalidInitDataError("auth_date missing")
    try:
        auth_date = int(auth_date_raw)
    except ValueError as e:
        raise InvalidInitDataError("auth_date not an integer") from e
    if time.time() - auth_date > MAX_AUTH_AGE_SECONDS:
        raise InvalidInitDataError("auth_date expired (>24h old)")

    user_json = parsed.get("user")
    if not user_json:
        raise InvalidInitDataError("user field missing")
    try:
        user_data = json.loads(user_json)
    except json.JSONDecodeError as e:
        raise InvalidInitDataError("user field is not valid JSON") from e

    if "id" not in user_data:
        raise InvalidInitDataError("user.id missing")

    return user_data


@db_transaction.atomic
def mark_onboarded(user: User) -> None:
    """Stamp the user as having seen the first-run onboarding (idempotent).

    Story 1.0 AC: re-calling does NOT overwrite the original timestamp.
    """
    if user.onboarded_at is not None:
        return
    from django.utils import timezone

    user.onboarded_at = timezone.now()
    user.save(update_fields=["onboarded_at"])


@db_transaction.atomic
def get_or_create_user_from_init_data(user_dict: dict) -> User:
    """Upsert a User from the validated Telegram user payload."""
    telegram_id = int(user_dict["id"])
    user, created = User.objects.get_or_create(
        telegram_id=telegram_id,
        defaults={
            "first_name": user_dict.get("first_name", ""),
            "last_name": user_dict.get("last_name", ""),
            "username": user_dict.get("username", "") or "",
            "language_code": user_dict.get("language_code", "uz")[:8],
        },
    )
    if not created:
        # Refresh mutable Telegram-side fields
        changed = False
        for field, value in {
            "first_name": user_dict.get("first_name", user.first_name),
            "last_name": user_dict.get("last_name", user.last_name),
            "username": user_dict.get("username", "") or "",
        }.items():
            if getattr(user, field) != value:
                setattr(user, field, value)
                changed = True
        if changed:
            user.save(update_fields=["first_name", "last_name", "username", "last_seen"])
    return user
