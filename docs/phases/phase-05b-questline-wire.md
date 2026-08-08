# Phase 05b — QuestlineWire (live driver without AltTester Desktop)

> Session preamble: see `phase-00-bootstrap.md`. Read `docs/01-ARCHITECTURE.md` §3.1 + §5.1,
> `docs/drivers.md`, ADR-0004, and **ADR-0005**.
>
> **Two gates (mandatory):**
> - **Gate A (this PR):** design only — ADR + this brief + status/integration docs.
>   **STOP for maintainer approval before coding.**
> - **Gate B (follow-up PR, same chat OK after explicit “go”):** implement listener +
>   Python driver + profiles + smoke.

## Context

Phases 00–05 are merged. `AltTesterDriver`, companion `QuestlineHooks`, and
`LocalAdbProvider` / `android_local` exist. Live e2e that needs AltTester Desktop is
**blocked** (€0 Community/Desktop mismatch — see ADR-0005 and reference-game §8).
QL-1/QL-2 game code (hooks, Dev APK, Verify) remains valid; do **not** rip AltTester UPM
from the game yet.

This phase is numbered **05b** (insert between 05 and 06): it unblocks phase-05 live
acceptance without renumbering resilience → release (06–15).

## Objective

Ship **QuestlineWire** so Editor (and, if feasible, Android) hooks-first smoke runs
**without** AltTester Desktop, behind `DriverPort` + `DriverHandle`, exportable via
companion + profile config.

## MVP scope (locked)

### In

1. **C# listener** in `unity-package` (companion) speaking ADR-0005 NDJSON/TCP protocol;
   wired to existing `QuestlineHooks` (`GetManifestJson` / `InvokeHook`).
2. Compile gate: `#if UNITY_EDITOR || QUESTLINE_DEV` (or equivalent). No release builds.
3. **Python `QuestlineDriver`** (`driver = "questline"`) implementing `DriverPort`:
   `connect` / `disconnect` / `is_alive` / `app_state` / `call_game_method` /
   `hooks_manifest` (+ soft-reload reconnect). Module path:
   `questline.drivers.wire` (avoid `questline.drivers.questline` stutter); registry key
   remains `"questline"`.
4. Non-MVP UI methods (`find` / `find_all` / `hierarchy` / `screenshot` / `tap` /
   `press` / `swipe` / `text_input`): clear `NotImplementedError` or `AuthoringError`
   with pointer to Wire MVP / phase-14 Poco — documented in `drivers.md`.
5. Profiles / extras: smoke runnable without `[alttester]` Desktop — e.g.
   `editor` + `android_local` variants with `driver = "questline"`, port **13000**,
   Android via existing `LocalAdbProvider` + `adb reverse`.
6. **Smoke:** dedicated `examples/wire-smoke` (hooks-first) green on **Editor** live
   without Desktop. Prefer not to break AltTester-oriented `examples/unity-smoke`.
7. **Conformance:** run the subset that applies (connect/alive/disconnect, app_state,
   call_game_method / hooks); document deferred UI assertions.
8. Promote `hooks_manifest()` onto `DriverPort` (or shared protocol helper used by both
   AltTester and Wire) — closes phase-04 backlog note.
9. Sync notes for reference game (QL-2b later): bootstrap enable Wire, defines, files to
   refresh from companion — **no** game `automation/` scaffold yet.
10. Update `STATUS-DUAL.md` + this checklist; PR with Cómo probarlo (PowerShell).

### Out of MVP

- Full hierarchy / find / tap parity with AltTester
- Poco / Appium
- Ripping AltTester from examples or reference-game UPM overnight
- Auth on the wire, non-loopback bind, paid services, Desktop reinstall
- Scaffolding game-repo `automation/` (still gated on first green live smoke)

## Profiles

| Profile | Driver | Host/port | Device | Notes |
|---------|--------|-----------|--------|-------|
| `editor` (wire) | `questline` | `127.0.0.1:13000` | none | Editor play mode; Wire listener started by companion bootstrap |
| `android_local` (wire) | `questline` | `127.0.0.1:13000` after reverse | `adb` / `LocalAdbProvider` | Same reverse story as phase-05; APK must be `QUESTLINE_DEV` with Wire compiled in |
| legacy AltTester profiles | `alttester` | same port | as today | Optional; mutually exclusive with Wire on :13000 |

## Port choice

**Keep 13000** (ADR-0005). Document mutual exclusion with AltTester Prefab.

## Error mapping

See ADR-0005 §8 table → existing taxonomy (`InfraError` / `SessionLostError` /
`AuthoringError` / `TestError`).

## Non-goals

- Replacing MockDriver as CI default
- Changing the hooks registration API games already use
- ElJuegaso gameplay / D10–D11
- Force-push / secrets in PRs

## Acceptance criteria

### Gate A (this PR — docs only)

- [x] ADR-0005 merged (or open for approval) with transport, port, security, protocol sketch
- [x] This brief locked (DoD, MVP in/out, profiles, error mapping)
- [x] `GAME-INTEGRATION.md` + `STATUS-DUAL.md` updated (blocked AltTester live → next = Wire)
- [ ] Maintainer **explicit go** before Gate B coding

### Gate B (implement — after go)

- [ ] Companion listener + bootstrap API under define gate; unit-testable protocol helpers where practical
- [ ] `QuestlineDriver` + plugin registry `driver = "questline"` (no `[alttester]` required)
- [ ] Soft-reload reconnect regression (fake or live)
- [ ] CI: fake-transport / protocol unit tests green; conformance subset green
- [ ] Maintainer-checked: `examples/wire-smoke` green on Editor without Desktop
- [ ] Android: green via `adb reverse` in same PR **or** documented follow-up DoD if blocked
- [ ] Deferred conformance / UI methods documented
- [ ] QL-2b sync notes (exact companion files to refresh in reference game)
- [ ] `STATUS-DUAL.md` + phase checklist updated; PR test plan (PowerShell)

## PR checklist

| Gate | Title (English, repo style) |
|------|-----------------------------|
| A | `docs(phase-05b): QuestlineWire ADR + brief` |
| B | `phase-05b: QuestlineWire driver + companion listener` |

ADR-0005. Do not implement in Gate A.
