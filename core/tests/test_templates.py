"""Sprint 0 — Story 0.5 — base layout + nav + toast + tokens verification."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def test_base_template_has_mobile_viewport_lock() -> None:
    base = (BASE_DIR / "core" / "templates" / "base.html").read_text(encoding="utf-8")
    assert 'name="viewport"' in base
    assert "width=device-width" in base
    assert "maximum-scale=1" in base
    assert "user-scalable=no" in base


def test_base_template_includes_required_scripts() -> None:
    base = (BASE_DIR / "core" / "templates" / "base.html").read_text(encoding="utf-8")
    assert "telegram-web-app.js" in base
    assert "htmx.min.js" in base
    assert "alpine.min.js" in base


def test_base_template_loads_tokens_and_build_css() -> None:
    base = (BASE_DIR / "core" / "templates" / "base.html").read_text(encoding="utf-8")
    assert "tokens.css" in base
    assert "build.css" in base


def test_base_template_lang_uzbek() -> None:
    base = (BASE_DIR / "core" / "templates" / "base.html").read_text(encoding="utf-8")
    assert '<html lang="uz">' in base


def test_nav_has_five_tabs_with_aria_labels() -> None:
    nav = (BASE_DIR / "core" / "templates" / "core" / "_nav.html").read_text(encoding="utf-8")
    # Five tabs (Sprint v0.5 order: Uy · Tarix · [+ Qo'shish] · Qarzlar · Hisobot).
    # Centre + uses the longer aria for screen-reader clarity.
    for label in ["Uy", "Tarix", "Yangi tranzaksiya qo'shish", "Qarzlar", "Hisobot"]:
        assert f'aria-label="{label}"' in nav, f"Missing nav tab: {label}"
    assert "safe-area-inset-bottom" in nav


def test_toast_uses_alpine_and_has_aria_live() -> None:
    toast = (BASE_DIR / "core" / "templates" / "core" / "_toast.html").read_text(encoding="utf-8")
    assert "x-show" in toast
    assert 'role="alert"' in toast
    assert 'aria-live="polite"' in toast


def test_tokens_css_defines_color_palette() -> None:
    tokens = (BASE_DIR / "static" / "css" / "tokens.css").read_text(encoding="utf-8")
    # UX spec required tokens
    for var in [
        "--color-primary",
        "--color-income",
        "--color-expense",
        "--color-debt",
        "--space-4",
        "--container-max",
        "--radius-card",
        "--tap-target-min",
    ]:
        assert var in tokens, f"Missing token: {var}"


def test_vendored_js_files_present() -> None:
    htmx = BASE_DIR / "static" / "js" / "htmx.min.js"
    alpine = BASE_DIR / "static" / "js" / "alpine.min.js"
    assert htmx.exists() and htmx.stat().st_size > 10_000, "htmx.min.js missing or too small"
    assert alpine.exists() and alpine.stat().st_size > 10_000, "alpine.min.js missing or too small"
