# FP-G1 — GameLens: balance snapshot, diff & (deferred) AI implications

> Session preamble: see `phase-00-bootstrap.md`. Read **before coding:**
> [`BALANCE-AUTOMATION.md`](../BALANCE-AUTOMATION.md),
> [`03-FUTURE-PHASES.md`](../03-FUTURE-PHASES.md) Group G,
> [`GAME-INTEGRATION.md`](../GAME-INTEGRATION.md) §5,
> [`FEATURE-PIPELINE-PLAN.md`](../FEATURE-PIPELINE-PLAN.md) §5.6,
> [`STATUS-DUAL.md`](../STATUS-DUAL.md),
> [`02-AI-ROADMAP.md`](../02-AI-ROADMAP.md) (framing rules).
>
> **Scheduled:** immediately with game **D11** + **QL-5** (joint wave).
> **Size:** M. This is a catalog FP given a full brief (same rules as numbered phases).

## Context

Phases 00–10 are merged (Wire v2 UI ✅). The reference game is entering **D11**
(economy mid/late). Maintainer intent: automate playtest-driven balance via GameLens.
**FP-G1** is the **config truth** layer (what changed in SOs). Measured playthroughs
are **FP-G2/G3** and come **right after** this wave — see BALANCE-AUTOMATION §4.
**Do not** wait for phase-11 to ship snapshot/diff.

## Objective

Ship a genre-agnostic **balance snapshot + typed diff** pipeline driven by a
**game-declared manifest** (QL-5), with CLI + store persistence. AI implications
report is **in scope as a stub / deferred acceptance** until phase-11 LLMPort exists.

## In scope

1. **Manifest contract** (companion + docs): game marks which ScriptableObjects are
   balance data (attribute and/or manifest asset). Questline core never hardcodes
   ElJuegaso type names. Align schema with game **QL-5** chat before merge.
2. **Extractor** (Editor / `QUESTLINE_DEV`): serialize designated SOs → normalized
   `balance_snapshot.json` (stable key paths, numeric/string/curve shapes documented).
3. **Snapshot store**: keyed by game version and/or git commit (+ optional feature_id);
   fits existing run/store patterns; artifact on disk + DB row as appropriate.
4. **CLI:** `questline lens snapshot` (capture/import) and `questline lens diff <vA> <vB>`
   (human-readable + machine JSON).
5. **Diff engine:** typed entries — numeric Δ + %, added/removed **entities** as
   first-class (FEATURE-PIPELINE §5.6), curve/series changes; group by manifest
   **system** tags (economy, creatures, waves, …).
6. **Supplementary context (read-only):** optional Markdown/CSV from game repo paths
   for later AI — **not** numerically diffed.
7. **AI implications (deferred gate):** interface + prompt stub that consumes
   diff (+ optional design docs). If phase-11 is absent: skip live LLM; document
   `pending phase-11`. Framing: output labeled *model reasoning* only.
8. **Tests:** fixtures (fake SO JSON / companion fake) in CI — no live Unity required
   for Python diff tests; companion editor path documented for maintainer.
9. **Docs:** update BALANCE-AUTOMATION / STATUS-DUAL / GAME-INTEGRATION / wire or
   companion notes; HUD panel **minimal or explicitly deferred** (graphs can follow).
10. **ADR** if schema or store layout needs a durable decision (short ADR ok).

## Out of scope

- Game economy design (**D11**) or writing the game’s SO list (**QL-5** owns manifest
  *contents*; this phase owns *format + exporter*)
- Telemetry ingestion (**FP-G2**), bot playthroughs (**FP-G3**)
- phase-11 providers (unless already merged — then wire the deferred report)
- Hardcoding P1 unit/skill names in `src/questline`
- FP-F feature pipeline beyond accepting optional `feature_id` on snapshots

## Prerequisites

- Companion package + Wire path exist (phases 4 / 05b / 09b).
- Game QL-5 in flight or completed for a real dogfood manifest (CI uses fixtures).
- **Not** required: phase-11, FP-G2, FP-G3.

## Game trigger

| Framework | Game |
|-----------|------|
| **FP-G1** | **QL-5** — balance SO manifest + sync companion exporter |

## Acceptance criteria

- [x] CI: snapshot normalize + diff unit tests (including **new entity** diffs); CLI
      smoke on fixtures.
- [x] Manifest schema documented; unknown SO / missing file → clear errors.
- [x] `questline lens snapshot` / `diff` work against fixture pack without Unity.
- [x] Maintainer path: export from Editor with a sample manifest (reference game or
      mini fixture scene) documented in PowerShell.
- [x] AI report: either live via LLMPort **or** explicit deferred checklist item + stub.
- [x] STATUS-DUAL + BALANCE-AUTOMATION date/order unchanged unless this PR advances them.
- [x] Self-review + `Incidents: …` in PR; no secrets in snapshots.

## PR checklist

Title `fp-g1: GameLens snapshot and diff`.
Self-review required. Link QL-5 / D11 PRs if concurrent.
PowerShell Cómo probarlo (fixture + optional Editor export).

## Lessons / incidents

- Shipped snapshot/diff without waiting for QL-5 contents or phase-11 LLMPort; CI uses
  generic fixture packs (`tests/fixtures/lens/`).
- Manifest schema locked in ADR-0009; QL-5 must match `schema_version: 1` +
  `asset_path` (Editor) / `source_file` (Python pack).
- **Incidents:** none.
