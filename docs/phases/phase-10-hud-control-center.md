# Phase 10 — HUD II: control center + perf graphs

> Session preamble: see `phase-00-bootstrap.md`. Read `docs/01-ARCHITECTURE.md §6`.

## Context
Phases 00–09 merged. HUD viewer works; PerfProbe data exists; quarantine ledger is CLI-only.

## Objective
HUD becomes the framework's control center: launch and manage runs, manage quarantine,
edit profiles, and visualize performance — all local, all backed by the same public APIs
the CLI uses (no UI-only code paths).

## In scope
1. **Run launcher**: UI to compose a run — profile picker, marker/test selection (from
   collected test list), device picker (live from DeviceProvider discovery), reporter
   toggles → starts a run as a managed subprocess; live view attaches automatically;
   stop button = graceful cancel (store sealed, reporters finalize). Concurrent-run guard
   honors the device lock from Phase 05.
2. **Quarantine management**: ledger-backed list (reason, age, owner, exit criteria,
   linked issue); add/remove through the same code path as the CLI (symmetry guaranteed);
   "limbo audit" button surfacing marker↔ledger mismatches.
3. **Profile/config editor**: form-based editing of `questline.toml` profiles with
   validation (same pydantic models) and diff preview before save; secrets shown as
   env-var names only, never values.
4. **Perf graphs**: series per run/test with threshold overlays; build-over-build
   comparison (pick 2 runs → deltas per metric); flakiness board gains a duration-vs-pass
   correlation view.
5. **Safety**: every mutating endpoint is localhost-only + CSRF token; a `--read-only`
   flag serves Phase-08 behavior for viewing on another machine.
6. Docs: `docs/hud.md` updated (control center section + screenshots).

## Out of scope
AI actions in HUD (buttons land with Phase 12), auth/multi-user, remote agents.

## Acceptance criteria
- [ ] CI: endpoint tests for launcher/quarantine/config APIs (subprocess mocked); UI smoke
      extends Phase-08 Playwright run (launch mock run from UI → see it live → stop it).
- [ ] Maintainer-checked: full loop on real hardware — compose run in HUD against their
      phone, watch live, stop, inspect, quarantine a flaky test from the UI, exit it later.
- [ ] Config editor rejects an invalid profile with the same error the CLI would give.
- [ ] Perf comparison view renders two real runs side by side.

## PR checklist
Title `phase-10: HUD control center`.
