"""Sprint 0 — Story 0.2 — settings.py env-driven config sanity checks."""

from pathlib import Path

from django.conf import settings


def test_secret_key_loaded_from_env() -> None:
    """SECRET_KEY is set (any non-empty value from .env)."""
    assert isinstance(settings.SECRET_KEY, str)
    assert len(settings.SECRET_KEY) >= 20


def test_debug_is_bool_from_env() -> None:
    """DEBUG is a bool, cast by python-decouple."""
    assert isinstance(settings.DEBUG, bool)


def test_allowed_hosts_is_list() -> None:
    """ALLOWED_HOSTS is parsed via Csv() cast."""
    assert isinstance(settings.ALLOWED_HOSTS, list)
    assert len(settings.ALLOWED_HOSTS) >= 1


def test_locale_uzbek() -> None:
    """LANGUAGE_CODE='uz', TIME_ZONE='Asia/Tashkent'."""
    assert settings.LANGUAGE_CODE == "uz"
    assert settings.TIME_ZONE == "Asia/Tashkent"


def test_csp_middleware_registered() -> None:
    """django-csp middleware is in MIDDLEWARE."""
    assert "csp.middleware.CSPMiddleware" in settings.MIDDLEWARE


def test_csp_directives_strict() -> None:
    """CSP defaults to self only, allows Telegram domains."""
    directives = settings.CONTENT_SECURITY_POLICY["DIRECTIVES"]
    assert directives["default-src"] == ["'self'"]
    assert "https://telegram.org" in directives["script-src"]


def test_logging_configured() -> None:
    """LOGGING dict present with stdout handler."""
    assert "stdout" in settings.LOGGING["handlers"]
    assert settings.LOGGING["root"]["level"] in {"DEBUG", "INFO", "WARNING", "ERROR"}


def test_all_local_apps_installed() -> None:
    """All 10 domain apps registered (moved from test_smoke to reduce duplication)."""
    expected = {
        "core",
        "accounts",
        "transactions",
        "categories",
        "debts",
        "voice",
        "currencies",
        "recurring",
        "reports",
        "notifications",
    }
    installed = set(settings.INSTALLED_APPS)
    missing = expected - installed
    assert not missing, f"Missing apps: {missing}"


def test_secret_key_has_no_default_in_source() -> None:
    """settings.py calls config('SECRET_KEY') WITHOUT default — fail-fast on missing env."""
    settings_py = Path(__file__).resolve().parent.parent.parent / "iwallet" / "settings.py"
    source = settings_py.read_text(encoding="utf-8")
    assert 'config("SECRET_KEY")' in source, "SECRET_KEY must be loaded via decouple config()"
    assert 'config("SECRET_KEY",' not in source, (
        "SECRET_KEY must have NO default — required env var (per Story 0.2 AC3)"
    )
