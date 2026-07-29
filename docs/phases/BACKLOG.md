# Questline phase backlog

Out-of-scope discoveries and deferred improvements from phase PRs.
Format: `- [ ] (phase-NN) description`

---

- [ ] (phase-01) Add strict mypy to CI (`mypy src/`) — Phase 0 did not ship it; keep typing clean and gate later.
- [ ] (phase-01) Probe-budget path in `wait_for` (architecture distinguishes probe vs deadline; only deadline loop shipped).
- [ ] (phase-01) Dedicated `artifacts` SQLite table (currently events-only via `ArtifactSaved`).
- [ ] (phase-00) Backfill CONTRIBUTING.md, ADR-0001, pre-commit, extras stubs if still missing from bootstrap gaps.
