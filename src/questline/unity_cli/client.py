"""Subprocess wrapper for the experimental ``unity`` CLI.

Feature-detect: a missing binary is ``available=False``, not an exception.
Stdout is parsed for JSON. Tokens are never logged.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("questline.unity_cli")

Runner = Callable[[list[str], float, dict[str, str]], "UnityRun"]
Which = Callable[[str], str | None]


@dataclass
class UnityRun:
    """One CLI invocation. ``stdout`` is for parsing only — do not export it."""

    returncode: int | None
    stdout: str
    stderr: str
    timed_out: bool = False
    missing: bool = False

    def payload(self) -> Any | None:
        return parse_cli_stdout(self.stdout)


def parse_cli_stdout(stdout: str) -> Any | None:
    """Parse a JSON document from CLI stdout. Plain text returns None."""
    text = (stdout or "").strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    starts = [i for i in (text.find("{"), text.find("[")) if i >= 0]
    if not starts:
        return None
    try:
        return json.loads(text[min(starts) :])
    except json.JSONDecodeError:
        return None


def _default_which(name: str) -> str | None:
    return shutil.which(name)


class UnityCli:
    """Call ``unity`` with ``--json``. Inject ``runner`` / ``which`` in tests."""

    def __init__(
        self,
        *,
        binary: str = "unity",
        runner: Runner | None = None,
        which: Which | None = None,
    ) -> None:
        self.binary = binary
        self._runner = runner
        self._which = which if which is not None else _default_which

    def available(self) -> bool:
        return self._which(self.binary) is not None

    def run(
        self,
        args: list[str],
        *,
        timeout_s: float,
        extra_env: dict[str, str] | None = None,
    ) -> UnityRun:
        env = dict(extra_env or {})
        if not self.available():
            return UnityRun(returncode=None, stdout="", stderr="", missing=True)
        if self._runner is not None:
            return self._runner(list(args), timeout_s, env)
        return _subprocess_run(self.binary, args, timeout_s, env)


def _subprocess_run(
    binary: str,
    args: list[str],
    timeout_s: float,
    extra_env: dict[str, str],
) -> UnityRun:
    proc_env = os.environ.copy()
    proc_env.update(extra_env)
    argv = [binary, *args]
    try:
        completed = subprocess.run(
            argv,
            capture_output=True,
            timeout=timeout_s,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=proc_env,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        logger.warning("unity CLI timed out after %.1fs", timeout_s)
        return UnityRun(
            returncode=None,
            stdout=_text(exc.stdout),
            stderr=_text(exc.stderr),
            timed_out=True,
        )
    except OSError as exc:
        logger.warning("unity CLI failed to start (%s)", type(exc).__name__)
        return UnityRun(returncode=None, stdout="", stderr="", missing=True)
    return UnityRun(
        returncode=completed.returncode,
        stdout=completed.stdout or "",
        stderr=completed.stderr or "",
    )


def _text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    return value
