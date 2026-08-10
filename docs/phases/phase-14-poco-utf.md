# Phase 14 — Poco (second UI backend) + Unity Test Framework ingestion

> Session preamble: see `phase-00-bootstrap.md`. Read `docs/01-ARCHITECTURE.md §3.1 + §5.2`
> and **ADR-0008**. Happy-path live hooks **and** Unity find/tap use **QuestlineWire**
> (05b + **09b**). **Poco** proves a second UI adapter (and covers richer / non-Unity
> cases). Prefer Poco over legacy AltTester when Wire is not enough. If PocoDriver needs
> `DriverPort` changes, record an ADR.

## Context
Phases 00–13 (and 05b / **09b** Wire) merged. Wire covers hooks/session **and**
lightweight Unity hierarchy/find/tap/screenshot (ADR-0008). AltTester remains a
**legacy remoto** adapter (Desktop). The claim "easy to switch drivers" still needs a
**second UI backend** — that is Poco.

## Objective
`PocoDriver` passing the conformance suite against a real Unity target, and Unity Test
Framework (C#) results ingested into the same run store/HUD.

## In scope
1. **PocoDriver** (`drivers/poco/`, extra `questline[poco]`): DriverPort over Poco;
   locator compilation; hierarchy normalization; error mapping. Pin versions; document
   quirks in `docs/drivers.md`. Port gaps → ADR before changing `DriverPort`.
2. **Docs:** wire-setup = happy-path Unity (hooks + Wire v2 UI); Poco side-by-side as
   alternate UI backend (not AltTester).
3. **Conformance parity:** Wire (hooks + UI subset) + Poco (full UI) + Mock; publish parity table.
4. **UTF orchestration** (`questline unity-test run`): batchmode `-runTests`, NUnit XML → store.
5. **Demo:** smoke / pages green via `driver = "questline"` (Wire) and `driver = "poco"`
   by flipping profile — **not** requiring `alttester`.

## Out of scope
Reviving AltTester Desktop as primary; Appium (backlog); iOS; farms.
Wire v2 UI is **phase-09b** (not deferred here).

## Acceptance criteria
- [ ] CI: PocoDriver unit tests (transport mocked); UTF XML parser green on fixtures.
- [ ] Maintainer-checked: conformance vs live Poco target; profile flip Wire↔Poco where applicable.
- [ ] Maintainer-checked: `questline unity-test run` → C# results in HUD.
- [ ] Parity table published; any port change in ADR.

## PR checklist
Title `phase-14: poco driver + utf ingestion`.
