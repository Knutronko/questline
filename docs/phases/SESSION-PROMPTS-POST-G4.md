# Session prompts — after FP-G4 (phase-12 + parallel ElJuegaso)

> Paste **one prompt per Cursor chat**. Merge the G4 close-out docs PR first so
> `STATUS-DUAL.md` says G4 is merged and phase-12 is unparked.
>
> Canonical: [`STATUS-DUAL.md`](../STATUS-DUAL.md) §4,
> [`BALANCE-AUTOMATION.md`](../BALANCE-AUTOMATION.md),
> [`phase-12-ai-agents.md`](phase-12-ai-agents.md),
> [`hud.md`](../hud.md).

**Now (after docs close-out merges):**

| Chat | Workspace | Parallel? |
|------|-----------|-----------|
| **1** | questline | **Start this** — numbered **phase-12** test agents |
| **2** | ElJuegaso | **Parallel, human** — D11 feel playtest (not a coding phase) |
| **3** | ElJuegaso | **Parallel, small code** — optional `QUESTLINE_SNAPSHOT_ID` on later bots |
| **4** | ElJuegaso | **Optional parallel** — **QL-8** Unity CLI + Pipeline + `unity mcp` dogfood |

**Do not start in these chats:** Wire **09c** (parked), **phase-13** (needs 12),
**phase-14 / QL-4 Poco**, **D12** (after D11 feel; richer `FUTURE_EVENT_NAMES` later),
**FP-U1 / FP-U2** (after 12; live needs QL-8).
Do not re-build the GameLens balance agent (FP-G4, done).
QL-8 prompts: [`SESSION-PROMPTS-UNITY-CLI.md`](SESSION-PROMPTS-UNITY-CLI.md).

---

## Prompt 1 — questline · phase-12 AI agents (**start this**)

Talk to Pablo in **Spanish**. Docs, PR title/body, and commit messages in English.

```
Project: questline (D:\dev\questline). Phase-12 — AI agents: kernel, triage, maintainer, self-healing locators.

Talk to Pablo in Spanish. Docs, PR title/body, and commit messages in English.

FP-G4 is MERGED (PR #36). GameLens balance agent + HUD browse already exist
(questline.lens.agent, #/lens). Do NOT reimplement retune-copilot, SO writes, or
GameLens Ask. This phase is TEST agents (failing pytest), not balance.

Read first (do not reinvent):
- docs/STATUS-DUAL.md
- docs/02-AI-ROADMAP.md §2–3
- docs/phases/phase-12-ai-agents.md (this brief — follow it)
- docs/hud.md + docs/hud-user-guide.md (HUD-first: operator actions ship in questline hud)
- docs/ai-setup.md, docs/adr/ADR-0011-llmport-budget.md
- src/questline/ai/ (LLMPort, router, FakeProvider tool_calls — G4 already uses a thin loop)
- ElJuegaso path D:\Projects\ElJuegaso is dogfood only — never invent Unity commits

Hard product rules:
- Genre-agnostic core: no P1 type/SO names in src/questline
- AI never invents green/red; the anti-false-green gate re-runs the test; agent claims are ignored
- Store schema: append-only migrations (ADR-0002)
- Prefer Wire for live Unity; extra questline[ai] stays empty (urllib)
- Secrets: env var NAMES only. Do not paste keys. Mistral live smoke remains deferred
- HUD-first: "Triage this run" / "Diagnose this test" in the same PR (API + SPA + Playwright).
  PowerShell how-to is extra.
- Import-linter: HUD must not import questline.ai.factory / cursor_cli (same isolation as G4)

Scope: agent kernel (allow-listed tools, per-task turn budget, incremental persist,
hermetic read-only); triage (read-only digest); maintainer (diagnose default, fix opt-in,
anti-false-green); healer (suggest locators.yaml only, never write); HUD hooks; docs/ai-agents.md.

Out of scope: phase-13 generators/eval, GameLens retune, AI bot policies, 09c, Poco, D12,
auto-PRs, writing ScriptableObjects.

Start with a short plan (kernel vs G4 lens.agent reuse, HUD buttons, persist shape) and
wait for OK before coding.
PR title: phase-12: ai agents. Do not merge unless Pablo asks.
Self-review + Incidents: INC-… or none. Close-out STATUS-DUAL if status changed.
Verified in HUD: required.
```

---

## Prompt 2 — ElJuegaso · D11 feel playtest (**parallel, human**)

This is **not** a coding session. Workspace if you take notes: `D:\Projects\ElJuegaso`.
Talk to Pablo in Spanish. Any committed notes in the **game** repo only if Pablo asks;
questline agents must not invent ElJuegaso commits.

```
Human playtest — ElJuegaso P1 D11 feel (B1–B5). Not a Questline code phase.

Canonical: questline docs/STATUS-DUAL.md §3–4, BALANCE-AUTOMATION.md.
Game: D:\Projects\ElJuegaso (not C:\Users\Pablo\Projects\ElJuegaso).

What to do:
- Play IEB Pass B presets B1–B5 yourself (feel, not bots).
- G3 live matrix was 75/75 passed with outcome=lose — that is measured play for retune,
  not a bot/framework fail. Do not “fix” bots to force wins.
- Note economy mid/late, amber starvation, pressure — for a later human SO retune.
- Do not start D12, Poco/QL-4, or Wire 09c from this chat.
- Do not ask an agent to invent Unity commits.

Optional after play: jot feel notes in the game docs Pablo names. No questline PR.
```

---

## Prompt 3 — ElJuegaso · optional snapshot id on later bots (**parallel, small**)

Talk to Pablo in **Spanish**. Docs/PR/commits in English. Workspace: `D:\Projects\ElJuegaso`.

```
Project: ElJuegaso (D:\Projects\ElJuegaso). Optional follow-up after FP-G3 live:
attach QUESTLINE_SNAPSHOT_ID on later bot runs so GameLens can join
telemetry_sessions to a balance snapshot.

Talk to Pablo in Spanish. Docs, PR title/body, and commit messages in English.

Read first:
- questline docs/STATUS-DUAL.md, docs/gamelens.md, docs/telemetry.md, docs/GAME-INTEGRATION.md
- game integracion-questline.md § telemetry / bots
- Live G3 used config_snapshot_id=snap-unset (join gap). Do not silently join on game_version.

Scope: wire bot/CI launch so later matrix runs set QUESTLINE_SNAPSHOT_ID to a real
imported snapshot id when the operator has one. Keep snap-unset when unset.
Do not invent KPIs, do not add enemy.spawn for bots, do not start D12 catalog,
do not Point-spam, do not enable 09c.

Out of scope: questline phase-12, retune SOs, changing G3 policies.

Start with a short plan (where env is read, how HUD/lens will join) and wait for OK.
Do not merge unless Pablo asks.
```

---

## Prompt 4 — ElJuegaso · QL-8 Unity CLI dogfood (optional parallel)

Full prompt lives in [`SESSION-PROMPTS-UNITY-CLI.md`](SESSION-PROMPTS-UNITY-CLI.md)
(QL-8 block). Workspace: `D:\Projects\ElJuegaso`. Does **not** replace Wire.
Do not start FP-U1/U2 from that chat.
