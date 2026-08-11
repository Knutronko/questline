# Phase 09b — QuestlineWire v2 (find / hierarchy / tap / screenshot)

> Session preamble: see `phase-00-bootstrap.md`. Read **ADR-0008**, ADR-0005 (transport),
> ADR-0003 (locators), `docs/01-ARCHITECTURE.md` §3.1, `docs/wire-setup.md`,
> `docs/drivers.md`, and `DriverPort` / `questline.drivers.wire`.
>
> **Prerequisite:** phase-09 (PerfProbe) merged (or maintainer explicitly waives).
> **Do not renumber** phases 10–15 — this is a Wire follow-up like 05b.

## Context

Phases 00–08 (+ 05b Wire MVP) are merged; **09** adds PerfProbe. Wire today is
hooks/session only: `find` / `hierarchy` / `tap` / `screenshot` raise
`AuthoringError` (“use Poco”). Game `automation/` and future **GameLens FP-G3** bot
playthroughs need €0 UI navigation **before** phase-14 Poco and before deep balance
automation. Maintainer order: **09 → 09b → D11 / FP-G1**.

## Objective

Ship **Wire v2 UI ops** on the existing NDJSON listener so `driver = "questline"` can
find/tap through a real Unity hierarchy (Editor first; Android via existing
`adb forward` path), with Fake-transport CI and an extended `wire-smoke`.

## In scope

1. **ADR-0008** already accepted in the docs PR — implement it; do not reopen the
   Poco-vs-Wire role split unless blocked.
2. **C# companion** (`unity-package`): handlers for `hierarchy`, `find`, `find_all`,
   `tap`, `screenshot`; advertise `protocol_version` / `features` on `hello`; keep
   MVP hooks ops unchanged; `#if UNITY_EDITOR || QUESTLINE_DEV` only; hierarchy caps.
3. **Python `QuestlineDriver`:** implement the same methods on `DriverPort` (remove
   MVP UI stubs for those five); Locator compile per ADR-0003; wait probe/deadline;
   map errors to taxonomy; leave `press` / `swipe` / `text_input` as explicit
   `AuthoringError` (or thin wrappers if free).
4. **FakeWireTransport** (+ unit/conformance subset) green in CI without Unity.
5. **`examples/wire-smoke`:** at least one test that finds a known GO / UI marker and
   taps (or asserts hierarchy contains it). Document live flags.
6. **Docs:** `wire-setup.md` roadmap row → ✅; parity note vs Mock/Poco; game **QL-2c**
   sync notes (refresh companion + rebuild Dev APK). Update STATUS-DUAL when done.
7. **Optional maintainer:** Android Wire v2 smoke after QL-2c APK rebuild.

## Out of scope

- PocoDriver / UTF (phase-14)
- GameLens FP-G1–G3 implementation
- PerfProbe (09) / HUD II (10)
- Full gesture/text_input parity; AltTester Desktop; non-loopback bind; auth
- Ripping AltTester UPM from the reference game
- Renaming phases 10–15

## Protocol (summary — detail in ADR-0008)

Same NDJSON framing as ADR-0005. New ops: `hierarchy`, `find`, `find_all`, `tap`,
`screenshot`. `hello` advertises UI capability. Element / hierarchy JSON must round-trip
to `Element` / `HierarchySnapshot` without leaking Unity types to tests.

## Error mapping

| Condition | Error | Verdict |
|-----------|--------|---------|
| Socket / disconnect mid-op | `SessionLostError` | infra |
| Element missing after wait | `ElementNotFoundError` | test |
| Bad locator / unknown op on old companion | `AuthoringError` | authoring |
| UI op not implemented (`swipe`…) | `AuthoringError` (explicit message) | authoring |

## Game trigger

| Framework | Game |
|-----------|------|
| **09b** | **QL-2c** — sync `QuestlineWireServer` (+ any new companion files), Editor verify, rebuild `QUESTLINE_DEV` APK for Android |

**HUD:** Wire v2 reuses existing screenshot / `ArtifactSaved` paths — **no new HUD
pages/APIs in 09b** (same deferral contract as phase 09 → graphs in 10). See `docs/hud.md`.

## Acceptance criteria

- [x] CI: Wire UI unit tests via fake transport; existing hooks smoke still green;
      **full matrix below** covered (or explicitly skipped with reason).
- [x] `examples/wire-smoke` includes a UI find/(tap|hierarchy) case; maintainer Editor live green.
- [x] `hello` feature/`protocol_version` gate documented; old companion → clear error on UI ops.
- [x] Docs + **STATUS-DUAL** (semáforo + roadmap + **Mermaid §4**) + GAME-INTEGRATION QL-2c
      row updated; ADR-0008 remains accepted; `wire-setup.md` roadmap row → ✅.
- [ ] Optional: Android live after QL-2c APK.

## Required test matrix (before merge)

Enumerate and cover (FakeWire unit **and** live Editor where marked). Do **not** merge
with only a happy-path tap.

| Area | Cases (minimum) |
|------|-----------------|
| `hierarchy` | empty/minimal tree; depth/node caps enforced; stable ids round-trip |
| `find` / `find_all` | by `name`, `id`, `path`, `text`, `component`; scope filter; 0 matches → wait then `ElementNotFoundError`; multiple matches (`find` vs `find_all`) |
| `tap` | Element from prior find; `Point` screen tap; missing/stale element id |
| `screenshot` | non-empty PNG bytes; failure path maps cleanly (no silent empty) |
| Transport / versioning | old companion (no `ui` feature) → `AuthoringError` on UI ops; hooks still work; disconnect mid-op → `SessionLostError` |
| Regression | MVP hooks (`hello`/`ping`/`call_hook`/`hooks_manifest`) unchanged |
| Conformance | Wire driver passes hooks + new UI subset (or documented skip for deferred gestures) |
| Live | Editor wire-smoke find+tap; document Android as optional maintainer / QL-2c |

`press` / `swipe` / `text_input` must remain explicit `AuthoringError` (message points to
backlog / hooks), with a unit test each.

## PR checklist

Title `phase-09b: Wire v2 find/hierarchy/tap`. Self-review section required.
PowerShell Cómo probarlo (Editor `QUESTLINE_LIVE_TARGET=1` + wire-smoke).
**Docs gate:** STATUS-DUAL Mermaid + tables; wire-setup; GAME-INTEGRATION; hud.md evolution
row if UI runs produce new artifacts users should see (or explicitly defer).

## Lessons / incidents

| Id | Lesson |
|----|--------|
| [INC-0001](../incidents/INC-0001-wire-perf-socket-race.md) | Live wire-smoke saw `hooks_manifest`/`hierarchy` return `GetPerfSample` payloads — leftover `QUESTLINE_PERF_ENABLED`; fixed with transport lock + id check + clear-env docs. |
| [INC-0002](../incidents/INC-0002-companion-sync-uncommitted.md) | Editor AC needs game companion v2 in Play (`listening … (v2)`); framework-only merge is not enough — QL-2c PR required. |

Maintainer Editor live: **green** 2026-08-11 (`examples/wire-smoke` 4 passed after INC-0001 clear-env + lock).
