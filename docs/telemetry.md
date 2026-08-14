# GameLens telemetry (FP-G2)

> **Measured truth:** event series + session summaries. Config truth remains
> [`gamelens.md`](gamelens.md) (FP-G1). Schema: [`adr/ADR-0010-gamelens-telemetry.md`](adr/ADR-0010-gamelens-telemetry.md).
> Brief: [`phases/phase-fp-g2-telemetry.md`](phases/phase-fp-g2-telemetry.md).
> Loop: [`BALANCE-AUTOMATION.md`](BALANCE-AUTOMATION.md).

HUD telemetry view: **deferred** (CLI MVP). Same pattern as the GameLens panel.

## Thin catalog (locked)

| `name` | Required payload | Optional |
|--------|------------------|----------|
| `session.start` | — | `level_id`, `mode` |
| `session.end` | `outcome` | `duration_s`, `wave_index` |
| `session.checkpoint` | `label` (opaque) | `currencies`, `wave_index`, `extra` |
| `currency.earned` | `currency_id`, `amount` > 0 | `balance_after`, `source` |
| `currency.spent` | `currency_id`, `amount` > 0 | `balance_after`, `sink` |
| `unit.deployed` | `unit_id` | `cost`, `currency_id`, `lane`, `slot`, `tags[]` |
| `combat.leak` | — | `wave_index`, `lane`, `unit_id` (`t` on the event) |
| `wave.started` | `wave_index` ≥ 0 | — |
| `wave.completed` | `wave_index` | `duration_s`, `cleared` |
| `skill.cast` | `skill_id` | `cost`, `currency_id`, `wave_index` |
| `repair.applied` | — | `cost`, `currency_id`, `amount` |

Unknown names are **stored** but not rolled into the summary. Core never interprets
id strings.

### Session envelope

`game_version` (required at ingest), optional `git_commit`, `feature_id`,
`config_snapshot_id` (FP-G1 snapshot **id**), `policy_id` (NULL until FP-G3),
`seed` (TEXT), `source` = `wire` | `spool` | `import`, optional `run_id`.

## Later catalog (D12 / G2+ — do not invent parallel names)

These names are reserved in `questline.telemetry.schema.FUTURE_EVENT_NAMES`.
Thin G2 does **not** emit or roll them up. When a later phase adds them, **reuse
the string** and extend summaries via a **new** store migration (never rewrite
migration 4).

| Reserved `name` | Typical payload (sketch) | Why later |
|-----------------|--------------------------|-----------|
| `combat.damage` | `amount`, opaque `attacker_id` / `victim_id`, optional `tags` | Unit power / DPS curves |
| `projectile.spawn` | ids, kind | Combat traces; optional if `combat.damage` is enough |
| `projectile.hit` | ids | Same |
| `projectile.dissipate` | ids, reason | Same |
| `creature.grown` | `unit_id`, opaque `stage` | Ranch / meta progression (D12+) |
| `buff.picked` | `buff_id`, optional `cost` / `currency_id` | Between-wave draft pick rate |
| `buff.skipped` | optional `wave_index` | Draft skip rate |
| `unit.relocated` | `unit_id`, from/to | Relocate casts / wave |
| `session.revive` | `cost`, `currency_id` | Soft spend / fail recovery |
| `enemy.spawn` | `unit_id`, `lane`, `wave_index` | Pressure / lane occupancy (can wait if leak+wave suffice) |

Still **not** first-class (stay in game debug dumps unless a later brief promotes
them): per-frame ticks as a distinct name (map to `currency.earned` + `source`),
panel-open / arm / cancel for skills, cheat toggles.

Checkpoint **labels** stay game-defined. Suggested labels for KPI moments (QL-6
chooses; core does not require this list): `prep_end`, `post_3_deploy`, `mid_w1`,
`mid_w2`, `between_wave`, `end`.

## CLI

```powershell
uv run questline telemetry import tests/fixtures/telemetry/sess-a.json --store .questline-tmp-tel.db
uv run questline telemetry import tests/fixtures/telemetry/sess-b.json --store .questline-tmp-tel.db
uv run questline telemetry query --store .questline-tmp-tel.db
uv run questline telemetry query sess-a --store .questline-tmp-tel.db
uv run questline telemetry query sess-a --format json --store .questline-tmp-tel.db
uv run questline telemetry query sess-a --compare sess-b --store .questline-tmp-tel.db
```

`--store FILE` puts artifacts at `FILE.parent / artifacts / telemetry / <id> / spool.json`.

## Companion emit (QL-6)

Call only from `#if UNITY_EDITOR || QUESTLINE_DEV` (companion asmdef is gated).
Wire bootstrap registers hooks; games also `QuestlineTelemetry.EnsureRegistered()`.

```csharp
var ctx = new TelemetryContext {
    SessionId = Guid.NewGuid().ToString("N"),
    GameVersion = Application.version,
    Seed = seed.ToString(),
};
QuestlineTelemetry.BeginSession(ctx);
QuestlineTelemetry.CurrencyEarned("soft", 25, balanceAfter: 125, source: "tick");
QuestlineTelemetry.EndSession("lose");
```

Spool: `{persistentDataPath}/questline_telemetry/<session_id>.json` (UTF-8 no BOM).

Hooks: `BeginTelemetrySession` / `SetTelemetryContext` (JSON string),
`EndTelemetrySession` (outcome), `DrainTelemetry`, `TelemetryStatus`.

## Consumers

| Consumer | How to use this |
|----------|-----------------|
| **QL-6** | Map done (2026-08-13). Game mapping + dogfood labels/gaps live in ElJuegaso `docs/prototipos/P1/integracion-questline.md` §10 (not in `src/questline`). |
| **FP-G3** | Set `policy_id` + `seed` + `config_snapshot_id` via `SetTelemetryContext` **after** combat `BeginSession` (`LoadIeb` wipes context if set too early). Then `drain_telemetry(driver, store)` after the session. IEB play does **not** set `P1Rng` unless the bot calls `SetSeed`. Checkpoints the game actually emits: `post_3_deploy`, `between_wave`, `prep_end`, `end` — **not** `mid_w1`/`mid_w2`. ∞Ám sessions omit `currency.spent`. Buff v1 = `SkipBuffDraft` (no offer list on `BoardState`). Brief: [`phases/phase-fp-g3-bots.md`](phases/phase-fp-g3-bots.md). |
| **phase-11** | Read `telemetry_sessions.summary` as *measured*. Never invent missing KPIs (no `enemy.spawn` / ally KO / DPS until D12). |
| **HUD (later)** | Read the same tables; no second store. BACKLOG owner. |
| **D12 / G2+** | Append reserved names above; new migration if summary columns/JSON keys grow. Game note: `diseno-modo-infinito.md`. |

Python drain (automated runs):

```python
from questline.telemetry import drain_telemetry

drain_telemetry(driver, store, end_outcome="lose", run_id=run_id)
```

## Cómo probarlo (CI / no Unity)

```powershell
cd D:\dev\questline
uv pip install -e ".[dev]"
uv run pytest tests/test_telemetry.py tests/test_migrations.py -q --no-cov
uv run questline telemetry import tests/fixtures/telemetry/sess-a.json --store .questline-tmp-tel.db
uv run questline telemetry query sess-a --store .questline-tmp-tel.db
```
