# Phase 02 — Driver abstraction + MockDriver + conformance suite

> Session preamble: see `phase-00-bootstrap.md`. Read `docs/01-ARCHITECTURE.md §3.1`.

## Context
Phases 00–01 merged: kernel (config, events, store, errors, waits) exists.

## Objective
The `DriverPort` protocol, the driver-agnostic locator model, the `DriverHandle` live
indirection, a full in-memory `MockDriver`, and the **conformance suite** any real adapter
must pass. This phase decides how easy "switching drivers" really is — design carefully.

## In scope
1. `drivers/port.py`: `DriverPort` protocol per architecture §3.1 (connect/find/hierarchy/
   screenshot/interactions/`call_game_method`/app_state) + `ConnectionTarget`, `Element`,
   `HierarchySnapshot` (normalized node tree), `AppState`.
2. **Locator model** (`drivers/locators.py`): `Locator(by, value, scope)`; registry loader
   for `locators.yaml` + codegen script emitting typed accessors (generated file committed,
   never hand-edited, header says so); adapter-side `compile(Locator) -> native query`
   hook.
3. **DriverHandle** (`drivers/handle.py`): provider indirection — all consumers hold the
   handle, never the driver; `reset()` swaps the underlying driver atomically; a test
   proves stale-reference bugs are impossible (old driver disposed, consumers keep working).
4. **MockDriver** (`drivers/mock/`): in-memory scene graph (nodes, visibility, tap handlers,
   text), scriptable behaviors (element appears after N ms; connection drops on command K)
   — the fault-injection substrate later phases reuse.
5. **Conformance suite** (`drivers/conformance.py`): parametrized pytest suite that takes
   any `DriverPort` factory and verifies semantic contracts: find vs wait behavior under
   both timeout kinds, error mapping to the taxonomy (§2.4), hierarchy normalization,
   screenshot bytes, interaction acknowledgement, `is_alive` truthfulness after forced
   disconnect. MockDriver must pass 100%.
6. Docs: `docs/drivers.md` — how to write an adapter (checklist + conformance run command).

## Out of scope
Real adapters (AltTester = Phase 04, Poco = Phase 14, Appium = Phase 15 backlog),
pages/steps (Phase 03).

## Acceptance criteria
- [ ] MockDriver passes the full conformance suite in CI.
- [ ] Locator codegen: sample `locators.yaml` → generated module → used in a test.
- [ ] DriverHandle stale-reference test passes (reset mid-use, no consumer breaks).
- [ ] Fault injection demonstrated: scripted disconnect surfaces as `SessionLostError`
      with correct verdict `infra`.
- [ ] Coverage ≥ 90% on `drivers/` (excluding generated code).

## PR checklist
Title `phase-02: driver abstraction`. ADR-0003 (locator model & why adapters compile it).
