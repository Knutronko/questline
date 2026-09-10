# FP-G1 follow-up — GameLens implications live report

> Session preamble: see `phase-00-bootstrap.md`. Read **before coding:**
> [`BALANCE-AUTOMATION.md`](../BALANCE-AUTOMATION.md),
> [`gamelens.md`](../gamelens.md),
> [`ai-setup.md`](../ai-setup.md),
> [`02-AI-ROADMAP.md`](../02-AI-ROADMAP.md) (framing),
> [`adr/ADR-0011-llmport-budget.md`](../adr/ADR-0011-llmport-budget.md),
> [`telemetry.md`](../telemetry.md),
> [`STATUS-DUAL.md`](../STATUS-DUAL.md),
> [`phases/phase-fp-g1-gamelens-snapshot.md`](phase-fp-g1-gamelens-snapshot.md)
> (snapshot/diff already shipped).
>
> **Scheduled:** immediately after **phase-11** merge. Snapshot/diff (FP-G1), thin
> telemetry (FP-G2), and G3 bots are already on main.
> **Size:** S–M. Catalog FP (same rules as numbered phases). Prompts:
> [`SESSION-PROMPTS-G1-IMPLICATIONS.md`](SESSION-PROMPTS-G1-IMPLICATIONS.md).

## Context

Phase-11 shipped LLMPort + a **thin** `build_implications` consumer (`lens diff --ai`).
That call is not yet the **live report** the closed loop needs: join G3
`telemetry_sessions.summary` to a real GameLens snapshot, persist the narrative,
and dogfood it on maintainer data. G3 live cells are all `outcome=lose` with
`config_snapshot_id=snap-unset` — that is **measured**, not a bot fail, and must
stay a **gap** until a snapshot id is attached.

This slice is **judgment labeled *model reasoning***. It is **not** phase-12
(agents), **not** AI bot policies, **not** FP-G4 design copilot.

## Objective

A maintainer can run `questline lens diff` (or a dedicated `lens report`) against
two snapshots **or** one snapshot vs current, get a structured implications
artifact (measured facts + gaps + model-reasoning priorities), using Groq or
Ollama live (Mistral still deferred). CI stays fake-transport.

## In scope

1. **Join keys:** `game_version`, `config_snapshot_id`, `policy_id`, `seed`.
   Sessions with `snap-unset` / missing snapshot → gap, never a silent join.
2. **Measured block only** from `telemetry_sessions.summary` (ADR-0010). Always
   list `combat.damage` (and other `FUTURE_EVENT_NAMES`) as absent until D12
   emits them — **never impute**.
3. **Persist** the implications report (store row and/or
   `artifacts/lens/<id>/implications.json` + optional `.md`). Stdout-only is not
   enough for dogfood.
4. **Prompt** `lens_implications.v1` (or a new versioned file): short bullet
   priorities; English; no green/red; `lose` is play data.
5. **CLI:** keep `--ai` on `lens diff`; add `questline lens report` only if diff
   is the wrong verb. PowerShell how-to in `gamelens.md` + `ai-setup.md`.
6. **Tests:** fake router + fixture sessions (including `snap-unset` and missing
   damage KPI). No live keys in CI.
7. **Live smoke (maintainer):** Groq (`-p ai_groq`) and/or Ollama; write the
   report; confirm gaps mention `snap-unset` and `combat.damage` on current G3
   data. Mistral not required.
8. **Docs close-out:** STATUS-DUAL, BALANCE-AUTOMATION decision-log, `gamelens.md`,
   `03-FUTURE-PHASES.md` G1 AI line. HUD GameLens panel: **extend or explicit
   defer** (BACKLOG already defers the panel — CLI report is the MVP unless you
   ship a tiny run/lens read-only view).

## Out of scope

- Phase-12 tool loop / triage / healer / HUD action buttons
- AI-controlled bot policies (post-G3 add-on)
- FP-G4 RAG copilot / chat
- Inventing Unity commits in ElJuegaso (optional snapshot-id chat is separate)
- D11 retunes, 09c, Poco, D12 event catalog expansion
- Filling gaps with model estimates presented as data

## Game trigger (optional parallel chat)

| Framework | Game |
|-----------|------|
| This FP | Optional: export QL-5 snapshot + `QUESTLINE_SNAPSHOT_ID` on later bot runs so the next matrix can join. Not required to ship the report (current data must show the gap). |

## Acceptance criteria

- [x] CI: implications with fake LLM; `snap-unset` → gap; `combat.damage` in gaps;
      no live keys.
- [x] Report persisted (not stdout-only).
- [x] Maintainer live: Groq **and** Ollama `lens diff` on fixture store 2026-09-10
      (`status: ok`, persist). Groq usable; Ollama `llama3.2` path-ok but weak on gaps.
      Fixture DB has no G3 sessions (`session_count=0` correct). Mistral still deferred.
- [x] Self-review + `Incidents: none`; HUD GameLens **FP-G4** (12b folded; after this PR).
- [x] STATUS-DUAL next-row updated when this lands.

## PR checklist

Title `fp-g1: GameLens implications live report`. English PR. Talk to Pablo in Spanish.

## Self-review

- Persist: `artifacts/lens/<a>__<b>/implications.json` + `.md`; store table
  `lens_implications` via **migration 6** (append-only).
- Join: exact `config_snapshot_id` only in `measured.sessions`. `snap-unset` / NULL
  matching `game_version` → `measured.unjoined` + gap. Never silent `game_version`
  fallback. `FUTURE_EVENT_NAMES` listed as gaps; not imputed.
- CLI: kept `lens diff --ai` (no `lens report`). `--no-ai` does not persist.
- HUD: **not this PR** — operator HUD + agent is **FP-G4** (12b folded).
- Live: Groq + Ollama fixture smoke (see `gamelens.md`). Does not retune ElJuegaso.
- Tests: fake LLM / FakeProvider; no live keys.
- Out of scope held: phase-12 agents, FP-G4, AI bot policies, 09c, Poco, D12,
  ElJuegaso Unity.
- **Incidents: none**
- **Verified in HUD:** n/a (12b)
- **STATUS-DUAL:** next = FP-G4 (this PR was G1); phase-12 parked after G4
