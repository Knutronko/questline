# Phase 14 — Poco (primary UI hierarchy) + Unity Test Framework ingestion

> Session preamble: see `phase-00-bootstrap.md`. Read `docs/01-ARCHITECTURE.md §3.1 + §5.2`.
> This phase PROVES the driver abstraction for **UI hierarchy**. Happy-path live hooks
> already use **QuestlineWire** (05b). **Poco** is preferred over legacy AltTester for
> find / hierarchy / tap. If PocoDriver needs `DriverPort` changes, record an ADR.

## Context
Phases 00–13 (and 05b Wire) merged. Wire covers hooks/session without Desktop.
AltTester remains a **legacy remoto** adapter (Desktop). The claim "easy to switch
drivers" needs a second **UI** backend — that is Poco, not AltTester.

## Objective
`PocoDriver` passing the conformance suite against a real Unity target, and Unity Test
Framework (C#) results ingested into the same run store/HUD.

## In scope
1. **PocoDriver** (`drivers/poco/`, extra `questline[poco]`): DriverPort over Poco;
   locator compilation; hierarchy normalization; error mapping. Pin versions; document
   quirks in `docs/drivers.md`. Port gaps → ADR before changing `DriverPort`.
2. **Docs:** wire-setup stays happy-path hooks; Poco side-by-side for UI (not AltTester).
3. **Conformance parity:** Wire (hooks subset) + Poco (full UI) + Mock; publish parity table.
4. **UTF orchestration** (`questline unity-test run`): batchmode `-runTests`, NUnit XML → store.
5. **Demo:** smoke / pages green via `driver = "questline"` (hooks) and `driver = "poco"` (UI)
   by flipping profile — **not** requiring `alttester`.

## Out of scope
Reviving AltTester Desktop as primary; Appium (backlog); iOS; farms; Wire v2 UI parity
(explicitly deferred to Poco).

## Acceptance criteria
- [ ] CI: PocoDriver unit tests (transport mocked); UTF XML parser green on fixtures.
- [ ] Maintainer-checked: conformance vs live Poco target; profile flip Wire↔Poco where applicable.
- [ ] Maintainer-checked: `questline unity-test run` → C# results in HUD.
- [ ] Parity table published; any port change in ADR.

## PR checklist
Title `phase-14: poco driver + utf ingestion`.
