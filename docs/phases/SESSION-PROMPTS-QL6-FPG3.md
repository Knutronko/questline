# Session prompts — QL-6 + FP-G3 (after FP-G2)

> Paste one prompt per Cursor chat. Workspaces: ElJuegaso = `D:\Projects\ElJuegaso`,
> questline = `D:\dev\questline`.
> Canonical contracts: questline [`docs/telemetry.md`](../telemetry.md),
> [`adr/ADR-0010-gamelens-telemetry.md`](../adr/ADR-0010-gamelens-telemetry.md),
> [`phases/phase-fp-g2-telemetry.md`](phase-fp-g2-telemetry.md) (QL-6 mapping table),
> [`phases/phase-fp-g3-bots.md`](phase-fp-g3-bots.md).
> Order: **QL-6 (game) → FP-G3 (both)**. Do not start G3 until an Editor combat
> session imports or drains into the store.

**Chats:** **2** (do not merge QL-6 into G3).

| Chat | Workspace | Phase |
|------|-----------|-------|
| 1 | ElJuegaso | QL-6 |
| 2 | questline (+ game `automation/` in the G3 chat as needed) | FP-G3 |

---

## Prompt 1 — ElJuegaso · QL-6

```
Proyecto: ElJuegaso (D:\Projects\ElJuegaso). Fase QL-6 — Mapear P1Debug.Event → QuestlineTelemetry (thin).

Contexto obligatorio (léelo entero; el contrato vive en questline, no lo reinventes):
- D:\dev\questline\docs\telemetry.md
- D:\dev\questline\docs\adr\ADR-0010-gamelens-telemetry.md
- D:\dev\questline\docs\phases\phase-fp-g2-telemetry.md (sección QL-6 mapping)
- D:\dev\questline\unity-package\Runtime\QuestlineTelemetry.cs (API C# a copiar/sync companion)
- integracion-questline.md fila QL-6; debug.md; economias.md KPIs
- INC-0002: sync companion en un PR de juego el mismo día; INC-0008: UTF-8 sin BOM

Alcance QL-6 (thin):
- Sync com.questline.companion desde questline (QuestlineTelemetry + hooks).
- Emitir SOLO el catálogo thin (session start/end, checkpoint, currency in/out, unit.deployed, combat.leak, wave started/completed, skill.cast, repair.applied).
- Llamadas bajo #if UNITY_EDITOR || QUESTLINE_DEV (el asmdef companion ya está gated).
- Checkpoints con labels opacos para KPIs: prep_end, post_3_deploy, mid_w1, mid_w2, between_wave, end (ajusta si el flujo no tiene ese momento; documenta los labels que sí emites).
- currency_id / unit_id / skill_id / tags los elige el juego; no hace falta que coincidan con nombres P1 en questline.
- Dump P1 sigue existiendo. No implementes combat.damage / projectile.* / ranch / buff / relocate / revive (reservados D12/G2+ en telemetry.md).
- Verificar: una sesión Editor → spool en persistentDataPath/questline_telemetry/ → `questline telemetry import` en el store del juego o de questline.
- Actualizar integracion-questline.md + pedir STATUS-DUAL en questline (o PR docs).

Fuera de alcance: FP-G3 bots, 09c, D12, HUD, retunes D11.
Empieza por el plan de mapeo evento-a-evento (tabla debug.md → name) y espera OK.
```

---

## Prompt 2 — questline · FP-G3

```
Proyecto: questline (D:\dev\questline). Fase FP-G3 — Bots deterministas + curvas medidas.

Contexto obligatorio:
- docs/phases/phase-fp-g3-bots.md (léelo entero)
- docs/telemetry.md + ADR-0010 (drain_telemetry, SetTelemetryContext, policy_id/seed/config_snapshot_id)
- docs/BALANCE-AUTOMATION.md §5 (Tap+hooks; 09c solo si gate)
- docs/GAME-INTEGRATION.md §2 (bots en ElJuegaso automation/, no en core)
- Target niveles: IEB B1–B5. QL-6 debe estar emitiendo (si no, pending game QL-6).

Alcance: policies deterministas, matrix N seeds, drain al store, compare summaries.
Fuera: AI policies, 09c salvo gate, eventos ricos D12, HUD salvo defer explícito.
Empieza por el plan de policies + hook gaps y espera OK.
```
