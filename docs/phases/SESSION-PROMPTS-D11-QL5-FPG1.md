# Session prompts — joint wave D11 + QL-5 + FP-G1

> Paste one prompt per Cursor chat. Workspaces: ElJuegaso = `D:\Projects\ElJuegaso`,
> questline = `D:\dev\questline`. Read [`BALANCE-AUTOMATION.md`](../BALANCE-AUTOMATION.md)
> for the closed-loop order (bots + telemetry **before** phase-11 AI).

**Chats:** exactly **3** (do not merge D11 with QL-5).

| Chat | Workspace | Phase |
|------|-----------|-------|
| 1 | ElJuegaso | D11 |
| 2 | ElJuegaso | QL-5 |
| 3 | questline | FP-G1 |

After this wave: schedule **FP-G2 + QL-6**, then **FP-G3** bots targeting **B1–B5**
(IEB Pass B; policies TBD), **then** phase-11 AI (serial). 09c only if Wire gate fails.

---

## Prompt 1 — ElJuegaso · D11

```
Proyecto: ElJuegaso (D:\Projects\ElJuegaso). Fase D11 — Economía mid/late + knobs medibles.

Contexto obligatorio (léelo entero antes de planificar):
- En questline: docs/BALANCE-AUTOMATION.md (bucle GameLens; bots+telemetría ANTES de phase-11)
- docs/prototipos/P1/plan-fase-d.md (D11), economias.md, diseno-d10-5-balance-ieb.md (§ Calibración)
- roadmap-post-d6.md, integracion-questline.md (D11 adopta GameLens; TODO balance en SO)
- STATUS-DUAL en questline

Alcance D11:
- Mid/late ámbar: sinks, pacing, boost entre oleadas si procede, W2+ density con datos
- Documentar KPIs de feel que mediremos luego con FP-G2/G3 (ámbar curves, time-to-deploy, leaks…)
- TODOS los knobs nuevos/cambiados en ScriptableObjects / P1Defaults — cero magic numbers
- Mantener testabilidad: hooks/getters si hay mecánica nueva; P1Debug.Event en flujos nuevos
- Actualizar docs + decisiones + STATUS-DUAL (vía PR questline o pedir al chat FP-G1) al cerrar

Fuera de alcance: QL-5 manifest, FP-G1 código, telemetría QL-6, bots FP-G3, phase-11, D12.
Chats paralelos: QL-5 (mismo repo) y FP-G1 (questline). Si creas SOs nuevos, nómbralos para QL-5.
Empieza con plan corto de entregables + criterios Hecho (código vs playtest humano) y espera OK.
```

---

## Prompt 2 — ElJuegaso · QL-5

```
Proyecto: ElJuegaso (D:\Projects\ElJuegaso). Sesión QL-5 — Manifest de SOs de balance (GameLens FP-G1).

Contexto obligatorio:
- questline docs/BALANCE-AUTOMATION.md
- docs/prototipos/P1/integracion-questline.md (fila QL-5)
- guia-agentes-p1.md (todo balance en SO)
- questline: GAME-INTEGRATION.md §5, phases/phase-fp-g1-gamelens-snapshot.md, STATUS-DUAL.md

Alcance QL-5:
- Manifest de export: lista de SOs que SON balance (CombatBalance, GridConfig, WaveBuffConfig,
  LevelConfig, UnitStats, Economy, MetaTimers, Skills, + lo que D11 añada) + system tags
- Contrato con companion/FP-G1 (atributo o asset); el juego declara QUÉ; el fw serializa CÓMO
- No retunes de economía; no telemetría QL-6; no bots
- Docs + sync companion si el contrato lo exige; alinear schema con chat FP-G1 antes de merge

Fuera de alcance: D11 diseño, FP-G1 Python/CLI (salvo schema compartido), phase-11.
Empieza listando SOs candidatos en el repo + propuesta de formato de manifest; espera OK.
```

---

## Prompt 3 — questline · FP-G1

```
Proyecto: questline (D:\dev\questline). Fase FP-G1 — GameLens snapshot + diff (AI report deferred).

Contexto obligatorio:
- docs/BALANCE-AUTOMATION.md (orden: G1 → G2 → G3 bots → phase-11; NO invertir)
- docs/phases/phase-fp-g1-gamelens-snapshot.md (brief canónico — síguelo)
- docs/03-FUTURE-PHASES.md Group G, GAME-INTEGRATION.md §5, FEATURE-PIPELINE-PLAN.md §5.6
- docs/STATUS-DUAL.md, docs/phases/SESSION-PROMPTS-D11-QL5-FPG1.md

Alcance: lo del brief FP-G1 (extractor companion, store, CLI lens snapshot/diff, diff tipado
incl. new entities, fixtures CI). Informe AI = stub / pending phase-11 salvo que 11 ya exista.
No hardcodear ElJuegaso en core. No implementar FP-G2/G3 ni phase-11 en este PR.

Chats: ElJuegaso D11 y QL-5. Contrato manifest con QL-5.
Empieza por confirmar acceptance del brief + ADR si hace falta; espera OK antes de code flood.
Al cerrar: STATUS-DUAL + Self-review + Incidents.
```
