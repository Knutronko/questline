# Questline — Feature Pipeline Plan (documento independiente)

> **Qué es este documento:** el plan completo del pipeline feature→tests ("cada vez que
> añado algo al juego, el framework me propone y genera la cobertura: unit C#, e2e, API,
> perf y balance"). Es un documento APARTE — no modifica ningún doc del repo. Cuando
> decidas programar sus fases, este doc es la fuente para escribir los briefs; mientras
> tanto, la sección 5 trae los prompts-addendum listos para pegar a las sesiones de las
> fases ya planificadas para que dejen los ganchos preparados.
>
> Decisiones tomadas (29 jul): trigger = CLI git-diff bajo demanda · intención = híbrido
> diff + descripción corta (inferencia pura como fallback) · unit C# = generados en rama
> del repo del juego con tu review · encaje = nuevo grupo FP-F + addendums.

---

## 1. El pipeline de un vistazo

```
   (desarrollas una feature en tu juego y la terminas)
                      │
                      ▼
   questline feature scan          ← FP-F1
   · git diff del repo del juego vs último commit analizado
   · detecta: SO nuevos/cambiados, scripts nuevos, hooks nuevos,
     escenas/prefabs tocados, strings nuevas
   · te enseña el resumen y te pide 2-4 líneas de descripción
                      │
                      ▼
   Feature Registry (store)        ← FP-F1
   · feature_id, descripción, commit range, artefactos detectados,
     variables de balance introducidas, tests vinculados
                      │
                      ▼
   questline feature plan <id>     ← FP-F2 (IA)
   · coverage plan propuesto por tipo:
     unit C# · e2e · API · perf · balance-watch
   · TÚ apruebas/editas el plan (gate humano)
                      │
                      ▼
   questline feature generate <id> ← FP-F2 (IA)
   · e2e Python → rama en el repo questline-tests del juego
   · unit C# (UTF) → rama en el repo del juego
   · API tests → suites del módulo api (si aplica)
   · cada test queda tagged con el feature_id
   · gate: todo test generado debe EJECUTAR antes de reportarse
                      │
                      ▼
   questline feature impact <id>   ← FP-F3 (IA + GameLens)
   · snapshot de balance post-feature vs pre-feature
   · entidades nuevas (torre nueva, dino nuevo) analizadas contra
     el ecosistema existente
   · informe: implicaciones en gameplay/economía + focos de playtest
```

Resultado acumulado: el juego crece con su cobertura, el registry responde "¿qué cubre la
feature X?" y "¿qué feature introdujo esta variable?", y el HUD enseña salud por feature.

---

## 2. FP-F1 — Feature scan + Feature Registry · M · sin IA

**Qué hace:**
- `questline feature scan [--game-repo <path>]`: diff del repo del juego desde el último
  commit analizado (marcador en el store). Detección tipada:
  - ScriptableObjects nuevos/modificados (reutiliza el extractor de FP-G1 si ya existe;
    si no, parser propio de .asset YAML de Unity),
  - scripts C# nuevos + clases/métodos públicos añadidos,
  - hooks nuevos del companion package (manifest de hooks),
  - escenas/prefabs añadidos o tocados,
  - claves de localización nuevas.
- Prompt interactivo: resumen de lo detectado + petición de descripción corta (2-4 líneas).
  Sin descripción → se marca `intent_source: inferred` (la calidad del plan baja y el doc
  lo dice; ver decisión 2).
- **Feature Registry** en el store: tabla `features` (id, nombre, descripción, commits,
  artefactos, `intent_source`, fecha) + vínculos test↔feature y variable-de-balance↔feature.
- `questline feature list/show <id>`: estado de cobertura por feature (qué tipos tiene,
  verdes/rojos del último run).

**Prerequisitos:** fases 01 (store con migraciones — ver addendum §5.1), 03 (tagging),
04 (manifest de hooks — ver addendum §5.3). NO necesita la capa IA → puede programarse
pronto, incluso antes de la fase 11.

## 3. FP-F2 — Coverage planner + generación multi-tipo · L · IA

**Qué hace:**
- `questline feature plan <id>`: agente (kernel de fase 12) cruza diff + descripción +
  registry + páginas/locators existentes → **coverage plan** estructurado (JSON + vista
  legible): por cada tipo (unit C#, e2e, API, perf), los casos concretos con
  justificación y prioridad. Tú lo apruebas o editas (archivo o HUD).
- `questline feature generate <id>`: genera lo aprobado —
  - **e2e Python**: vía el generador de la fase 13 (que recibe el coverage plan como spec
    enriquecida); páginas/locators desconocidos → TODOs con sugerencias desde hierarchy.
  - **unit C# (UTF)**: generación nueva — tests NUnit para la lógica detectada (economía,
    crianza, torres), escritos en una RAMA del repo del juego, nunca directo a main;
    ejecutables vía la orquestación batchmode de la fase 14; tu review antes de merge.
  - **API**: si el coverage plan lo incluye, suites del módulo `questline.api` (FP-T1),
    contra mock server si aún no hay backend real.
  - **perf**: no genera tests — añade la feature a los escenarios de PerfProbe con
    thresholds sugeridos.
- Gates heredados de la fase 13: todo test generado debe ejecutar (verde, o rojo por la
  razón declarada) antes de reportarse como éxito; nada se auto-mergea.
- Tagging: cada artefacto generado lleva el `feature_id` (marker en Python, atributo/
  categoría en NUnit) → el registry y el HUD los agrupan.

**Prerequisitos:** FP-F1 + fases 11-13 (capa IA + generador) + fase 14 (UTF) + FP-T1
para la pata API (degrada con aviso si no está).

## 4. FP-F3 — Impacto en balance/economía por feature · M · IA + GameLens

**Qué hace:**
- `questline feature impact <id>`: snapshot GameLens post-feature vs el snapshot previo,
  acotado a la feature: variables NUEVAS (entidad nueva: torre, dino, oleada) analizadas
  contra el ecosistema existente (¿esta torre domina a las demás por coste/DPS? ¿el dino
  nuevo rompe la curva de comida?), y variables EXISTENTES tocadas por la feature.
- Informe IA con el framing de FP-G1 (razonamiento del modelo etiquetado como tal;
  telemetría medida etiquetada como medida cuando FP-G2/G3 existan) + focos de playtest
  sugeridos + registro en el registry (la feature queda vinculada a sus variables).
- Con FP-G3 disponible: opción de lanzar bots pre/post feature y añadir la curva medida.

**Prerequisitos:** FP-F1 + FP-G1 (y opcionalmente G2/G3 para la parte medida).

**Orden recomendado del grupo:** FP-F1 → (FP-G1 si no está) → FP-F3 → FP-F2.
F1 da valor sin IA desde el primer día (registry + scan); F3 es tu mayor dolor declarado
(balance); F2 es la pieza grande y necesita casi toda la capa IA.

---

## 5. Fases afectadas + prompts-addendum (pégalos a la sesión de cada fase)

> Uso: pega el prompt al ARRANCAR la sesión de esa fase, junto al brief. Son en inglés
> (idioma del repo). Cada uno es un gancho barato — ninguno cambia el alcance de su fase.

### 5.1 Fase 01 — Core kernel (LA ESTÁS HACIENDO AHORA — pégalo ya)

```
ADDENDUM to phase-01 brief (approved by maintainer):
The run store must support lightweight schema migrations from day 1: a schema_version
table plus an ordered-migrations mechanism applied on open, and a unit test proving an
old store upgrades cleanly. Future modules will add tables (features, feature_links,
telemetry, eval_results) without refactoring. Do NOT create those future tables now —
only the migration mechanism. Also: events carry an optional free-form `tags: dict[str,str]`
field (empty by default) so future modules can annotate events (e.g. feature_id) without
schema changes.
```

### 5.2 Fase 03 — Authoring layer

```
ADDENDUM to phase-03 brief (approved by maintainer):
Add first-class test metadata `feature="<id>"` (marker or decorator param) alongside the
existing markers. It must: flow into the run store on every test result (tests table gains
a nullable feature_id column via a migration), be filterable at collection time
(`--feature <id>`), and appear in the quarantine ledger entries. Keep it optional and
non-breaking: tests without a feature tag behave exactly as before. A future "feature
registry" module will join on this column.
```

### 5.3 Fase 04 — AltTester adapter + Unity companion

```
ADDENDUM to phase-04 brief (approved by maintainer):
QuestlineHooks must be introspectable: the companion package exposes a machine-readable
manifest of registered hooks (name, typed args, causesSoftReload, optional `feature` label)
retrievable from the Python side via a single driver call. Rationale: a future feature-scan
tool diffs this manifest between game versions to detect newly added hooks. Keep it simple:
one serializable registry dump, covered by one test in the smoke suite.
```

### 5.4 Fase 13 — AI generation + eval harness

```
ADDENDUM to phase-13 brief (approved by maintainer):
Design the test generator's input as a structured CoveragePlanItem (intent description +
target area + expected behavior + priority), with "a plain-text spec" being just a
single-item plan. Rationale: a future feature-pipeline module will feed the generator
multi-item coverage plans derived from game-repo diffs; the generator should not need
rework to accept them. Document the CoveragePlanItem schema in docs/. No feature-scan
logic in this phase.
```

### 5.5 Fase 14 — Poco + UTF (menor)

```
ADDENDUM to phase-14 brief (approved by maintainer):
When ingesting Unity Test Framework NUnit XML, map NUnit categories to Questline test
metadata — specifically, a category of the form "feature:<id>" populates the same
feature_id column phase 03 introduced. One parser test with a categorized fixture.
```

### 5.6 FP-G1 — GameLens (cuando la programes)

```
ADDENDUM to FP-G1 brief (approved by maintainer):
The balance diff engine must treat NEW entities (a ScriptableObject that did not exist in
the previous snapshot) as a first-class diff type — not just changed values. New-entity
diffs carry the full stat block and are analyzed against existing entities of the same
family (relative positioning: cost/effect ratios vs peers). Snapshots and diff entries
accept an optional feature_id so a future feature-impact command can scope a diff to one
feature's changes.
```

### 5.7 Fases NO afectadas

00, 02, 05–10, 11, 12, 15 no necesitan cambios: el pipeline consume sus piezas tal cual
(kernel de agentes, HUD, PerfProbe, reporters). Si al ejecutarlas surge un conflicto con
este plan, apúntalo en BACKLOG.md y revisamos aquí.

---

## 6. Ejemplo end-to-end (tu juego)

1. Terminas la feature "evolución de dinos": `DinoEvolutionConfig.asset` (SO nuevo),
   `EvolutionService.cs`, hook `TriggerEvolution`, botón nuevo en la UI del criadero.
2. `questline feature scan` → detecta los 4 artefactos; escribes: "Los dinos evolucionan
   al nivel 10 si han comido 50 bayas; la evolución sube DPS x1.5 y coste de comida x2."
3. `questline feature plan dino-evolution` → propone: 6 unit C# (umbral 10/50, doble
   trigger, save/load del estado evolucionado…), 2 e2e (flujo UI de evolución; el dino
   evolucionado persiste tras reiniciar), 1 API (si hubiera backend de guardado), perf
   (escena del criadero con N dinos evolucionados), balance-watch (DPS x1.5 y comida x2
   registrados). Apruebas quitando/añadiendo lo que quieras.
4. `questline feature generate` → rama `questline/dino-evolution-tests` en el repo del
   juego (unit C#) + rama en el repo de tests (e2e). Revisas y mergeas.
5. `questline feature impact` → informe: "DPS x1.5 posiciona al dino evolucionado por
   encima de la torre tier-3 a igual coste acumulado → riesgo de dominancia desde la
   oleada 8; el x2 de comida solo compensa si la baya mantiene su precio actual…" +
   focos de playtest.
6. HUD → pestaña de la feature: cobertura, últimos verdes, variables que introdujo.

---

## 7. Registro de decisiones de este plan

| Fecha | Decisión |
|---|---|
| 2026-07-29 | Trigger: CLI git-diff bajo demanda (Editor window = azúcar futuro; auto-commit = flag opcional futuro, nunca default) |
| 2026-07-29 | Intención: híbrido diff + descripción corta; inferencia pura solo como fallback marcado `inferred` |
| 2026-07-29 | Unit C#: generados en rama del repo del juego, review humana, ejecutados vía fase 14 |
| 2026-07-29 | Encaje: grupo FP-F nuevo (F1 scan+registry, F2 planner+generación, F3 impacto balance) + addendums a fases 01/03/04/13/14 y FP-G1 |
| 2026-07-29 | Orden recomendado: FP-F1 → FP-G1 → FP-F3 → FP-F2 |
