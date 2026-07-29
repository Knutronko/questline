# Phase 06 — Resilience: health, recovery, watchdog, verdict classification

> Session preamble: see `phase-00-bootstrap.md`. Read `docs/01-ARCHITECTURE.md §2.6`.
> This phase encodes the hardest-won lessons of the whole design. Read the design rules
> in `docs/00-MASTER-PLAN.md §3` twice before coding.

## Context
Phases 00–05 merged. Real runs work but an unstable session kills a suite ungracefully.

## Objective
Runs degrade gracefully: session losses are detected, classified as infra, recovered when
possible, and never produce false test verdicts or silent hangs.

## In scope
1. **HealthMonitor** (`core/health.py`): cheap checks (driver `is_alive`, hierarchy
   non-empty, device online) invokable between tests and inside recovery.
2. **Session-loss detection**: centralized `classify(exc)` extension — signature list for
   transport errors (connection closed, no app connected, empty hierarchy at teardown…);
   each maps to `SessionLostError(kind)` with verdict `infra`. Pytest outcome for the
   affected test stays *failed* but verdict metadata says `infra` — reporters and triage
   read the verdict, never the raw outcome.
3. **RecoveryPolicy** (`core/recovery.py`): ordered strategies `reconnect_driver` (cheap,
   preserves app state) → `restart_app` → `restart_session` (device relaunch); config per
   profile; every attempt emits events with duration; consecutive-loss circuit breaker
   (N losses without an intervening pass → abort run with distinct exit code, reporters
   still fire).
4. **Watchdog**: no-progress timer (config; sane default) running as daemon thread;
   **progress marks in every long operation including recovery and between-test work**
   (unit test asserts marks fire during recovery — the classic gap); on trigger: persist,
   emit `WatchdogFired`, exit distinct code.
5. **Fault-injection test pack** (`tests/resilience/`): using MockDriver scripted faults —
   mid-step disconnect (recovered), repeated disconnect (circuit breaker), hang (watchdog),
   recovery that itself hangs (watchdog still fires).
6. Docs: `docs/resilience.md` — failure modes table: signature → classification → recovery
   → what the report shows.

## Out of scope
AI triage (Phase 12), reporters (Phase 07) — but events emitted here are their input.

## Acceptance criteria
- [ ] All fault-injection tests green in CI (no real device needed).
- [ ] Infra-classified failure shows `verdict=infra` in store; a plain assertion failure
      shows `verdict=test` — asserted by meta-tests.
- [ ] Watchdog fires during a scripted hung recovery (the gap case) and the run store
      contains everything up to that point.
- [ ] Circuit breaker aborts after N consecutive losses; exit code distinct; store sealed.
- [ ] Maintainer-checked (optional): pull the USB cable mid-run on a real device →
      clean infra classification + recovery attempt.

## PR checklist
Title `phase-06: resilience`. ADR-0005 (recovery ladder + why outcomes stay failed).
