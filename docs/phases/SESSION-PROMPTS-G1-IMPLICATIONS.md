# Session prompts — G1 implications live report (after phase-11)

> Paste **one prompt per Cursor chat**. Workspaces: questline = `D:\dev\questline`,
> ElJuegaso = `D:\Projects\ElJuegaso`.
> Canonical: [`BALANCE-AUTOMATION.md`](../BALANCE-AUTOMATION.md) (Immediate next),
> [`STATUS-DUAL.md`](../STATUS-DUAL.md) §4,
> [`phase-fp-g1-implications-live.md`](phase-fp-g1-implications-live.md).
>
> **Do not start phase-12, FP-G4, or AI bot policies in these chats.**

**Now:** **1 required chat** (questline). **1 optional** (game snapshot id). D11 feel
playtest is **human**, not a Cursor phase.

| Chat | Workspace | When |
|------|-----------|------|
| **1** | questline | **Start now** — implications live report |
| 2 | ElJuegaso | Optional parallel — `QUESTLINE_SNAPSHOT_ID` on later bots |
| — | — | **Do not** open phase-12 until chat 1 has merged (or Pablo says otherwise) |

---

## Prompt 1 — questline · G1 implications live report (**start this**)

Talk to Pablo in **Spanish**. Docs, PR titles/bodies, commits, code comments: **English**.
Do not merge unless Pablo asks.

```
Project: questline (D:\dev\questline). FP-G1 follow-up — GameLens implications live report.

Talk to Pablo in Spanish. Docs, PR title/body, and commit messages in English.

Phase-11 (LLMPort) is merged. Do not invent a numbered phase-12. This chat is the
BALANCE-AUTOMATION "Immediate next": interpret measured G2/G3 data + G1 config diffs
as *model reasoning*. It is not design copilot (FP-G4), not AI bot policies, not
agent triage.

Read first (do not reinvent):
- docs/STATUS-DUAL.md
- docs/BALANCE-AUTOMATION.md (closed loop + Immediate next; do not invert G1→G2→G3→11)
- docs/phases/phase-fp-g1-implications-live.md (this brief — follow it)
- docs/gamelens.md, docs/ai-setup.md, docs/02-AI-ROADMAP.md (framing)
- docs/adr/ADR-0011-llmport-budget.md, docs/telemetry.md, docs/hud.md
- src/questline/lens/report.py (build_implications / collect_measured)
- src/questline/ai/prompts/lens_implications.v1.md
- ElJuegaso path D:\Projects\ElJuegaso is dogfood only — never invent Unity commits there

Hard product rules:
- Genre-agnostic core: no P1 type/SO names in src/questline
- AI never invents green/red; measured data owns numbers
- outcome=lose on G3 cells is measured play, not a bot/framework fail
- config_snapshot_id=snap-unset and missing KPIs (combat.damage, FUTURE_EVENT_NAMES)
  are gaps — never impute
- Store schema: append-only migrations if you need a new table/columns (ADR-0002)
- Prefer Wire; extra questline[ai] stays empty (urllib)
- Secrets: env var NAMES only. Do not paste keys. Mistral live smoke remains deferred

Scope (brief in-scope list): persist implications (store and/or artifacts/lens/...);
join telemetry_sessions.summary on snapshot/version/policy/seed; CLI dogfood
(lens diff --ai and/or lens report); fake-LLM tests; Groq/Ollama live how-to;
STATUS-DUAL + gamelens.md + 03-FUTURE-PHASES G1 AI line; HUD extend OR explicit defer
(GameLens panel is already deferred in BACKLOG — CLI report is enough unless you
add a tiny read-only surface).

Out of scope: phase-12 agents, FP-G4 RAG chat, AI bot policies, 09c, Poco, D12
catalog expansion, D11 retunes, ElJuegaso Unity.

Start with a short plan (persist vs stdout, join behavior on snap-unset, HUD defer
or not) and wait for OK before coding.
PR title: fp-g1: GameLens implications live report. Do not merge.
Self-review + Incidents: INC-… or none. Close-out STATUS-DUAL if status changed.
```

---

## Prompt 2 — ElJuegaso · snapshot id on bot runs (optional, parallel)

ElJuegaso: talk to Pablo in **Spanish**. Docs/PRs/commits in this repo: **Spanish**.
Do not invent design retunes. No Unity feature work unless Pablo explicitly allows
— this is env/docs + export path.

```
Proyecto: ElJuegaso (D:\Projects\ElJuegaso). Seguimiento GameLens — adjuntar snapshot id
a las próximas tandas de bots.

Habla con Pablo en español. Docs, títulos de PR y commits: español (prefijos docs: / proto:).

Contexto: la matrix G3 live (75/75) quedó con config_snapshot_id=snap-unset. El informe
de implicaciones en questline debe poder juntar partidas a un snapshot QL-5. Esta
sesión NO retoca economía ni políticas.

Lee primero:
- docs/prototipos/P1/integracion-questline.md (QL-5 export, QL-6 envelope, §11 bots)
- automation/bots (cómo se lanza la matrix; env vars)
- D:\dev\questline\docs\gamelens.md (Editor export + lens snapshot --import)
- D:\dev\questline\docs\telemetry.md (config_snapshot_id)
- D:\dev\questline\docs\GAME-INTEGRATION.md (no reinventar el contrato)

Alcance:
- Documentar y, si hace falta, cablear QUESTLINE_SNAPSHOT_ID (o el env que ya use el
  envelope QL-6) en la receta de automation/bots
- Receta PowerShell: Unity menu Questline → Export Balance Snapshot →
  questline lens snapshot --import … → copiar el id al env de la siguiente matrix
- Actualizar integracion-questline.md / README de automation si el operador no tiene
  esos pasos. STATUS-DUAL en questline: pedir al chat 1 que lo apunte, o un docs PR
  mínimo en questline — no inventes fases

Fuera de alcance: retunes D11, nuevas políticas, 09c, D12, código Python de questline,
re-correr la matrix 75/75 (Pablo decide cuándo).

Empieza listando qué env/hook ya existe para snapshot id vs qué falta; espera OK.
```

---

## Do not paste yet — later chats

**Phase-12** (AI agents: triage / maintainer / heal) — after implications merge, or
when Pablo wants test-maintenance agents instead of balance narrative. Brief:
[`phase-12-ai-agents.md`](phase-12-ai-agents.md).

**FP-G4** design copilot and **AI bot policies** — after a live implications report
exists and deterministic G3 remains the baseline.
