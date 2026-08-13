# Session prompts — QL-6 + QL-7 + FP-G3

> Paste one prompt per Cursor chat. Workspaces: ElJuegaso = `D:\Projects\ElJuegaso`,
> questline = `D:\dev\questline`.
> Canonical contracts: questline [`docs/telemetry.md`](../telemetry.md),
> [`adr/ADR-0010-gamelens-telemetry.md`](../adr/ADR-0010-gamelens-telemetry.md),
> [`phases/phase-fp-g2-telemetry.md`](phase-fp-g2-telemetry.md) (QL-6 mapping table),
> [`phases/phase-fp-g3-bots.md`](phase-fp-g3-bots.md),
> ElJuegaso `docs/prototipos/P1/integracion-questline.md` **§10–§11**.
> Order: **QL-6 ✅ (game, 2026-08-13) → QL-7 (game, next) → FP-G3 (questline + `automation/`)**.
>
> **Do not start FP-G3 until QL-7 is merged.** Do not merge QL-7 into the G3 chat.

**Chats:** QL-6 is done. **Two chats left:** QL-7 (game), then FP-G3 (questline).

| Chat | Workspace | Phase |
|------|-----------|-------|
| 1 | ElJuegaso | QL-6 ✅ (2026-08-13) |
| 2 | ElJuegaso | **QL-7 next** — combat hooks |
| 3 | questline (+ game `automation/` only; **no Unity** unless Pablo explicitly allows) | FP-G3 after QL-7 merge |

---

## Prompt 1 — ElJuegaso · QL-6 (done)

Kept for history. Do not re-run.

```
Proyecto: ElJuegaso (D:\Projects\ElJuegaso). Fase QL-6 — Mapear P1Debug.Event → QuestlineTelemetry (thin).
(completed 2026-08-13 — see integracion-questline.md §10)
```

---

## Prompt 2 — ElJuegaso · QL-7 (next chat)

ElJuegaso conventions: human docs and PRs in **Spanish**. Agent instructions / code comments in English.

```
Project: ElJuegaso (D:\Projects\ElJuegaso). Phase QL-7 — Combat hooks so FP-G3 bots can drive IEB with finite amber.

Talk to Pablo in Spanish. Docs, PR title/body, and commit messages in this ElJuegaso chat: Spanish (repo convention: docs: / proto: prefixes).

Read first (do not reinvent):
- docs/implementacion/notas-para-ia.md
- docs/prototipos/P1/integracion-questline.md §11 (locked hook contract + policies — you IMPLEMENT HOOKS ONLY)
- §10.4–10.5 (∞Ám, seed, checkpoints)
- unity/Assets/_Prototipos/P1/Scripts/Debug/P1TestHooks.cs
- unity/Assets/_Prototipos/P1/Scripts/Debug/P1QuestlineBootstrap.cs (LoadIeb currently hardcodes infiniteAmber: true)
- CombatSession TryDeployCollector / TryDeployDino / Amber.Gain pickup path
- D:\dev\questline\docs\GAME-INTEGRATION.md (questline agents must not commit Unity; this chat is the game side)
- D:\dev\questline\docs\STATUS-DUAL.md (update if status changes; same PR if questline is checked out, else a small questline docs PR)

Scope QL-7 (game Unity + Spanish docs):
- P1TestHooks + QuestlineHooks registration for the table in §11.2:
  LoadIeb with infiniteAmber selectable (bots default false — STOP hardcoding true in Wire),
  SetInfiniteAmber, DeployAt JSON, CollectPickups, BoardState JSON, CastSkill JSON,
  RelocateAt JSON, plus register existing TryRepair / SkipBuffDraft / TryPickBuff /
  GetCombatPhase / GetEnded / GetWon / GetLiveEnemyCount / GetFossilLane / GetFossilDepth / GetBuffPickCost / GetRepairCooldown if missing from Wire.
- Multi-arg hooks: one JSON string (Register<string>). Do not add Register<T1,T2,T3> to the companion unless JSON is impossible.
- DeployAt must respect empty cell, amber cost, fighter slots. typeId 0 = collector. Internal tap path, not Drag.
- CollectPickups: all live AmberPickup, same Amber.Gain path as a world tap.
- BoardState: JSON fields listed in §11.2 — enough for balanced if/then. No new telemetry events. No enemy.spawn in the thin catalog.
- P1Debug.Event already covers deploy/gain; do not invent a parallel debug catalog.
- Update tools-editor.md with the new hook names. Update notas-para-ia / STATUS-DUAL when QL-7 lands.
- Verify: Editor Play + Wire: LoadIeb finite → DeployAt collector adjacent to fossil → CollectPickups raises amber → BoardState parses → GetEnded/GetWon after a short fight (cheat KillAllEnemies OK for smoke).

Out of scope: Python policies, automation/ matrix, drain_telemetry, 09c, D12 events, D11 retunes, AI, FP-G3.

Start with a short implementation plan (hook signatures vs CombatSession methods) and wait for OK before coding.
PR to main when done (Qué / Por qué / Cómo probarlo / Docs / Issue).
```

---

## Prompt 3 — questline · FP-G3 (after QL-7 merge)

Workspace: questline. Docs, PRs, commit messages: **English**. Speak to Pablo in **Spanish**.

```
Project: questline (D:\dev\questline). Phase FP-G3 — Deterministic bots and measured difficulty curves.

Language: when you address Pablo, use Spanish. All docs, PR titles/bodies, commit messages, and code comments in this questline chat: English.

Do NOT start until ElJuegaso QL-7 is merged on main (DeployAt, CollectPickups, BoardState, CastSkill, RelocateAt, finite LoadIeb). If QL-7 is missing, stop and say so.

Read first (do not reinvent):
- docs/phases/phase-fp-g3-bots.md (entire brief)
- docs/telemetry.md + ADR-0010 (drain_telemetry, SetTelemetryContext)
- docs/BALANCE-AUTOMATION.md §5–§8
- docs/GAME-INTEGRATION.md §2 (bots live in ElJuegaso automation/, NOT src/questline)
- docs/STATUS-DUAL.md
- ElJuegaso docs/prototipos/P1/integracion-questline.md §11 (LOCKED policies + kernel) and §10.4–10.5 (checkpoints, seed, finite amber, leak ≠ spawn)

Locked design (do not reopen):
- Shared kernel: finite amber, SetSeed + SetTelemetryContext, collector first adjacent to fossil ASAP, CollectPickups every tick if pickups exist, hooks not Drag.
- policy_id catalog v1: balanced, cheapest, rush, never_skill, always_skill — rules in game §11.4. balanced = if/then on BoardState, not an LLM.
- Buff between waves: per policy (table in §11.4). Repair: off in v1.
- Matrix DoD: IEB B1–B5 × 5 policies × N=3 seeds. PRs may be incremental (fake-driver + one-policy smoke → Editor one cell → full matrix) but the phase is not done until the full matrix writes sessions.
- Measured KPIs = thin summaries only. Do not invent spawn/KO/DPS/mid_w* KPIs. Do not add enemy.spawn telemetry.
- Type names (Dientes, amber, ieb-N) stay in automation/, never hardcoded in src/questline.

Scope:
- Deterministic policies + matrix runner in ElJuegaso automation/ (you MAY edit automation/ in that repo; you may NOT edit Unity/gameplay unless Pablo explicitly allows it in this chat — default no).
- Fake-driver unit tests in questline and/or automation CI (no Unity in CI).
- drain_telemetry after each run; policy_id + seed + config_snapshot_id set.
- Playability gate: hooks sufficient or STOP and schedule 09c (no Point-spam).
- Update STATUS-DUAL, BALANCE-AUTOMATION decision log, telemetry.md consumer note. HUD: explicit defer unless summaries are worth a small panel.

Out of scope: AI/LLM policies, 09c unless gate fails, D12 events, D11 retunes, phase-11, companion API churn.

Start with a plan (package layout in automation/, tick loop, how BoardState drives balanced) and wait for OK.
PR title like: fp-g3: deterministic bots and measured curves
```
