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
- [ ] (phase-03) Richer death-point API (close_code, structured HealthSnapshot) once Phase 06 HealthMonitor exists — today plugin stores `is_alive` + `app_state` in TestFinished.tags.
- [ ] (phase-03) Plugin auto-discovery of project `questline.toml` at repo root without `--questline-config` when running nested example suites.
- [ ] (phase-03) Quarantine audit nodeid normalization helper (Windows `\` vs `/`) shared by CLI and CI.
