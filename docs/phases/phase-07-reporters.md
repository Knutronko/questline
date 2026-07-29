# Phase 07 — Reporters: Slack + GitHub Issues (+ console/HTML)

> Session preamble: see `phase-00-bootstrap.md`. Read `docs/01-ARCHITECTURE.md §3.3`.

## Context
Phases 00–06 merged. Runs produce a rich event stream and classified verdicts. Nothing
reports them anywhere yet except the console log.

## Objective
`ReporterPort` + four adapters. Configured per profile; multiple reporters run in parallel;
a reporter crash never affects the run (bus isolation from Phase 01 is the guarantee).

## In scope
1. **ReporterPort** (`reporters/port.py`): `on_event(event)` + `finalize(run_summary)`;
   registration from config (`reporters = ["console", "slack"]`).
2. **ConsoleReporter**: rich live progress (current test, step, pass/fail counters).
3. **HtmlReporter**: static single-file HTML summary artifact per run (no server needed —
   the shareable artifact; HUD comes later for the interactive view).
4. **SlackReporter** (`questline[slack]`): run-start post (suite, profile, device) →
   updated/threaded on finish (totals, duration, verdict breakdown infra/test); per-failure
   thread replies (test, error class, death-point step, screenshot upload optional);
   webhook or bot-token modes; message templates as files; **allow-list rendering** —
   only whitelisted fields ever leave the machine (unit test: a poisoned artifact path/env
   var never appears in a rendered message).
5. **GitHubIssuesReporter**: files issues for `verdict=test` failures ONLY (never infra);
   dedupe by failure signature hash (test_id + error class + normalized message) — reruns
   comment instead of duplicating; auto-label; optional auto-close on green (config).
6. **Stubs**: `NotionReporter`, `JiraReporter`, `TestRailReporter` — port-conformant
   classes raising `NotImplementedError` with docs describing intended mapping.
7. Docs: `docs/reporting.md` + secrets setup (env vars only).

## Out of scope
HUD, AI digests (Phase 12 posts through these reporters).

## Acceptance criteria
- [ ] CI: all adapters unit-tested against recorded/fake transports (no live calls in CI).
- [ ] Maintainer-checked: demo run posts to a real Slack workspace with correct threading.
- [ ] Maintainer-checked: forced test failure files a GitHub issue in a sandbox repo;
      rerun dedupes (comments, no duplicate); infra failure files NOTHING.
- [ ] Allow-list rendering test passes.
- [ ] Reporter crash isolation test: a reporter that raises on every event → run completes,
      other reporters unaffected, error logged.

## PR checklist
Title `phase-07: reporters`.
