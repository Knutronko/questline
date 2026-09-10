# FP-G4 — GameLens balance agent + HUD

> Session preamble: see `phase-00-bootstrap.md`. Read **before coding:**
> [`STATUS-DUAL.md`](../STATUS-DUAL.md),
> [`BALANCE-AUTOMATION.md`](../BALANCE-AUTOMATION.md),
> [`gamelens.md`](../gamelens.md),
> [`telemetry.md`](../telemetry.md),
> [`hud.md`](../hud.md) (HUD-first lock),
> [`ai-setup.md`](../ai-setup.md),
> [`02-AI-ROADMAP.md`](../02-AI-ROADMAP.md),
> [`adr/ADR-0011-llmport-budget.md`](../adr/ADR-0011-llmport-budget.md),
> G1 live report [`phase-fp-g1-implications-live.md`](phase-fp-g1-implications-live.md).
>
> **Scheduled:** immediately after G1 implications live report (PR #34). **Before**
> numbered **phase-12** (triage / diagnose / healer — parked).
> **Size:** M. Catalog FP (does not renumber 12–15). Prompts:
> [`SESSION-PROMPTS-G4-BALANCE-AGENT.md`](SESSION-PROMPTS-G4-BALANCE-AGENT.md).
>
> **Maintainer lock (2026-09-10):** this is the “agente que balancea” + its UI.
> Operator acceptance is **in the HUD**, not PowerShell-only. Pablo reviews the
> **whole** control center (08–11 surfaces **and** the new GameLens panels).

## Context

Config truth (G1), measured sessions (G2/G3), and a persisted *model reasoning*
implications report already exist as CLI + store. Operators still need a **HUD**
to browse that loop and an **agent** that, given a diff + measured summaries,
proposes **retune focus** (priorities, not SO writes).

This is **not** phase-12. Phase-12 remains the test-agent kernel (triage /
maintainer / healer) and stays **parked** until after this FP.

Former **phase-12b** (HUD browse only) is **folded here** so we do not ship a
CLI-only agent and a HUD-only slice in two chats.

## Objective

A maintainer can open `questline hud`, browse snapshots / typed diffs / telemetry
sessions / implications, ask the GameLens agent what to look at for a retune, and
see labeled *model reasoning* next to *measured* numbers — without memorizing CLI.

## In scope

1. **HUD GameLens + telemetry (read-only browse):** list snapshots; typed diff;
   persisted implications; telemetry sessions (`outcome=lose` = measured play;
   `snap-unset` / `unjoined` / `combat.damage` stay gaps). Same store tables as
   CLI. Allow-listed APIs; no secrets.
2. **Balance agent (thin tool loop over LLMPort):** allow-listed **read** tools
   only (snapshots, diffs, `telemetry_sessions.summary`, `lens_implications`).
   Output = structured *model reasoning* priorities (English bullets). Persist
   the turn (store + artifact). Never write ScriptableObjects, never impute KPIs,
   never issue green/red / ship-no-ship.
3. **HUD agent surface:** ask/run the agent from the GameLens panel; show the
   reply + gaps + measured citations; cost row via existing `ai_calls`.
4. **Thin kernel for this agent only.** Do **not** implement phase-12 triage /
   maintainer / healer / `run_test` / patch tools. A later phase-12 may generalize
   the loop; do not block G4 on that refactor.
5. **Tests:** fake LLM + fake tools; `snap-unset` / missing `combat.damage` stay
   gaps; HUD API + Playwright for the new flows. No live keys in CI.
6. **Live (maintainer):** Groq (`-p ai_groq`) and/or Ollama in HUD. Mistral
   deferred. Prefer Groq for readable reasoning (`llama3.2` is path-ok but weak).
7. **Pablo HUD review (required):** walk runs, launcher, quarantine, profiles,
   perf, AI-cost, **plus** GameLens browse + agent. Self-review:
   `Verified in HUD: …`.
8. Docs: `hud.md`, `hud-operator-guide.md`, `gamelens.md`, `ai-setup.md`,
   STATUS-DUAL, BALANCE-AUTOMATION decision-log.

## Out of scope

- Numbered **phase-12**: triage / diagnose / healer / anti-false-green test fixes
- Writing Unity / ScriptableObjects / inventing ElJuegaso commits
- AI-controlled **bot policies** (still a later add-on vs deterministic G3)
- Auto-applying retunes; presenting model estimates as *measured*
- 09c, Poco, D12 catalog expansion, command palette
- Full RAG over Markdown design docs (nice-to-have if cheap; not a blocker)

## Who does what

| Layer | Owner | Role |
|-------|-------|------|
| Bots + telemetry | G2/G3 (done) | *Measured* |
| Implications report | G1 live (done) | Batch *model reasoning* on `lens diff --ai` |
| Balance agent + HUD | **this FP** | Interactive priorities + browse in HUD |
| Test agents | **phase-12** (later) | Failing tests, not SOs |
| Human | always | Writes the SO retune |

## Acceptance criteria

- [x] HUD: snapshots, one typed diff, one implications artifact, telemetry list
      (fixture store in CI; live store optional).
- [x] Agent: fake-LLM tool loop; gaps include `snap-unset` / `combat.damage`;
      persist; no live keys in CI.
- [ ] Maintainer: Groq (and/or Ollama) from **HUD**; numbers match store summaries.
- [ ] Pablo full-HUD review in Self-review (`Verified in HUD: …`).
- [x] STATUS-DUAL next-row = phase-12 (parked agents) or whatever Pablo locks.
- [x] Self-review + `Incidents: …` or `none`.

## PR checklist

Title `fp-g4: GameLens balance agent and HUD`. English PR. Talk to Pablo in Spanish.
Do not merge unless Pablo asks.

## Self-review

- HUD browse: snapshots, typed diff, persisted implications, telemetry sessions
  (`lose` = measured play; `snap-unset` / `combat.damage` stay gaps).
- Agent: allow-listed read tools only; persist `lens_agent_turns` (migration 7);
  fake-LLM CI; HUD Ask uses injected fake in smoke, Groq/Ollama from live profiles.
- HUD does not import `questline.ai.factory` (cursor_cli isolation).
- **Verified in HUD:** Playwright smoke (runs/test/AI-calls, launch→live→stop, perf
  compare, GameLens snapshots→diff→gaps→Ask, telemetry `lose`/`snap-unset`) +
  TestClient APIs. Maintainer live Groq/Ollama Ask on a real store = Pablo on this PR.
- **Incidents:** none

