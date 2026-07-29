# Phase 14 — Second driver (Poco) + Unity Test Framework ingestion

> Session preamble: see `phase-00-bootstrap.md`. Read `docs/01-ARCHITECTURE.md §3.1 + §5.2`.
> This phase PROVES the driver abstraction: if PocoDriver needs changes to `DriverPort`,
> that is a finding, not a failure — record it in an ADR and adjust the port deliberately.

## Context
Phases 00–13 merged. One real driver (AltTester) passes conformance. The claim "easy to
switch drivers" is so far only proven against a mock.

## Objective
`PocoDriver` passing the conformance suite against a real Unity target, and Unity Test
Framework (C#) results ingested into the same run store/HUD.

## In scope
1. **PocoDriver** (`drivers/poco/`, extra `questline[poco]`): implements DriverPort over
   poco / poco-sdk Unity integration; locator compilation Locator → Poco selector;
   hierarchy normalization to the same `HierarchySnapshot` shape; error mapping to the
   taxonomy. NOTE: the Poco Unity SDK is community-maintained and less active than
   AltTester — pin versions, document quirks in `docs/drivers.md`, and if a DriverPort
   gap appears, write ADR-0008 before changing the port.
2. **Companion package**: add the Poco SDK integration notes to `docs/unity-setup.md`
   (side-by-side with AltTester; both can coexist in a dev build).
3. **Conformance parity report**: run the conformance suite against both drivers; publish
   a parity table in docs (which semantics differ, how the port hides them).
4. **UTF orchestration** (`unity/utf.py` + CLI `questline unity-test run`): launch Unity
   batchmode `-runTests` (edit + play mode), parse NUnit XML, ingest results as a run in
   the store (suite = "unity-utf"); C# results appear in HUD next to Python runs; docs on
   writing UTF tests that use `QuestlineHooks` for setup.
5. **Demo**: the smoke suite green on the maintainer's game via BOTH drivers by flipping
   profile only (`driver = "alttester"` → `driver = "poco"`).

## Out of scope
Appium driver (backlog), iOS, farms.

## Acceptance criteria
- [ ] CI: PocoDriver unit tests (transport mocked); UTF XML parser green on fixtures
      (including failures + skipped).
- [ ] Maintainer-checked: conformance suite vs a live Poco-instrumented target; smoke suite
      green via both drivers with a one-line profile change.
- [ ] Maintainer-checked: `questline unity-test run` on their game → C# results in HUD.
- [ ] Parity table published; any port change documented in ADR-0008.

## PR checklist
Title `phase-14: poco driver + utf ingestion`.
