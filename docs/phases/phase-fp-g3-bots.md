# FP-G3 — Deterministic bots & measured difficulty curves

> Session preamble: see `phase-00-bootstrap.md`. Read **before coding:**
> [`BALANCE-AUTOMATION.md`](../BALANCE-AUTOMATION.md) (order G1 → **G2 → G3** → 11),
> [`telemetry.md`](../telemetry.md) + [`adr/ADR-0010-gamelens-telemetry.md`](../adr/ADR-0010-gamelens-telemetry.md),
> [`gamelens.md`](../gamelens.md) (attach `config_snapshot_id`),
> [`GAME-INTEGRATION.md`](../GAME-INTEGRATION.md) §4–§5,
> [`wire-setup.md`](../wire-setup.md), [`phase-09c`](phase-09c-wire-play-gestures.md) (parked),
> [`STATUS-DUAL.md`](../STATUS-DUAL.md).
>
> **Scheduled:** after FP-G2 ✅ and game **QL-6** (events actually emit).
> **Size:** L. Do **not** start until QL-6 dogfood produces at least one imported
> session from a live combat loop (Editor).
>
> **Does not wait on** phase-11, phase-13, or 09c (09c only if the playability gate fails).

## Context

FP-G1 is config truth; FP-G2 is measured truth (store + drain). This phase **exercises**
the game with deterministic policies so summaries become comparable curves
(version × policy × seed × snapshot).

Reference-game target levels: **IEB Pass B presets B1–B5** (policy details decided
here). Bots live in the **game** `automation/` suite (GAME-INTEGRATION §2), not in
questline core.

## Objective

Run N seeded sessions per (game_version, policy_id, snapshot) via Wire + hooks
(Tap deploy), drain telemetry into the store, and produce measured overlays
(summary diffs / curves from thin events + checkpoints). AI policies are **out**.

## In scope

1. **Policies (deterministic):** at least cheapest-deploy, rush, balanced,
   never-skill, always-skill (names are `policy_id` strings stored on the session).
2. **Session wiring (mandatory G2 contract):**
   - Before play (or immediately after combat start):
     `SetTelemetryContext` / `BeginTelemetrySession` JSON with
     `game_version`, `seed`, `policy_id`, `config_snapshot_id` (FP-G1 snapshot id
     used for this build), optional `feature_id` / `git_commit`.
   - Prefer `SetTelemetryContext` so the game’s own `BeginSession` is not wiped
     (ADR-0010 merge semantics: non-empty fields overwrite).
   - After the loop: `drain_telemetry(driver, store, end_outcome=..., run_id=...)`
     from `questline.telemetry.drain`.
   - Fixed `SetSeed` hook; same seed → same policy decisions.
3. **N repeats** per cell of the matrix (document N; start small, e.g. 3).
4. **Measured outputs:** use stored summaries (`deploy_count`, currency net,
   `time_to_first_leak`, waves, checkpoint labels). Do **not** invent KPIs in
   Python that the events cannot support. Amber-at-moment curves need QL-6
   `session.checkpoint` labels — if missing, list them as `pending QL-6 labels`,
   do not approximate from guesses.
5. **Compare:** `questline telemetry query <idA> --compare <idB>` and/or a small
   report (text/JSON) grouping by policy × version. Full HUD overlay is deferred
   with G2 HUD.
6. **Playability gate:** hooks + Tap first. If Drag/gestures are required on the
   measured path, **stop and schedule 09c** (do not silently Point-spam).
7. Missing combat hooks (`DeployAt`, select-unit, fire-skill, collect): add on
   the **game** side (not questline core names). Document hook names in
   `automation/` only.
8. Tests: matrix runner unit tests with FakeWire / mock driver + fixture spools
   (no Unity in CI). Live Editor dogfood is maintainer-checked.
9. Docs: STATUS-DUAL, BALANCE-AUTOMATION decision log, telemetry.md consumer
   note, HUD defer or explicit panel if summaries are worth browsing.

## Out of scope

- AI / LLM policies (after phase-11)
- 09c unless the gate fails
- Richer events (`combat.damage`, ranch, buff draft, relocate, revive) — those
  are D12 / G2+; bots must be useful on the **thin** catalog alone
- D11 retunes, phase-11 implications report
- Hardcoding reference-game type names in `src/questline`

## Prerequisites

- FP-G2 ingest + `drain_telemetry` + companion hooks.
- QL-6: game emits thin events in a real combat session (Editor spool or drain).
- Wire v2 (09b) + Tap/hooks path.
- FP-G1 snapshot id for the build under test (import snapshot before the matrix).

## Game trigger

| Framework | Game |
|-----------|------|
| **FP-G3** | Bot suite under `automation/` (policies, locators, hooks). QL-6 must already emit. |

## G2 API cheat-sheet (do not rediscover)

```python
from questline.drivers.port import GameHook
from questline.telemetry import drain_telemetry

driver.call_game_method(GameHook("SetTelemetryContext"), json.dumps({
    "policy_id": "cheapest",
    "seed": "42",
    "config_snapshot_id": snapshot_id,
    "game_version": game_version,
}))
# ... bot loop via hooks / tap ...
drain_telemetry(driver, store, end_outcome="lose", run_id=run_id)
```

Companion hooks: `BeginTelemetrySession`, `SetTelemetryContext`,
`EndTelemetrySession`, `DrainTelemetry`, `TelemetryStatus` (ADR-0010).
Ring overflow → `dropped_count` on the session; treat dropped > 0 as a data-quality
flag, not a pass/fail of the game.

## Acceptance criteria

- [ ] N seeded runs × documented policies × B1–B5 (or a documented subset) write
      `telemetry_sessions` with `policy_id` + `seed` + `config_snapshot_id` set.
- [ ] CI: fake-driver matrix + fixture ingest; no Unity.
- [ ] Live Editor: at least one policy completes a combat loop and a session
      appears in `questline telemetry query` (`pending` if QL-6 missing — then
      this phase does not merge as done).
- [ ] Playability gate recorded: hooks+Tap sufficient **or** 09c scheduled.
- [ ] No AI verdicts. Summaries are measured.
- [ ] STATUS-DUAL + Self-review + `Incidents: …`. HUD: extend **or** explicit defer.

## PR checklist

Title `fp-g3: deterministic bots and measured curves`.
Link QL-6. PowerShell Cómo probarlo (fake + optional Editor).
