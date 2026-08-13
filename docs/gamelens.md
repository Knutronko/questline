# GameLens (FP-G1)

> Balance **config truth**: snapshot + typed diff driven by a game-declared manifest
> (QL-5). AI implications report is **deferred** until phase-11. See
> [`BALANCE-AUTOMATION.md`](BALANCE-AUTOMATION.md),
> [`adr/ADR-0009-gamelens-snapshot.md`](adr/ADR-0009-gamelens-snapshot.md),
> [`phases/phase-fp-g1-gamelens-snapshot.md`](phases/phase-fp-g1-gamelens-snapshot.md).

## What ships in FP-G1

| Piece | Role |
|-------|------|
| Manifest schema | Game lists balance SOs + `system` tags (economy, creatures, waves, …) |
| Companion exporter | Editor menu **Questline → Export Balance Snapshot** |
| Store | `balance_snapshots` table + JSON under `{artifacts_dir}/lens/<id>/` (see `--store`) |
| CLI | `questline lens snapshot` / `questline lens diff` |
| Diff | Typed: numeric delta/%, added/removed **entities**, curve/series; grouped by system |
| AI report | Stub → `pending phase-11` (framing: *model reasoning* only) |

HUD GameLens panel: **deferred** (CLI MVP; see BACKLOG + `hud.md` evolution).

## Downstream consumers (do not break these contracts)

| Consumer | Needs from FP-G1 |
|----------|------------------|
| **QL-5** (game) | Manifest `schema_version: 1` contents; `asset_path` for Editor export |
| **FP-G2 / QL-6** | Same versioning keys on telemetry sessions. **QL-6 ✅.** Labels/gaps: game `integracion-questline.md` §10. Operator: [`telemetry.md`](telemetry.md). |
| **FP-G3** bots | Diff + snapshot id attached to seeded runs (`config_snapshot_id` + `policy_id` + `seed`); `drain_telemetry`; never invent pass/fail from AI. Brief: [`phases/phase-fp-g3-bots.md`](phases/phase-fp-g3-bots.md). |
| **phase-11** | Wire `implications_stub` → live LLMPort; keep *model reasoning* vs *measured* framing. Measured input = `telemetry_sessions.summary` (do not impute missing KPIs). |
| **D12 / G2+** | Richer events: reuse reserved names in [`telemetry.md`](telemetry.md) (damage, ranch, buff, relocate, revive, projectiles). |
| **FP-F3** feature impact | Optional `feature_id` on snapshots; `added_entity` diffs first-class |
| **HUD (later)** | Read `balance_snapshots` + artifacts; no separate store |

Genre-agnostic hard rule: **no game type names in `src/questline`** — only manifest tags.
## Manifest contract (QL-5 fills contents)

```json
{
  "schema_version": 1,
  "entries": [
    {
      "id": "economy",
      "system": "economy",
      "asset_path": "Assets/Balance/Economy.asset",
      "source_file": "economy.json",
      "kind": "config"
    }
  ],
  "supplementary": [
    { "kind": "markdown", "path": "docs/economias.md" }
  ]
}
```

- **`asset_path`**: required for Unity Editor export (AssetDatabase load).
- **`source_file`**: required for Python `--pack` import (CI / pre-exported dumps).
- Core never hardcodes game type names; unknown / missing assets → clear errors.

Normalized snapshot field types: `number` | `string` | `bool` | `curve` | `series` |
`object` | `null`.

## CLI

```powershell
# Import fixture pack (no Unity)
uv run questline lens snapshot --pack tests/fixtures/lens/pack-a --version 1.0.0 --store .questline/store.db
uv run questline lens snapshot --pack tests/fixtures/lens/pack-b --version 1.1.0 --store .questline/store.db

# Diff (text includes AI stub; JSON machine-readable)
uv run questline lens diff 1.0.0 1.1.0 --store .questline/store.db
uv run questline lens diff 1.0.0 1.1.0 --format json --no-ai --store .questline/store.db

# Import Editor export
uv run questline lens snapshot --import path\to\balance_snapshot.json --store .questline/store.db
```

Keys for `diff` resolve by snapshot **id** or **game_version** (latest).

## Maintainer Editor path

1. Sync `com.questline.companion` (includes `QuestlineBalanceExport`).
2. Place a QL-5 `balance_manifest.json` in the game repo (see sample below).
3. Unity menu **Questline → Export Balance Snapshot** → pick manifest → save JSON
   (UTF-8 **without** BOM; `lens --import` also accepts a UTF-8 BOM from older exports).
4. `questline lens snapshot --import …` into the project store.

Sample (generic; replace paths in QL-5):

See `examples/lens/sample_balance_manifest.json`.

## GameLens Cómo probarlo

```powershell
cd D:\dev\questline
# If uv pip install fails with questline.exe locked: close HUD / other questline
# terminals, then retry. pytest can still run without reinstall.
uv pip install -e ".[dev]"
uv run pytest -q
uv run pytest tests/test_lens.py tests/test_lens_cli.py tests/test_lens_extra.py tests/test_migrations.py -q --no-cov

# --store FILE puts artifacts next to the DB (FILE's parent / artifacts / lens / …)
# NOT under .questline\ unless the store itself lives there.
Remove-Item .questline-tmp-lens.db, artifacts\lens -Recurse -Force -ErrorAction SilentlyContinue
uv run questline lens snapshot --pack tests/fixtures/lens/pack-a --version 1.0.0 --store .questline-tmp-lens.db
uv run questline lens snapshot --pack tests/fixtures/lens/pack-b --version 1.1.0 --store .questline-tmp-lens.db
uv run questline lens diff 1.0.0 1.1.0 --store .questline-tmp-lens.db
Get-Content artifacts\lens\1.0.0\balance_snapshot.json | Select-Object -First 30
uv run questline lens snapshot --import artifacts\lens\1.1.0\balance_snapshot.json --id reimport-1.1 --store .questline-tmp-lens.db
uv run questline lens diff 1.0.0 reimport-1.1 --store .questline-tmp-lens.db
```

Expect: `+ entity unit_beta`, numeric Δ on `amber_per_tick` / `dps`, curve change, and
`pending: phase-11` in the text report.
