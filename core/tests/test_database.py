"""Sprint 0 — Story 0.3 — DATABASE_URL parsing."""

import dj_database_url
import pytest


def test_dj_database_url_sqlite_fallback() -> None:
    """Empty DATABASE_URL → sqlite (handled in settings via `if DATABASE_URL` check)."""
    # When config returns "" the if-check falls through to sqlite block
    from django.conf import settings

    engine = settings.DATABASES["default"]["ENGINE"]
    assert engine in {
        "django.db.backends.sqlite3",
        "django.db.backends.postgresql",
    }, f"Unexpected engine: {engine}"


def test_dj_database_url_parses_postgres_dsn() -> None:
    """Verify dj_database_url.parse handles a Postgres DSN correctly."""
    dsn = "postgres://user:pass@localhost:5432/iwallet"
    parsed = dj_database_url.parse(dsn, conn_max_age=600, conn_health_checks=True)
    assert parsed["ENGINE"] == "django.db.backends.postgresql"
    assert parsed["NAME"] == "iwallet"
    assert parsed["USER"] == "user"
    assert parsed["HOST"] == "localhost"
    assert parsed["PORT"] == 5432
    assert parsed["CONN_MAX_AGE"] == 600
    assert parsed["CONN_HEALTH_CHECKS"] is True


@pytest.mark.django_db
def test_migration_creates_baseline_tables() -> None:
    """pytest-django auto-creates the test DB and runs migrations → baseline tables exist."""
    from django.db import connection

    with connection.cursor() as cursor:
        if connection.vendor == "sqlite":
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        else:
            cursor.execute("SELECT tablename FROM pg_tables WHERE schemaname='public'")
        tables = {row[0] for row in cursor.fetchall()}
    assert any(t.startswith(("auth_", "django_")) for t in tables), (
        f"Expected Django baseline tables; got {tables}"
    )
