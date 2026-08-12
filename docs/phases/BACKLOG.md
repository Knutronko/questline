# Questline phase backlog

Out-of-scope discoveries and deferred improvements from phase PRs.
Format: `- [ ] (phase-NN) description`

---

- [ ] (phase-01) Add strict mypy to CI (`mypy src/`) — Phase 0 did not ship it; keep typing clean and gate later.
- [ ] (phase-01) Probe-budget path in `wait_for` (architecture distinguishes probe vs deadline; only deadline loop shipped). Phase 02 implements probe/deadline budgets inside `DriverPort.find` only.
- [ ] (phase-01) Dedicated `artifacts` SQLite table (currently events-only via `ArtifactSaved`).
- [ ] (phase-00) Backfill CONTRIBUTING.md, ADR-0001, pre-commit, extras stubs if still missing from bootstrap gaps.
- [ ] (fp-f) Feature registry tables (`features`, `feature_links`, …) via store migrations — see `docs/FEATURE-PIPELINE-PLAN.md`; hooks landed in phase-01 (migrations + event `tags`) and phase-03 (`tests.feature_id`, `--feature`, quarantine `feature` field).
- [ ] (phase-02) CI check that `examples/generated_locators.py` matches codegen output (drift gate).
- [ ] (phase-02) Shared `find` wait helper extracted for adapters (today each adapter must reimplement probe/deadline budgeting around `wait_for`).
- [ ] (phase-02) `Locator.scope` semantics beyond path-substring filter — document per-adapter or normalize in port helpers.
- [x] (phase-03) Richer death-point API (close_code, structured HealthSnapshot) once Phase 06 HealthMonitor exists — plugin now stores `HealthSnapshot.as_tags()` (+ app_state) on failure; `close_code` still on `SessionLost` events / `SessionLostError`.
- [ ] (phase-03) Plugin auto-discovery of project `questline.toml` at repo root without `--questline-config` when running nested example suites.
- [ ] (phase-03) Quarantine audit nodeid normalization helper (Windows `\` vs `/`) shared by CLI and CI.
- [x] (phase-05 exit) Scaffold game-repo `automation/` — **done** (Editor coverage-demo
      green 2026-08-09). Poco UI assertions remain (phase-14 / QL-4).
      See `docs/GAME-INTEGRATION.md` §3.
- [x] (phase-04) Live path superseded by Wire; Desktop abandoned.
- [x] (phase-05b) Editor `wire-smoke` green; Wire MVP done. Poco UI remains (phase-14).
- [x] (phase-05b follow-up) Android Wire smoke after Dev APK rebuild — green 2026-08-09
      (`android_local` + `adb forward`; reverse steals device `:port`).
- [ ] (phase-14) Poco as **second** UI hierarchy adapter (+ UTF); Wire v2 UI is phase-09b.
- [x] (phase-09b) Wire v2 find/hierarchy/tap/screenshot — FakeWire CI + companion UI ops;
      game trigger QL-2c (sync companion + Dev APK).
- [ ] (phase-09c) Wire swipe/drag/long-press — **parked**; schedule only if FP-G3
      playability gate fails (BALANCE-AUTOMATION §5 / phase-09c brief).
- [ ] (fp-g1) AI implications live report — deferred to phase-11 (snapshot/diff ships first).
- [ ] (fp-g1) HUD GameLens panel (list snapshots / show typed diff) — deferred until
      FP-G2/G3 produce measured data worth browsing beside config diffs; CLI is MVP.
- [ ] (fp-g2) Thin telemetry before FP-G3 bots — do not wait for D12-only scheduling.
- [ ] (fp-g3) Deterministic bots do **not** wait for phase-13; AI policies after phase-11.
- [ ] (phase-09) Companion `draw_calls` is a reserved slot (always 0 in Runtime asmdef —
      no UnityEditor dependency). Optional Editor-only extension or game-injected counter.
- [ ] (phase-09) PerfProbe anomaly detection / soak trend analysis — deferred (phase brief
      out of scope; see AI roadmap / future phases).
- [x] (phase-09) HUD graphs / compare — done in phase-10.
- [ ] (phase-10) Command palette / “run any CLI” inside HUD — out of scope; keep
      `questline doctor` / one-off reports as CLI until a future phase claims it.
- [ ] (phase-12) AI action buttons in HUD (triage/maintainer triggers).
- [ ] (phase-09) Document PowerShell clear of `QUESTLINE_PERF_*` in every live how-to that
      follows a perf dogfood (see INC-0001) — done in wire-setup + performance.md; keep
      citing INC when adding new live recipes.
- [ ] (phase-05) Add Unity `.meta` files under `unity-package/` so git UPM (`questline.git?path=unity-package`) is importable — today Unity ignores the immutable package without `.meta`, forcing games to embed/copy the companion (ElJuegaso workaround). Cheap follow-up; deferred to avoid diluting Android scope.
- [ ] (phase-05) `questline devices list|lock` CLI surface (architecture CLI mentions `devices`; provider is enough for android_local pytest wiring).
- [ ] (phase-05) Sample-project minimal Android APK in-repo for CI-less live dogfood when game QL-2 is pending (optional; maintainer may use a local sample instead).
- [ ] (docs) Optional GitHub Project board (proposal B) or Notion cockpit (proposal C) mirroring `STATUS-DUAL.md` — only if maintainer wants a second visual layer.
