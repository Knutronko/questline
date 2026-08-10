# Phase 08 — HUD I: run viewer + live view

> Session preamble: see `phase-00-bootstrap.md`. Read `docs/01-ARCHITECTURE.md §6`.

## Context
Phases 00–07 merged. The run store holds full timelines, artifacts, verdicts. No UI.

## Objective
`questline hud` opens a local web dashboard: run history, run/test detail, artifacts,
trends, and a live view of an in-progress run.

## In scope
1. **Backend** (`hud/server.py`, extra `questline[hud]`): FastAPI over the run store;
   REST endpoints (runs list w/ filters, run detail, test detail incl. step timeline +
   death-point, artifacts, trends aggregations); WebSocket `/live` bridging the event bus
   for the run in progress; localhost bind by default (`--host` opt-in).
2. **Frontend** (`hud/frontend/` source → built assets embedded in the wheel; no Node
   required at runtime): SPA with pages —
   - **Runs**: table (profile, driver, device, totals, duration, verdict split), filters.
   - **Run detail**: tests grid (status, verdict, duration), infra-vs-test split banner.
   - **Test detail**: step timeline with real timestamps, artifacts (screenshot viewer,
     logcat), error + death-point panel, history sparkline of this test.
   - **Trends**: pass rate over time, duration trends, flakiness board (most-flaky tests).
   - **Live**: current run streaming (tests/steps appearing in real time).
3. **Design language**: dark, game-HUD aesthetic (it's called HUD — lean into it), but
   information-density first. Keep the stack boring (no heavy state framework).
4. CLI: `questline hud [--port] [--open]`; graceful "empty store" state.
5. Docs: `docs/hud.md` with screenshots.

## Out of scope
Control center (launch/stop runs, quarantine mgmt, config editor — Phase 10), perf graphs
(Phase 09 data → rendered in Phase 10), auth/multi-user.

## Acceptance criteria
- [x] CI: backend endpoint tests against a fixture store; frontend builds; a Playwright (or
      equivalent) smoke: open HUD → see seeded runs → drill to a test → see steps.
- [x] Live view test: scripted mock run streams into the browser (backend WS integration
      test acceptable in CI; visual check by maintainer).
- [x] Wheel embeds built assets — `pip install questline[hud]` on a clean machine serves
      the UI with no Node.
- [ ] Maintainer-checked: HUD over their real Android run history is usable and fast
      (<200 ms navigation on a few hundred runs).

## PR checklist
Title `phase-08: HUD viewer`. **ADR-0007** (frontend stack + embedding strategy; brief’s
“ADR-0006” was already taken by the recovery ladder).
