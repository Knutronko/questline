# Session prompts — FP-G4 GameLens balance agent + HUD

> Paste **one prompt per Cursor chat**. Workspace: questline = `D:\dev\questline`.
> Canonical: [`STATUS-DUAL.md`](../STATUS-DUAL.md) §4,
> [`BALANCE-AUTOMATION.md`](../BALANCE-AUTOMATION.md),
> [`phase-fp-g4-balance-agent.md`](phase-fp-g4-balance-agent.md),
> [`hud.md`](../hud.md).
>
> **Do not start numbered phase-12** (triage / diagnose / healer) in this chat.

**Now:** **1 required chat** (questline). D11 feel playtest stays **human**.

| Chat | Workspace | When |
|------|-----------|------|
| **1** | questline | **Start now** — balance agent + HUD |
| — | — | Phase-12 test agents **after** this FP merges |

---

## Prompt 1 — questline · FP-G4 balance agent + HUD (**start this**)

Talk to Pablo in **Spanish**. Docs, PR title/body, and commit messages in English.

```
Project: questline (D:\dev\questline). FP-G4 — GameLens balance agent + HUD.

Talk to Pablo in Spanish. Docs, PR title/body, and commit messages in English.

G1 implications live report is merged. Numbered phase-12 (triage / diagnose / healer)
is PARKED until after this FP. Do not implement those agents. Do not invent a new
numbered phase. This chat is BALANCE-AUTOMATION Immediate next: a GameLens *balance
agent* (retune *priorities*, not SO writes) plus its HUD. Former phase-12b HUD-browse
is folded in.

Read first (do not reinvent):
- docs/STATUS-DUAL.md
- docs/BALANCE-AUTOMATION.md
- docs/phases/phase-fp-g4-balance-agent.md (this brief — follow it)
- docs/hud.md (HUD-first lock: operator acceptance is in questline hud)
- docs/gamelens.md, docs/telemetry.md, docs/ai-setup.md, docs/02-AI-ROADMAP.md
- docs/adr/ADR-0011-llmport-budget.md
- src/questline/lens/report.py, src/questline/hud/
- ElJuegaso path D:\Projects\ElJuegaso is dogfood only — never invent Unity commits

Hard product rules:
- Genre-agnostic core: no P1 type/SO names in src/questline
- AI never invents green/red; measured data owns numbers
- outcome=lose is measured play, not a bot/framework fail
- snap-unset and missing KPIs (combat.damage, FUTURE_EVENT_NAMES) are gaps — never impute
- Store schema: append-only migrations (ADR-0002)
- Prefer Wire; extra questline[ai] stays empty (urllib)
- Secrets: env var NAMES only. Do not paste keys. Mistral live smoke remains deferred
- HUD-first: new operator workflows ship in questline hud in this PR (Playwright +
  TestClient). PowerShell how-to is extra, not the acceptance path.
- Pablo reviews the whole HUD in this phase (existing 08–11 + new GameLens surfaces)

Scope: HUD browse (snapshots, typed diff, implications, telemetry sessions);
thin read-only tool loop over LLMPort for retune priorities; persist agent turns;
fake-LLM tests; Groq/Ollama live in HUD; STATUS-DUAL + hud.md + gamelens.md.

Out of scope: phase-12 triage/diagnose/healer, AI bot policies, writing SOs,
09c, Poco, D12 catalog, auto-applying retunes.

Start with a short plan (HUD routes vs agent tools, persist shape, what Pablo
walks) and wait for OK before coding.
PR title: fp-g4: GameLens balance agent and HUD. Do not merge.
Self-review + Incidents: INC-… or none. Close-out STATUS-DUAL if status changed.
Verified in HUD: required.
```
