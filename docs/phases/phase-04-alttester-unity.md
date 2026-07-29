# Phase 04 — AltTester adapter + Unity companion package (first real green)

> Session preamble: see `phase-00-bootstrap.md`. Read `docs/01-ARCHITECTURE.md §3.1 + §5.1`.
> NOTE: parts of this phase require the maintainer's Unity project and manual verification —
> the brief marks which acceptance items are CI-checkable vs maintainer-checked.

## Context
Phases 00–03 merged. MockDriver passes conformance; demo suite runs. No real driver yet.
The maintainer has a personal Unity game (Android target) to integrate against, and will
handle Unity Editor operations locally.

## Objective
`AltTesterDriver` passing the conformance suite against a real Unity target (Editor play
mode and Windows standalone), plus v0 of the `com.questline.companion` UPM package.

## In scope
1. **AltTesterDriver** (`drivers/alttester/`, extra `questline[alttester]`): implements
   DriverPort over the AltTester Python driver; locator compilation Locator → AltTester
   query language; hierarchy normalization; screenshot; error mapping (WebSocket close
   codes → taxonomy: at minimum "no app with tag" → `InfraError`, "app disconnected" →
   `SessionLostError(kind)`); connection targets: `editor` (localhost), `standalone_exe`,
   `android` (used in Phase 05).
2. **Unity companion package v0** (`unity-package/`): UPM layout
   (`com.questline.companion`); `QuestlineHooks` registry (typed debug hooks the game
   registers; e.g. `SetLevel`, `GrantSoftCurrency`, `SkipTutorial`); hooks declare
   `causesSoftReload` — the Python side auto re-handshakes the driver after such hooks
   (no silent session death; regression-tested against a scripted reload in Editor).
   `call_game_method` on the driver resolves hooks by name with typed args.
3. **Setup docs** (`docs/unity-setup.md`): step-by-step — install AltTester Unity SDK +
   companion package into a game, build flags, run first test. Written for a stranger.
4. **Smoke suite** (`examples/unity-smoke/`): 3–5 tests (app boots, hierarchy non-empty,
   tap a button, call a hook, screenshot artifact saved) meant to run against ANY game
   that has the two packages installed.

## Out of scope
Android/adb (Phase 05), Poco (Phase 14), perf counters (Phase 09), UTF orchestration (14).

## Acceptance criteria
- [ ] CI: adapter unit tests green (transport mocked); conformance suite tagged
      `@requires_live_target` for the live half.
- [ ] Maintainer-checked: conformance suite passes against Editor play mode.
- [ ] Maintainer-checked: smoke suite green against Editor AND Windows standalone build.
- [ ] Maintainer-checked: `causesSoftReload` hook → driver re-handshake happens
      automatically and the following step succeeds.
- [ ] `docs/unity-setup.md` validated by actually following it.

## PR checklist
Title `phase-04: alttester adapter + unity companion`. ADR-0004 (companion hook contract).
