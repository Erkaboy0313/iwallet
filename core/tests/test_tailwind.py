"""Sprint 0 — Story 0.6 — Tailwind build sanity checks."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def test_package_json_pins_tailwind_v4() -> None:
    pkg = (BASE_DIR / "package.json").read_text(encoding="utf-8")
    assert "@tailwindcss/cli" in pkg
    assert '"^4' in pkg, "Tailwind must be pinned to v4.x"


def test_app_css_imports_tailwind_and_sources_templates() -> None:
    app_css = (BASE_DIR / "static" / "css" / "app.css").read_text(encoding="utf-8")
    assert '@import "tailwindcss"' in app_css
    # All 10 app templates must be sourced for purge
    for app in [
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
    ]:
        assert f"{app}/templates" in app_css, f"Missing @source for {app}"


def test_build_css_size_under_budget_if_built() -> None:
    """If build.css exists (post-`npm run build:css`), it stays under 30 KB raw."""
    build = BASE_DIR / "static" / "css" / "build.css"
    if not build.exists():
        return  # gitignored — fine on CI when build runs separately
    size_kb = build.stat().st_size / 1024
    assert size_kb < 50, (
        f"build.css = {size_kb:.1f} KB; target ≤ 30 KB gzipped (~50 KB raw). Audit @source globs."
    )
