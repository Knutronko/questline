"""ConsoleReporter — rich live progress on the event bus."""

from __future__ import annotations

import sys
from typing import TextIO

from questline.core.events import (
    Event,
    RunFinished,
    RunStarted,
    StepStarted,
    TestFinished,
    TestStarted,
)
from questline.reporters.port import RunSummary

try:
    from rich.console import Console
    from rich.live import Live
    from rich.table import Table
except ImportError:  # pragma: no cover - rich is a core dep; fallback for broken envs
    Console = None  # type: ignore[misc, assignment]
    Live = None  # type: ignore[misc, assignment]
    Table = None  # type: ignore[misc, assignment]


class ConsoleReporter:
    """Live pass/fail counters + current test/step via rich (or plain stderr)."""

    def __init__(self, *, stream: TextIO | None = None) -> None:
        self._stream = stream or sys.stderr
        self._profile = ""
        self._current_test = ""
        self._current_step = ""
        self._passed = 0
        self._failed = 0
        self._skipped = 0
        self._infra = 0
        self._test_verdict = 0
        self._live: AnyLive | None = None
        self._console: AnyConsole | None = None
        if Console is not None:
            self._console = Console(file=self._stream, highlight=False)

    def on_event(self, event: Event) -> None:
        if isinstance(event, RunStarted):
            self._profile = event.profile
            self._start_live()
            self._log(f"run started  profile={event.profile}  run_id={event.run_id}")
        elif isinstance(event, TestStarted):
            self._current_test = event.nodeid or event.test_id
            self._current_step = ""
            self._refresh()
        elif isinstance(event, StepStarted):
            self._current_step = event.name
            self._refresh()
        elif isinstance(event, TestFinished):
            status = (event.status or "").lower()
            if status == "passed":
                self._passed += 1
            elif status == "skipped":
                self._skipped += 1
            else:
                self._failed += 1
                if event.verdict == "infra":
                    self._infra += 1
                elif event.verdict == "test":
                    self._test_verdict += 1
            self._current_step = ""
            mark = {"passed": "PASS", "skipped": "SKIP"}.get(status, "FAIL")
            verdict = f" verdict={event.verdict}" if event.verdict else ""
            self._log(f"{mark}  {event.nodeid or event.test_id}{verdict}")
            self._refresh()
        elif isinstance(event, RunFinished):
            self._stop_live()
            dur = f"{event.duration_s:.2f}s" if event.duration_s is not None else "?"
            self._log(
                f"run finished  status={event.status}  duration={dur}  "
                f"pass={self._passed} fail={self._failed} skip={self._skipped}  "
                f"infra={self._infra} test={self._test_verdict}"
            )

    def finalize(self, run_summary: RunSummary) -> None:
        self._stop_live()
        _ = run_summary  # counters already printed on RunFinished

    def _start_live(self) -> None:
        if Live is None or self._console is None or self._live is not None:
            return
        self._live = Live(
            self._render_table(),
            console=self._console,
            refresh_per_second=8,
            transient=True,
        )
        self._live.start()

    def _stop_live(self) -> None:
        if self._live is not None:
            self._live.stop()
            self._live = None

    def _refresh(self) -> None:
        if self._live is not None:
            self._live.update(self._render_table())

    def _render_table(self) -> object:
        assert Table is not None
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_row("profile", self._profile or "—")
        table.add_row("test", self._current_test or "—")
        table.add_row("step", self._current_step or "—")
        table.add_row(
            "counters",
            f"pass={self._passed}  fail={self._failed}  skip={self._skipped}  "
            f"infra={self._infra}  test={self._test_verdict}",
        )
        return table

    def _log(self, message: str) -> None:
        if self._console is not None:
            self._console.print(f"[bold]questline[/] {message}")
        else:
            print(f"questline {message}", file=self._stream)


# Typing aliases when rich is present
AnyLive = object
AnyConsole = object
