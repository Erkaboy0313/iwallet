"""Sprint 0 — Story 0.4 — initData validation + user provisioning."""

import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import pytest

from accounts.exceptions import InvalidInitDataError
from accounts.models import User
from accounts.services import (
    MAX_AUTH_AGE_SECONDS,
    get_or_create_user_from_init_data,
    validate_init_data,
)

BOT_TOKEN = "123456:test-bot-token"


def _make_init_data(
    *,
    bot_token: str = BOT_TOKEN,
    user_id: int = 12345,
    first_name: str = "Test",
    username: str | None = "testuser",
    auth_date: int | None = None,
    bad_hash: bool = False,
) -> str:
    """Generate a signed initData string for tests."""
    if auth_date is None:
        auth_date = int(time.time())

    user_payload: dict = {"id": user_id, "first_name": first_name}
    if username:
        user_payload["username"] = username

    data: dict[str, str] = {
        "auth_date": str(auth_date),
        "query_id": "abc123",
        "user": json.dumps(user_payload, separators=(",", ":")),
    }
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    hash_value = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if bad_hash:
        hash_value = "0" * 64

    data["hash"] = hash_value
    return urlencode(data)


# ---------- validate_init_data ----------


def test_validate_valid_init_data_returns_user_dict() -> None:
    init_data = _make_init_data(user_id=42, first_name="Eric", username="eric")
    result = validate_init_data(init_data, BOT_TOKEN)
    assert result["id"] == 42
    assert result["first_name"] == "Eric"
    assert result["username"] == "eric"


def test_validate_rejects_bad_hmac() -> None:
    init_data = _make_init_data(bad_hash=True)
    with pytest.raises(InvalidInitDataError, match="HMAC mismatch"):
        validate_init_data(init_data, BOT_TOKEN)


def test_validate_rejects_expired_auth_date() -> None:
    expired = int(time.time()) - MAX_AUTH_AGE_SECONDS - 60
    init_data = _make_init_data(auth_date=expired)
    with pytest.raises(InvalidInitDataError, match="expired"):
        validate_init_data(init_data, BOT_TOKEN)


def test_validate_rejects_empty_init_data() -> None:
    with pytest.raises(InvalidInitDataError, match="empty"):
        validate_init_data("", BOT_TOKEN)


def test_validate_rejects_missing_hash() -> None:
    with pytest.raises(InvalidInitDataError, match="hash field missing"):
        validate_init_data("auth_date=1234567890", BOT_TOKEN)


def test_validate_rejects_when_bot_token_missing() -> None:
    init_data = _make_init_data()
    with pytest.raises(InvalidInitDataError, match="bot_token not configured"):
        validate_init_data(init_data, "")


def test_validate_rejects_wrong_bot_token() -> None:
    """initData signed with one token must not validate against another."""
    init_data = _make_init_data(bot_token="other-token")
    with pytest.raises(InvalidInitDataError, match="HMAC mismatch"):
        validate_init_data(init_data, BOT_TOKEN)


# ---------- get_or_create_user_from_init_data ----------


@pytest.mark.django_db
def test_get_or_create_creates_new_user() -> None:
    init_data = _make_init_data(user_id=999, first_name="New", username="newuser")
    user_dict = validate_init_data(init_data, BOT_TOKEN)
    user = get_or_create_user_from_init_data(user_dict)
    assert user.telegram_id == 999
    assert user.first_name == "New"
    assert user.username == "newuser"
    assert User.objects.count() == 1


@pytest.mark.django_db
def test_get_or_create_updates_existing_user_username_change() -> None:
    User.objects.create(telegram_id=500, first_name="Old", username="oldname")
    new_data = {"id": 500, "first_name": "Old", "username": "newname"}
    user = get_or_create_user_from_init_data(new_data)
    assert user.username == "newname"
    assert User.objects.count() == 1
