# Phase 03 — Authoring layer (pytest plugin, pages, steps, assertions, quarantine)

> Session preamble: see `phase-00-bootstrap.md`. Read `docs/01-ARCHITECTURE.md §4`.

## Context
Phases 00–02 merged: kernel + DriverPort + MockDriver + conformance suite exist.

## Objective
The layer test authors touch daily. A demo suite in `examples/demo-tests/` runs end-to-end
against MockDriver, emitting real events into the store.

## In scope
1. **pytest plugin** (`authoring/plugin.py`): session fixtures wiring
   profile → driver (via DriverHandle) → store subscriber; per-test Run/Test events;
   `--questline-profile` CLI option; markers namespace (`quest.smoke`, `quest.regression`,
   custom via config); quarantined tests excluded by default,
   `--include-quarantined` runs them.
2. **Pages** (`authoring/pages.py`): base `Page` with locator-registry binding and
   DriverHandle access; NO waits hardcoded — `WaitPolicy` injected (profile default,
   page override, call override).
3. **Step pipeline** (`authoring/steps.py`): `Scenario` builder per architecture §4 —
   declarative steps (`Tap`, `WaitFor`, `Save`, `AssertThat`, `HandleOptional`) + `.call()`
   inline callables as first-class steps; nothing executes before `.run(ctx)`; every step
   emits `StepStarted/StepFinished` with timestamps and outcome; `HandleOptional` implements
   the probe-then-move-on pattern for unpredictable popups (uses `probe`, never `deadline`).
4. **Context** (`authoring/context.py`): typed key-value store for data flowing between
   steps (replaces implicit shared state); readable in assertions and reports.
5. **Assertions** (`authoring/expect.py`): fluent `expect(x).equals/differs/is_true/
   contains/…`; constructing an assertion with no comparator = `AuthoringError` at build
   time (hard fail, unit-tested).
6. **Quarantine ledger** (`authoring/quarantine.py` + `quarantine.yaml` format):
   entry {test_id, reason, date, owner, exit_criteria, issue}; CLI
   `questline quarantine add|remove|audit`; `audit` exits non-zero on limbo
   (marker↔ledger mismatch) — wired into CI.
7. **Demo suite** (`examples/demo-tests/`): a small fake "game" scripted in MockDriver +
   ~8 tests exercising pages, steps, optional popups, data flow, one quarantined test.

## Out of scope
Real drivers, reporters, resilience policies (Phase 06), HUD.

## Acceptance criteria
- [ ] `pytest examples/demo-tests --questline-profile mock` green in CI; store contains
      the full timeline (runs→tests→steps) afterwards (asserted by a meta-test).
- [ ] Death-point data: a deliberately failing demo test yields last-started step +
      driver health in the store.
- [ ] Comparator-less assertion fails at build time with a clear message.
- [ ] `questline quarantine audit` catches a seeded limbo state in a test fixture.
- [ ] Coverage ≥ 85% on `authoring/`.

## PR checklist
Title `phase-03: authoring layer`. Update `docs/` with an authoring guide (`docs/writing-tests.md`).
