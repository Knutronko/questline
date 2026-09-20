"""Code-owned pytest classification. Model claims never decide executed/green."""

from __future__ import annotations

import re
from typing import Any

_COLLECT_FAIL = re.compile(
    r"ERROR collecting|ImportError|SyntaxError|collected 0 items|no tests ran",
    re.IGNORECASE,
)
_PASSED = re.compile(r"\b\d+ passed\b")
_FAILED = re.compile(r"\b\d+ failed\b")


def classify_pytest(result: dict[str, Any]) -> tuple[bool, bool]:
    """Return ``(executed, green)`` from a pytest subprocess result.

    Collection/import failures are *not* executed. A model cannot override this.
    """
    rc = int(result.get("returncode") if result.get("returncode") is not None else 2)
    out = f"{result.get('stdout') or ''}\n{result.get('stderr') or ''}"
    if _COLLECT_FAIL.search(out):
        return False, False
    if _PASSED.search(out) or _FAILED.search(out):
        return True, rc == 0
    if rc == 0:
        return True, True
    if rc == 1:
        return True, False
    return False, False


def expected_from_spec(spec: str) -> str:
    """Parse ``expect: green|red`` from a spec. Default green."""
    match = re.search(
        r"(?im)^\s*expect(?:ed)?\s*:\s*(green|red|pass|fail|passed|failed)\s*$",
        spec or "",
    )
    if match is None:
        return "green"
    token = match.group(1).lower()
    if token in {"green", "pass", "passed"}:
        return "green"
    return "red"


def spec_matches(expected: str, *, executed: bool, green: bool) -> bool:
    if not executed:
        return False
    if expected == "green":
        return green
    return not green
