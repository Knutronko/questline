# FP-G3 — Deterministic bots & measured difficulty curves

> Session preamble: see `phase-00-bootstrap.md`. Read **before coding:**
> [`BALANCE-AUTOMATION.md`](../BALANCE-AUTOMATION.md) (order G1 → **G2 → G3** → 11),
> [`telemetry.md`](../telemetry.md) + [`adr/ADR-0010-gamelens-telemetry.md`](../adr/ADR-0010-gamelens-telemetry.md),
> [`gamelens.md`](../gamelens.md) (attach `config_snapshot_id`),
> [`GAME-INTEGRATION.md`](../GAME-INTEGRATION.md) §4–§5,
> [`wire-setup.md`](../wire-setup.md), [`phase-09c`](phase-09c-wire-play-gestures.md) (parked),
> [`STATUS-DUAL.md`](../STATUS-DUAL.md).
>
> **Scheduled:** after FP-G2 ✅, game **QL-6 ✅**, and game **QL-7 ✅** (combat hooks).
> **Size:** L. Policies + hook contract: ElJuegaso `integracion-questline.md` **§11**.
> Mapping / labels / gaps: same doc **§10.4–10.5**. **Do not start this phase until QL-7 is merged.**
>
> **Does not wait on** phase-11, phase-13, or 09c (09c only if the playability gate fails).

## Context

FP-G1 is config truth; FP-G2 is measured truth (store + drain). This phase **exercises**
the game with deterministic policies so summaries become comparable curves
(version × policy × seed × snapshot).

Reference-game target levels: **IEB Pass B presets B1–B5**. Policy catalog is **locked**
in the game doc §11 (not reinvented here). Bots live in the **game** `automation/` suite
(GAME-INTEGRATION §2), not in questline core.

## Objective

Run N seeded sessions per (game_version, policy_id, snapshot) via Wire + hooks
(Tap deploy), drain telemetry into the store, and produce measured overlays
(summary diffs / curves from thin events + checkpoints). AI policies are **out**.

## In scope

1. **Policies (deterministic, locked):** implement the catalog in game §11 — shared
   kernel (collector-first, finite amber, collect pickups) plus `balanced`, `cheapest`,
   `rush`, `never_skill`, `always_skill`. `balanced` is **if/then on `BoardState`**, not
   an LLM. Do **not** invent extra `policy_id`s in v1. Names are stored on the session.
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
3. **N repeats** per cell. Locked: **N = 3**. DoD = **full** matrix B1–B5 × 5 policies × N
   seeds. PRs may land incrementally (fake-driver + one-policy smoke → Editor one cell →
   full matrix) but the phase is not done until the full matrix writes sessions.
4. **Measured outputs:** use stored summaries (`deploy_count`, currency net,
   `time_to_first_leak`, waves, checkpoint labels). Do **not** invent KPIs in
   Python that the events cannot support. Amber-at-moment curves use QL-6
   labels the game **actually emits:** `post_3_deploy`, `between_wave`,
   `prep_end` (between-wave prep only), `end`. **Do not** expect `mid_w1` /
   `mid_w2` (no such moment in the combat flow). `combat.leak` is base-reach,
   not spawn count. Ally KO / `enemy.spawn` are D12.
5. **Compare:** `questline telemetry query <idA> --compare <idB>` and/or a small
   report (text/JSON) grouping by policy × version. Full HUD overlay is deferred
   with G2 HUD.
6. **Playability gate:** hooks + Tap first. If Drag/gestures are required on the
   measured path, **stop and schedule 09c** (do not silently Point-spam).
7. Combat hooks (`DeployAt`, `CollectPickups`, `BoardState`, `CastSkill`, `RelocateAt`,
   finite `LoadIeb`) are **QL-7** (game). This phase **consumes** them; do not reimplement
   in `src/questline` and do not edit Unity unless the maintainer explicitly allows it
   (default: **no** — QL-7 is a separate ElJuegaso chat). Document hook names only in
   `automation/`.
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
- QL-6 ✅: game emits thin events (Editor spool imported). **Bots must**
  `SetSeed` + `SetTelemetryContext.seed` — IEB start does not call
  `P1Rng.ApplyLevelDefaultSeed`. Play **finite amber** (`LoadIeb` `infiniteAmber: false`).
- **QL-7 ✅:** combat hooks in game §11.2. **Hard gate** — without them this phase
  cannot measure sinks or run `balanced`.
- Wire v2 (09b) + Tap/hooks path.
- FP-G1 snapshot id for the build under test (import snapshot before the matrix).

## Game trigger

| Framework | Game |
|-----------|------|
| **FP-G3** | Bot suite under `automation/` (policies §11, locators, hooks). **QL-7 must already exist.** |

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

- [ ] N=3 seeded runs × 5 policies × B1–B5 write
      `telemetry_sessions` with `policy_id` + `seed` + `config_snapshot_id` set.
      (Fake matrix ✅ in `automation/tests`. Live `@pytest.mark.g3_matrix` maintainer.)
- [x] CI: fake-driver matrix + fixture ingest; no Unity.
- [ ] Live Editor: at least one policy completes a combat loop and a session
      appears in `questline telemetry query` (maintainer-checked; `suites/test_g3_cheapest.py`).
- [x] Playability gate recorded: hooks+Tap sufficient (**09c parked**).
- [x] No AI verdicts. Summaries are measured.
- [x] STATUS-DUAL + Self-review + `Incidents: none`. HUD: **explicit defer**.

## PR checklist

Title `fp-g3: deterministic bots and measured curves`.
Link QL-7 ([ElJuegaso #47](https://github.com/Knutronko/ElJuegaso/pull/47)) and QL-6.
PowerShell how-to-test (fake + optional Editor). Docs/PRs/commits in **English**.

## Self-review

- Fake CI: `cd D:\Projects\ElJuegaso\automation` → `uv run --no-sync pytest tests -q -o addopts=` (19 passed).
- Live: `QUESTLINE_LIVE_TARGET=1` + `suites/test_g3_smoke.py` then `test_g3_cheapest.py`;
  full matrix `-m g3_matrix`. Optional `QUESTLINE_SNAPSHOT_ID`.
- `Verified in HUD: n/a (telemetry view deferred)`.
- **Incidents: INC-0009**.
- JSON hook args are Python strings (`json.dumps`); companion `ParseArgsArray` is scalars-only.

## Lessons / incidents

- `SetTelemetryContext` must run **after** `LoadIeb` / combat `BeginSession` or the game
  wipes `policy_id`. Buff v1 is `SkipBuffDraft` (no offer list on `BoardState`).
- Live `uv run pytest` from ElJuegaso `automation/` rebuilds the questline git pin;
  hatch `force-include` of HUD static duplicated `index.html` in the wheel
  ([INC-0009](../incidents/INC-0009-hatch-hud-static-duplicate.md)). Use
  `uv pip install -e D:\dev\questline` then `uv run --no-sync pytest …`.
- Live cheapest treated Support as lane cover (cost 65 < Cuello 75). Lock: Support/Trampero
  do not cover; Support deploys behind Armadura or a damaged cover ally.
- **Incidents:** INC-0009 (this PR).
