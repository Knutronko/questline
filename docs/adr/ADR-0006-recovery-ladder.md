# ADR-0006: Recovery ladder + infra verdicts (outcomes stay failed)

- **Status:** accepted (phase-06)
- **Context:** Unstable game sessions (USB drops, Wire disconnect, empty hierarchy at
  teardown) historically look like red tests. Misclassifying infra as test failure is
  the #1 trust killer in game automation. Architecture §2.6 requires health checks,
  an ordered recovery ladder, a no-progress watchdog, and store verdicts separate from
  pytest outcomes. Phase brief checklist cited “ADR-0005” for this decision, but
  ADR-0005 is already QuestlineWire — this document is **ADR-0006**.
- **Decision:**
  1. **Normalize then classify.** Transport / signature failures become
     `SessionLostError(kind=…)` via `normalize_exception`; `classify` yields
     `verdict=infra`. Bare `AssertionError` maps to `verdict=test`.
  2. **Pytest outcome stays failed.** Recovery does **not** retry or rewrite the
     failed test result. Subsequent tests may continue on a recovered session.
     Reporters and AI triage read `tests.verdict`, never raw pytest outcome alone.
  3. **Recovery ladder** (config-gated): `reconnect_driver` → `restart_app` →
     `restart_session`, always via `DriverHandle.reset` / provider (never freeze a
     raw `DriverPort`). Each attempt emits `RecoveryAttempted`; success emits
     `DriverRecovered`. Device steps no-op/skip when no device is configured (mock CI).
  4. **Circuit breaker:** N consecutive session losses without an intervening pass
     aborts the run (`CircuitBreakerTripped`, exit `141`), store sealed.
  5. **Watchdog:** daemon no-progress timer; every long operation including recovery
     must `mark_progress()`. Fire → `WatchdogFired`, seal run, exit `140`.
- **Consequences:**
  - Fault-injection pack (`tests/resilience/`) is the CI gate; live USB-pull is optional.
  - Phase-08 HUD ADR numbering shifts (brief’s ADR-0006 claim → next free number).
  - Reporters (phase 07) consume these events without changing the ladder.
- **Alternatives considered:** Auto-retry failed tests after recovery (rejected —
  hides flakes and violates anti-false-green). Soft-skip infra tests (rejected —
  loses signal that a test attempted to run). Freezing driver refs across reset
  (rejected — design rule §3.5).
