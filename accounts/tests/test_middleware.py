"""Sprint 0 — Story 0.4 — TelegramAuthMiddleware integration tests."""

import json

import pytest
from django.http import HttpResponse
from django.test import override_settings

from accounts.middleware import TelegramAuthMiddleware
from accounts.tests.test_services import BOT_TOKEN, _make_init_data


def _request(rf, path: str = "/app/secret/", init_data: str | None = None):
    """Build a request via Django RequestFactory; optionally inject initData header.

    Default path is a hypothetical protected route — `/app/home/` is now in
    PUBLIC_APP_PATHS (it's a shell render), so middleware tests use a non-public
    path to exercise the auth branch.
    """
    headers: dict = {}
    if init_data is not None:
        headers["HTTP_X_TELEGRAM_INITDATA"] = init_data
    return rf.get(path, **headers)


@pytest.fixture
def middleware():
    return TelegramAuthMiddleware(get_response=lambda _req: HttpResponse("ok"))


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
@pytest.mark.django_db
def test_middleware_attaches_user_for_valid_init_data(rf, middleware) -> None:
    init_data = _make_init_data(user_id=7, first_name="Eric", username="eric")
    request = _request(rf, init_data=init_data)
    response = middleware(request)
    assert response.status_code == 200
    assert request.user.telegram_id == 7
    assert request.user.is_authenticated is True


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
def test_middleware_returns_401_for_bad_hmac(rf, middleware) -> None:
    init_data = _make_init_data(bad_hash=True)
    request = _request(rf, init_data=init_data)
    response = middleware(request)
    assert response.status_code == 401
    assert json.loads(response.content) == {"error": "invalid_init_data"}


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
def test_middleware_returns_401_for_missing_header(rf, middleware) -> None:
    request = _request(rf, init_data=None)
    response = middleware(request)
    assert response.status_code == 401


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
def test_middleware_skips_non_app_paths(rf, middleware) -> None:
    """Routes outside /app/* bypass auth entirely (e.g., /admin/, /bot/webhook/)."""
    request = _request(rf, path="/admin/login/", init_data=None)
    response = middleware(request)
    assert response.status_code == 200  # passes through to get_response


@override_settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN)
def test_middleware_lets_public_app_paths_through_without_init_data(rf, middleware) -> None:
    """/app/home/ is a public shell — anonymous GET must NOT be blocked."""
    request = _request(rf, path="/app/home/", init_data=None)
    response = middleware(request)
    assert response.status_code == 200  # passes to get_response (no auth check)
