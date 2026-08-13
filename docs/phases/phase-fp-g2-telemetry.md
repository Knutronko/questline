# FP-G2 — GameLens: thin gameplay telemetry (measured truth)

> Session preamble: see `phase-00-bootstrap.md`. Read **before coding:**
> [`BALANCE-AUTOMATION.md`](../BALANCE-AUTOMATION.md) (order **G1 → G2/QL-6 → G3 → 11**),
> [`03-FUTURE-PHASES.md`](../03-FUTURE-PHASES.md) Group G · FP-G2,
> [`GAME-INTEGRATION.md`](../GAME-INTEGRATION.md) §4–§5,
> [`gamelens.md`](../gamelens.md) (consumers: same `game_version` / `feature_id` /
> snapshot id as FP-G1),
> [`adr/ADR-0009-gamelens-snapshot.md`](../adr/ADR-0009-gamelens-snapshot.md)
> (**do not reuse ADR-0009**; next free number if schema/store lands),
> [`STATUS-DUAL.md`](../STATUS-DUAL.md),
> [`02-AI-ROADMAP.md`](../02-AI-ROADMAP.md) (framing: *measured* vs *model reasoning*),
> [`hud.md`](../hud.md) HUD-first contract (this phase **defers** the view).
>
> **Scheduled:** immediately after FP-G1 ✅ / QL-5 ✅. **Before** FP-G3 bots.
> **Size:** M. Catalog FP with a full brief (same rules as numbered phases).
>
> Schema OK'd 2026-08-13. Implementation on `fp-g2-thin-telemetry`.

## Context

FP-G1 shipped **config truth** (snapshot + typed diff, ADR-0009). Bots (FP-G3) cannot
leave comparable measured series if they only dump screenshots. FP-G2 is the
**measured truth** layer: a genre-agnostic event API, store tables, and CLI ingest/query.

The reference game maps existing `P1Debug.Event` names → this API in **QL-6** (separate
ElJuegaso chat, after the companion contract exists). Questline core **never** hardcodes
ElJuegaso / P1 type names. Dump files stay; telemetry adds version-comparable series.

**Do not** invert the loop: no FP-G3, no phase-11 AI verdicts, no D12-rich events in this
wave. Thin first, then bots, then richer telemetry with D12.

## Objective

Ship a **thin**, genre-agnostic `QuestlineTelemetry` companion API + store + CLI so
automated Wire runs and manual play spools become queryable sessions keyed the same way
as GameLens snapshots. Session summaries are **computed from events** (plus optional
checkpoints). AI never invents numbers.

## In scope

1. **Companion API** (`QuestlineTelemetry` in `com.questline.companion`): typed emit
   helpers + generic `Emit(name, payload)`. Auto-context on the session envelope
   (version, optional commit / feature / snapshot id / policy / seed). Compile under
   `#if UNITY_EDITOR || QUESTLINE_DEV` (same gate as Wire / balance export).
2. **Transport (two paths, no Wire protocol bump):**
   - **Automated runs:** in-memory buffer drained over existing Wire `call_hook`
     (`DrainTelemetry`). Python writes into the store. Optional end-of-session file
     flush as well.
   - **Manual play:** JSON spool on disk (UTF-8 **without BOM** — INC-0008) imported
     later via CLI.
3. **Store:** append-only **migration 4** — `telemetry_sessions` + `telemetry_events`.
   Do **not** reuse the run-store `events` table (that is framework run/test/step
   traffic). Optional artifact copy of the raw spool under
   `{artifacts_dir}/telemetry/<session_id>/spool.json`.
4. **CLI:** own typer group `questline telemetry` (not under `lens`). Minimum:
   `import` / `query`. CI-testable without Unity.
5. **Session summaries:** JSON blob on the session row, rolled up from known event
   names at ingest (counts, currency net, first leak `t`, waves completed, duration,
   outcome). Checkpoints stored as events; labels are opaque strings.
6. **QL-6 contract** (this brief + ADR-0010): locked thin event names, payload fields,
   and C# emit surface. Mapping table for the reference game lives here as **game-side
   documentation only** — not imported by `src/questline`.
7. **Tests:** fixture spool JSON + migration + CLI; utf-8-sig loaders; ASCII-only CLI
   text (INC-0007).
8. **Docs:** `docs/gamelens.md` (or a short `docs/telemetry.md` if the G2 surface is
   too large for gamelens.md), companion README, GAME-INTEGRATION / STATUS-DUAL /
   BALANCE-AUTOMATION decision log, `hud.md` evolution + BACKLOG HUD deferral, ADR-0010.
9. **HUD view: explicitly deferred** (CLI MVP), same pattern as the GameLens panel.

## Out of scope

- **QL-6** game mapping / P1Debug wiring (ElJuegaso chat after this contract exists)
- **FP-G3** bots, policies, bot suite in `automation/`
- **phase-09c** Wire gestures
- **phase-11** AI implications / LLMPort
- HUD telemetry panel (BACKLOG owner: later HUD slice after G3 data exists)
- D11 retunes, D12 infinite-mode richer events (`creature.grown`, damage series, …)
- New Wire `op` / `protocol_version` bump (use `call_hook`)
- Hardcoding ElJuegaso names in `src/questline`
- Pass/fail verdicts derived from telemetry (store facts only; humans / later AI
  *reason* about them)

## Prerequisites

- FP-G1 snapshot/diff ✅ (ADR-0009). Same versioning keys.
- Companion + Wire `call_hook` ✅ (05b / 09b).
- **Not** required: QL-6 implemented, FP-G3, phase-11, HUD panel.

## Game trigger

| Framework | Game |
|-----------|------|
| **FP-G2** | **QL-6** — map debug events → `QuestlineTelemetry` (thin). Pending until this API exists in the companion the game embeds. |

Mark live dogfood `pending game QL-6`. Finish everything fixture/CI-checkable in this PR.

---

## Proposed schema (lock this in ADR-0010)

### Envelope (session row, not copied onto every event)

| Field | Required | Notes |
|-------|----------|-------|
| `id` | yes | Stable session id (UUID or game-supplied). |
| `schema_version` | yes | Spool JSON = `1`. |
| `game_version` | yes | Same string space as FP-G1 snapshots. |
| `git_commit` | no | |
| `feature_id` | no | Same optional key as snapshots / tests. |
| `config_snapshot_id` | no | GameLens snapshot **id** (not invent a second key). May be null if no snapshot imported yet. **No FK** — snapshot can land later. |
| `policy_id` | no | Empty/null until FP-G3. Store NULL when unset. |
| `seed` | no | TEXT (int or hex). Strongly recommended for comparable runs. |
| `started_at` / `finished_at` | start yes | ISO-8601. |
| `outcome` | on end | Opaque string (`win` / `lose` / `abort` / `unknown` or game-defined). Core does not enum-check beyond non-empty on `session.end`. |
| `source` | yes | `wire` \| `spool` \| `import`. |
| `run_id` | no | Framework pytest run id when drained during a suite. |
| `dropped_count` | no | Events dropped by ring overflow. |

### Event record

| Field | Notes |
|-------|-------|
| `seq` | Monotonic per session (drain / file order). |
| `t` | Seconds from `session.start` (unscaled). `0` on start. |
| `name` | Dotted lowercase catalog name (or extra names — see unknown policy). |
| `payload` | JSON object. Unknown keys preserved. |

**Unknown event names:** ingest and store (forward-compatible). Session summary rollup
**only** uses the thin catalog below. CLI may note `unknown_event_names` in query JSON.
Do not fail the import.

**Overflow:** in-memory ring (default 10 000). Drop-oldest; increment `dropped_count`.
`DrainTelemetry` returns at most **500** events per call so Wire JSON stays bounded.

### Thin event catalog (QL-6 contract)

Genre-agnostic names. Ids (`currency_id`, `unit_id`, `skill_id`, checkpoint `label`)
are **opaque strings declared by the game**. Core never interprets them.

| `name` | When | Required payload | Optional payload |
|--------|------|------------------|------------------|
| `session.start` | Combat / measured session begins | — | `level_id`, `mode` (opaque) |
| `session.end` | Session finishes | `outcome` | `duration_s`, `wave_index` |
| `session.checkpoint` | KPI moment / periodic snapshot | `label` (opaque) | `currencies` (map id→number), `wave_index`, `extra` (object) |
| `currency.earned` | Inflow | `currency_id`, `amount` (>0) | `balance_after`, `source` (opaque: tick, pickup, …) |
| `currency.spent` | Outflow | `currency_id`, `amount` (>0) | `balance_after`, `sink` (opaque: deploy, skill, repair, buff, …) |
| `unit.deployed` | A unit is placed | `unit_id` | `cost`, `currency_id`, `lane`, `slot`, `tags` (string list, game-defined) |
| `combat.leak` | Enemy / threat reaches fail condition | — | `wave_index`, `lane`, `unit_id` (`t` is the event `t`) |
| `wave.started` | Wave (or between-wave prep) begins | `wave_index` (int ≥ 0) | — |
| `wave.completed` | Wave cleared | `wave_index` | `duration_s`, `cleared` (bool, default true) |
| `skill.cast` | Skill actually fires | `skill_id` | `cost`, `currency_id`, `wave_index` |
| `repair.applied` | Repair / equivalent sink succeeds | — | `cost`, `currency_id`, `amount` |

**Not in thin (defer to D12 / G2+):** damage dealt/taken, projectile traces,
creature growth / ranch, buff draft pick/skip as first-class events, relocate, revive /
soft currency, per-frame fossil ticks as a separate name (map tick → `currency.earned`
with `source`). **Reserved names** (do not invent aliases): see
[`telemetry.md`](../telemetry.md) later catalog and
`questline.telemetry.schema.FUTURE_EVENT_NAMES`. Games may still `Emit` extra names;
they will store but not roll up.

**Downstream briefs** (written so later sessions do not rediscover this contract):
[`phase-fp-g3-bots.md`](phase-fp-g3-bots.md),
[`SESSION-PROMPTS-QL6-FPG3.md`](SESSION-PROMPTS-QL6-FPG3.md),
phase-11 measured-data note, BACKLOG HUD + G2+ events.

**Why `session.checkpoint`:** KPIs like “currency at prep-end / post-Nth-deploy / mid-W1”
need a phase label the core cannot infer. The game emits a checkpoint with an opaque
`label`; QL-6 chooses labels. Core stores them as events.

### Session summary (computed at ingest)

JSON on `telemetry_sessions.summary`. Measured facts only:

```json
{
  "event_counts": { "currency.earned": 12, "unit.deployed": 5 },
  "currency_net": { "soft": 40 },
  "currency_in": { "soft": 120 },
  "currency_out": { "soft": 80 },
  "deploy_count": 5,
  "skill_casts": 2,
  "repair_count": 1,
  "leak_count": 1,
  "time_to_first_leak": 42.5,
  "waves_started": 3,
  "waves_completed": 2,
  "duration_s": 90.0,
  "outcome": "lose",
  "checkpoint_labels": ["prep_end", "mid_w1"],
  "dropped_count": 0,
  "unknown_event_names": []
}
```

`currency_net` keys are whatever `currency_id` values appeared. No P1 names in code —
fixtures in tests may use generic ids (`soft`, `unit_a`) or a doc example `amber`.

### Spool JSON (`schema_version: 1`)

```json
{
  "schema_version": 1,
  "session": {
    "id": "sess-example",
    "game_version": "1.0.0",
    "git_commit": null,
    "feature_id": null,
    "config_snapshot_id": "1.0.0",
    "policy_id": null,
    "seed": "42",
    "started_at": "2026-08-13T12:00:00+00:00",
    "finished_at": "2026-08-13T12:01:30+00:00",
    "outcome": "lose",
    "source": "spool",
    "dropped_count": 0
  },
  "events": [
    { "seq": 1, "t": 0.0, "name": "session.start", "payload": { "mode": "ieb" } },
    { "seq": 2, "t": 1.2, "name": "currency.earned", "payload": { "currency_id": "soft", "amount": 25, "balance_after": 125, "source": "tick" } }
  ]
}
```

Encoding: UTF-8 without BOM on write; Python reads `utf-8-sig`.

### SQLite (migration 4)

```sql
CREATE TABLE IF NOT EXISTS telemetry_sessions (
    id TEXT PRIMARY KEY,
    game_version TEXT NOT NULL,
    git_commit TEXT,
    feature_id TEXT,
    config_snapshot_id TEXT,
    policy_id TEXT,
    seed TEXT,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    outcome TEXT,
    source TEXT NOT NULL,
    run_id TEXT,
    artifact_path TEXT,
    summary TEXT,
    meta TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tel_sessions_version ON telemetry_sessions(game_version);
CREATE INDEX IF NOT EXISTS idx_tel_sessions_snapshot ON telemetry_sessions(config_snapshot_id);
CREATE INDEX IF NOT EXISTS idx_tel_sessions_policy ON telemetry_sessions(policy_id);
CREATE INDEX IF NOT EXISTS idx_tel_sessions_feature ON telemetry_sessions(feature_id);
CREATE INDEX IF NOT EXISTS idx_tel_sessions_created ON telemetry_sessions(created_at);

CREATE TABLE IF NOT EXISTS telemetry_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES telemetry_sessions(id),
    seq INTEGER NOT NULL,
    t REAL NOT NULL,
    name TEXT NOT NULL,
    payload TEXT NOT NULL,
    UNIQUE(session_id, seq)
);
CREATE INDEX IF NOT EXISTS idx_tel_events_session ON telemetry_events(session_id);
CREATE INDEX IF NOT EXISTS idx_tel_events_name ON telemetry_events(name);
```

Re-import of the same `session.id`: **replace** session row + delete/replace events
(documented; CLI `--replace` or implicit on same id). Do not silently duplicate.

---

## C# API (how the game emits)

Namespace `Questline.Companion`. Games call this from gameplay code (QL-6); they do
not need to know Wire.

```csharp
var ctx = new TelemetryContext {
    SessionId = Guid.NewGuid().ToString("N"),
    GameVersion = Application.version, // or PlayerSettings.bundleVersion in Editor
    GitCommit = null,
    FeatureId = null,
    ConfigSnapshotId = null,  // optional; bots/G3 will set when known
    PolicyId = null,          // FP-G3
    Seed = seed.ToString(),
};
QuestlineTelemetry.BeginSession(ctx);
QuestlineTelemetry.Checkpoint("prep_end", currencies: null, waveIndex: 0);
QuestlineTelemetry.CurrencyEarned("soft", 25, balanceAfter: 125, source: "tick");
QuestlineTelemetry.CurrencySpent("soft", 50, balanceAfter: 75, sink: "deploy");
QuestlineTelemetry.UnitDeployed("unit_a", cost: 50, currencyId: "soft", lane: 1, tags: new[] { "fighter" });
QuestlineTelemetry.CombatLeak(waveIndex: 2, lane: 0);
QuestlineTelemetry.WaveStarted(0);
QuestlineTelemetry.WaveCompleted(0, durationS: 30f);
QuestlineTelemetry.SkillCast("skill_a", cost: 80, currencyId: "soft", waveIndex: 1);
QuestlineTelemetry.RepairApplied(cost: 40, currencyId: "soft");
QuestlineTelemetry.Emit("custom.foo", payloadJson); // extra names OK
QuestlineTelemetry.EndSession("lose");
```

**Hooks registered by the companion** (no game registration required):

| Hook | Role |
|------|------|
| `BeginTelemetrySession` | Optional; Python/bots may start a session with context JSON before play. |
| `EndTelemetrySession` | Force end + flush spool. Arg: outcome. |
| `DrainTelemetry` | Return JSON `{ "events": [...], "dropped_count": N, "session": {...} }` and clear the drained prefix. |
| `TelemetryStatus` | Buffer count, session id, dropped_count (debug). |

Spool path (manual): `{persistentDataPath}/questline_telemetry/<session_id>.json`
flushed on `EndSession` and periodically (e.g. every N events). Never log secrets;
session meta is version/seed/ids only.

---

## QL-6 mapping (reference game — documentation only)

**Not implemented in this FP.** When QL-6 runs in ElJuegaso, map ~1:1. Core tests must
not import this table.

| P1Debug.Event | Thin `name` | Notes |
|---------------|-------------|-------|
| combat / IEB start (`Root.StartIeb` / combat begin) | `session.start` | `mode` e.g. ieb / campaign (opaque) |
| `Combat.End` | `session.end` | outcome win/lose |
| `Balance.Snapshot` / KPI moments | `session.checkpoint` | labels e.g. `prep_end`, `post_3_deploy`, `mid_w1`, `mid_w2`, `between_wave`, `end` — **game chooses** |
| `Amber.Gain` / `Fossil.Tick` | `currency.earned` | `currency_id` chosen by game (do not put that string in questline core) |
| `Amber.Spend` | `currency.spent` | `sink` = deploy / skill / repair / buff / … |
| `Deploy.Dino` / `Deploy.Collector` | `unit.deployed` | distinguish via `tags` or `unit_id`, not core enums |
| `Combat.Leak` | `combat.leak` | first leak `t` = event `t` |
| wave begin | `wave.started` | |
| `Wave.Cleared` | `wave.completed` | |
| `Skill.Cast` | `skill.cast` | PanelOpen/Arm/Cancel stay debug-only unless later promoted |
| `Repair.Apply` | `repair.applied` | Warn-only short/CD/none → do not emit |

Out of thin: `Shot.*`, ranch, `Buff.*`, `Wave.W2PlusPressure`, `Spawn.Enemy` (optional
later). Dump remains.

---

## CLI (proposed)

```powershell
uv run questline telemetry import path\to\spool.json --store .questline/store.db
uv run questline telemetry query --store .questline/store.db
uv run questline telemetry query --version 1.0.0 --snapshot 1.0.0 --store .questline/store.db
uv run questline telemetry query sess-example --format json --store .questline/store.db
```

- `import`: validate envelope, write artifact, insert session + events, compute summary.
- `query` with no id: list sessions (version, snapshot, policy, seed, outcome, event count).
- `query <id|prefix>`: one session summary + event_counts; `--format json` for machines.
- Optional thin compare (nice-to-have if cheap): `--compare <idA> <idB>` diffs summary
  numeric fields. Full curve overlay waits for G3.

Human text: ASCII-only (INC-0007). `--store FILE` artifacts next to the DB parent
(same rule as `lens`).

Python drain helper (for G3 / live tests, can ship a small function now):
`drain_telemetry(driver, store)` looping `DrainTelemetry` until empty.

## Transport decision (ADR-0010)

**Use hooks, not a new Wire op.** Reasons: no `protocol_version` bump, FakeWire already
speaks `call_hook`, AltTester legacy path still works via `InvokeHook`. Revisit a
dedicated op only if drain polling becomes a bottleneck in G3 soak.

## HUD

**Defer.** Update `docs/hud.md` evolution: FP-G2 row = CLI only (like GameLens).
BACKLOG: `(fp-g2) HUD telemetry view` — owner later, after G3 produces several sessions
worth browsing. Self-review: `Verified in HUD: n/a (telemetry view deferred)`.

## ADR

**ADR-0010** (next free after 0009): spool schema, event catalog, migration 4, hook
drain vs Wire op, unknown-event policy, HUD defer. Do **not** reuse ADR-0009.

## Tests (CI, no Unity)

- Migration 4 applies on a v3 store; `CURRENT_SCHEMA_VERSION == 4`.
- Import fixture spool → session + events + summary numbers.
- Re-import same id replaces, does not duplicate.
- Missing `game_version` → clear error.
- Extra / unknown event name stored; listed in `unknown_event_names`.
- BOM spool still imports (`utf-8-sig`).
- CLI `import` + `query` smoke (text + json).
- Companion C#: no Python compile of C#; document maintainer Editor path. Optional:
  fixture JSON **as if** emitted by the API (golden spool in `tests/fixtures/telemetry/`).

## Docs to touch at implementation (not this OK-wait)

- This brief (lessons after merge).
- `docs/gamelens.md` downstream G2 section **or** `docs/telemetry.md` + pointer.
- `unity-package/README.md` emit + drain example.
- `GAME-INTEGRATION.md` §4 FP-G2 row status notes.
- `STATUS-DUAL.md` semáforo when the PR lands (G2 in progress / done).
- `BALANCE-AUTOMATION.md` decision log date when G2 ships.
- `hud.md` + `BACKLOG.md` HUD defer.
- `03-FUTURE-PHASES.md` FP-G2 status line.
- ADR-0010.

## Acceptance criteria

- [x] Brief + schema OK'd by maintainer (this file). Then implement on a branch.
- [x] CI: ingest + summary + CLI on fixtures; migrations test covers v4; no Unity.
- [x] Companion `QuestlineTelemetry` + drain hooks; UTF-8 no BOM spool writer.
- [x] `questline telemetry import` / `query` work with `--store` without Unity.
- [x] Genre-agnostic: grep-gate or review — no P1 type/SO/event names under `src/questline`.
- [x] HUD telemetry **explicitly deferred** (hud.md + BACKLOG).
- [x] ADR-0010 + STATUS-DUAL + GAME-INTEGRATION + companion README.
- [x] QL-6 contract (catalog + C# + mapping table) in brief/ADR; game mapping **not** in this PR.
- [ ] Self-review + `Incidents: …` in PR; no secrets in spools/fixtures.

## PR checklist

Title `fp-g2: thin telemetry ingest and companion API`.
Self-review required. Link QL-6 when that game PR exists.
PowerShell Cómo probarlo (fixture import/query; optional Editor spool after QL-6).

## Lessons / incidents

- Thin catalog locked independently of QL-6 contents; CI uses generic fixture spools
  (`tests/fixtures/telemetry/`). Later event names reserved in `FUTURE_EVENT_NAMES`.
- HUD telemetry panel **explicitly deferred** (CLI MVP); G3/QL-6 briefs point at
  ADR-0010 + `drain_telemetry` so they do not rediscover the contract.
- **Incidents:** none (this PR).
