# Phase 01 — Core kernel

> Session preamble: see the "How to use this brief" block in `phase-00-bootstrap.md`.
> Read `docs/01-ARCHITECTURE.md §2` — this phase implements it.

## Context
Phase 00 merged: scaffold + CI gate exist. `src/questline/core/` is empty.

## Objective
The kernel every other module depends on: config/profiles, event bus, run store,
error taxonomy, wait primitive, JSONL ledger. Fully unit-tested; no external services.

## In scope
1. **Config** (`core/config.py`): `questline.toml` loader with `[profile.<name>]` tables;
   resolution CLI-flag > env (`QUESTLINE_*`) > profile > default; typed `Settings` model
   (pydantic); actionable startup errors (missing key names the fix). Secrets only via env.
2. **Event bus** (`core/events.py`): typed frozen dataclass events per architecture §2.2;
   sync pub/sub; subscriber errors are isolated (one bad reporter never kills a run) but
   logged loudly.
3. **Run store** (`core/store.py`): SQLite schema §2.3 (`runs, tests, steps, events,
   perf_samples, ai_calls, quarantine`); incremental transactional writes driven by
   subscribing to the bus; artifact directory manager (save bytes → path + `ArtifactSaved`
   event); JSONL append-only ledger mirror.
4. **Error taxonomy** (`core/errors.py`): hierarchy per §2.4 + `classify(exc) ->
   Verdict(infra|test|authoring|unknown)`.
5. **Wait primitive** (`core/waits.py`): `WaitPolicy(probe, deadline, interval)` +
   `wait_for(condition, policy, on_timeout=...)`; condition exceptions count as failed
   probes; composition/override rules per §2.5; **regression test proving no code path can
   silently reset a caller's configured timeout**.
6. **Structured logging** (`core/log.py`): stdlib logging with JSON formatter option;
   every event also logged.
7. CLI stub (`questline --version`, `questline doctor` printing resolved profile).

## Out of scope
Drivers, devices, reporters, HUD, AI, resilience/recovery (Phase 06).

## Acceptance criteria
- [ ] Unit coverage ≥ 90% on `core/`; all CI checks green.
- [ ] Kill-safety test: simulated run writer killed mid-run → store contains all events
      up to the kill point (incremental persistence proven).
- [ ] Store can reconstruct a full run timeline (steps with real timestamps) from a
      scripted fake run.
- [ ] `questline doctor` prints the resolved profile from a sample `questline.toml`.
- [ ] Timeout-override regression test exists and passes.

## PR checklist
Title `phase-01: core kernel`. ADR-0002 (SQLite + JSONL mirror choice, 10 lines).
