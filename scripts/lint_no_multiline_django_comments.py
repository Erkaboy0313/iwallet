#!/usr/bin/env python3
"""Fail when a Django template contains a multi-line {# ... #} comment.

Django's {# ... #} is single-line only — multi-line variants leak as literal
body text when rendered. We've hit this three times in production; this hook
makes it impossible to land again.

Usage (pre-commit / CI):
    python scripts/lint_no_multiline_django_comments.py
Exit code 1 if any offender found; 0 otherwise.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {".venv", "node_modules", ".claude", "staticfiles", "__pycache__"}
MULTILINE_DJANGO_COMMENT = re.compile(r"\{#(?:[^#]|#(?!\}))*?\n(?:[^#]|#(?!\}))*?#\}")


def main() -> int:
    offenders: list[tuple[str, int]] = []
    for path in ROOT.rglob("*.html"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for match in MULTILINE_DJANGO_COMMENT.finditer(text):
            line = text[: match.start()].count("\n") + 1
            offenders.append((str(path.relative_to(ROOT)), line))
    if offenders:
        print("Multi-line {# ... #} found — convert to {% comment %} ... {% endcomment %}:")
        for path, line in offenders:
            print(f"  {path}:{line}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
