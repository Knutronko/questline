# Phase 12b — HUD GameLens + telemetry operator surface

> **Superseded 2026-09-10 (maintainer lock):** do **not** start this brief as a
> HUD-only phase. Browse panels + the balance agent ship together as
> **[FP-G4](phase-fp-g4-balance-agent.md)**. Numbered phase-12 (test agents) is
> parked until after G4.
>
> Session preamble: see `phase-00-bootstrap.md`. Read [`hud.md`](../hud.md),
> [`gamelens.md`](../gamelens.md), [`telemetry.md`](../telemetry.md),
> [`BALANCE-AUTOMATION.md`](../BALANCE-AUTOMATION.md),
> [`STATUS-DUAL.md`](../STATUS-DUAL.md) §4.
>
> **Originally scheduled:** after phase-12. **Does not** renumber 13–15.
> Kept for history; follow FP-G4 instead.

## Context

FP-G1 (snapshots, diffs, persisted implications), FP-G2 (telemetry sessions), and
FP-G3 (bot matrix) landed as **CLI + store**. Phase-11 added an AI-cost table on
run detail. Phase-12 adds **agent** HUD buttons (triage / diagnose) on failed
runs — that is **not** this slice.

Operators should not need to remember `questline lens diff` / `questline telemetry`
to read config truth, measured sessions, or *model reasoning*.

## Objective

Read-only HUD panels over the **same** store tables the CLI uses
(`balance_snapshots`, `lens_implications`, `telemetry_sessions`). No second store.
Pablo reviews the full control center for clarity.

## In scope

1. **GameLens panel:** list snapshots; open a typed diff; show persisted
   implications (`status`, `framing`, gaps, *model reasoning* vs *measured*).
   `snap-unset` / `unjoined` / `combat.damage` stay visible gaps — never imputed.
2. **Telemetry panel:** list sessions; show `summary` (outcome, policy, seed,
   snapshot id); `outcome=lose` labeled as measured play, not a framework fail.
3. **Allow-listed APIs** only (same contract as CLI). No secret values, no raw
   home paths in exported reports.
4. **Maintainer UI review (required):** walk runs, launcher, quarantine, profiles,
   perf graphs, AI-cost table, **plus** the new panels. File UX gaps in BACKLOG
   or fix in-phase if small. Self-review: `Verified in HUD: …` (full walk).
5. Docs: `hud.md` + `hud-operator-guide.md` how-to (PowerShell recipes stay for
   CI/scripting).

## Out of scope

- Phase-12 agent kernel / triage / healer (already a numbered phase)
- FP-G4 design-copilot **chat** (“what should I retune?”)
- AI bot policies, writing ScriptableObjects, inventing Unity commits
- 09c, Poco, D12 event catalog, command palette / arbitrary CLI
- Green/red verdicts from the model

## Who does “how to balance”?

| Layer | Phase | Role |
|-------|-------|------|
| Bots + telemetry | G2/G3 | *Measured* numbers |
| Implications report | G1 live report | *Model reasoning* priorities (CLI today; this HUD shows it) |
| Test agents | **12** | Triage / diagnose / heal **tests**, not SO retunes |
| HUD browse | **12b (this)** | See the loop without CLI |
| Design copilot | **FP-G4** (later) | RAG chat that proposes retune focus |
| Human | always | Writes the SO change |

## Acceptance criteria

- [ ] HUD lists snapshots + one typed diff + one persisted implications artifact
      (fixture store is enough in CI; live store optional).
- [ ] HUD lists telemetry sessions; `lose` / `snap-unset` readable as measured/gap.
- [ ] Pablo full-HUD review noted in Self-review (`Verified in HUD: …`).
- [ ] STATUS-DUAL + `hud.md` evolution table updated; CLI recipes remain.

## PR checklist

Title `phase-12b: HUD GameLens and telemetry`. English PR. Talk to Pablo in Spanish.
Do not merge unless Pablo asks.
