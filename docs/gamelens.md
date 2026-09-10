# GameLens (FP-G1)

> Balance **config truth**: snapshot + typed diff driven by a game-declared manifest
> (QL-5). AI implications: **live report** via LLMPort (`lens diff --ai`) — *model
> reasoning*, never a verdict. See
> [`BALANCE-AUTOMATION.md`](BALANCE-AUTOMATION.md),
> [`adr/ADR-0009-gamelens-snapshot.md`](adr/ADR-0009-gamelens-snapshot.md),
> [`adr/ADR-0011-llmport-budget.md`](adr/ADR-0011-llmport-budget.md),
> [`ai-setup.md`](ai-setup.md),
> [`phases/phase-fp-g1-gamelens-snapshot.md`](phases/phase-fp-g1-gamelens-snapshot.md),
> [`phases/phase-fp-g1-implications-live.md`](phases/phase-fp-g1-implications-live.md).

## What ships in FP-G1

| Piece | Role |
|-------|------|
| Manifest schema | Game lists balance SOs + `system` tags (economy, creatures, waves, …) |
| Companion exporter | Editor menu **Questline → Export Balance Snapshot** |
| Store | `balance_snapshots` + `lens_implications` (migration 6); JSON under `{artifacts_dir}/lens/<id>/` |
| CLI | `questline lens snapshot` / `questline lens diff` (`--ai` default) |
| Diff | Typed: numeric delta/%, added/removed **entities**, curve/series; grouped by system |
| AI report | **Live:** `build_implications` via LLMPort. Persists `artifacts/lens/<a>__<b>/implications.json` + `.md` and a `lens_implications` store row (migration 6). Framing: *model reasoning*. Numbers from `telemetry_sessions.summary` only. `snap-unset` sessions are **unjoined** (never a silent version join). Missing KPIs (`combat.damage`, other `FUTURE_EVENT_NAMES`) are gaps, never imputed. Design-copilot / retune chat remains FP-G4. |

HUD GameLens panel: **phase-12b** (after phase-12). Until then: CLI + persisted artifacts
(see BACKLOG + `hud.md`).

## Downstream consumers (do not break these contracts)

| Consumer | Needs from FP-G1 |
|----------|------------------|
| **QL-5** (game) | Manifest `schema_version: 1` contents; `asset_path` for Editor export |
| **FP-G2 / QL-6** | Same versioning keys on telemetry sessions. **QL-6 ✅.** Labels/gaps: game `integracion-questline.md` §10. Operator: [`telemetry.md`](telemetry.md). |
| **FP-G3** bots | Diff + snapshot id attached to seeded runs (`config_snapshot_id` + `policy_id` + `seed`); `drain_telemetry`; never invent pass/fail from AI. Brief: [`phases/phase-fp-g3-bots.md`](phases/phase-fp-g3-bots.md). |
| **phase-11** | LLMPort substrate used by `build_implications`. |
| **G1 live report** | Persist implications; join measured sessions; `snap-unset` → gap. |
| **D12 / G2+** | Richer events: reuse reserved names in [`telemetry.md`](telemetry.md) (damage, ranch, buff, relocate, revive, projectiles). |
| **FP-F3** feature impact | Optional `feature_id` on snapshots; `added_entity` diffs first-class |
| **FP-G4** | Design copilot / RAG chat over snapshots + telemetry + reports. |
| **HUD (phase-12b)** | Read `balance_snapshots` + `lens_implications` + artifacts; no separate store |

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

# Diff (text includes AI implications when --ai; JSON machine-readable)
# --ai is the default: writes artifacts/lens/<a>__<b>/implications.json + .md
uv run questline lens diff 1.0.0 1.1.0 --store .questline/store.db
uv run questline lens diff 1.0.0 1.1.0 --format json --no-ai --store .questline/store.db

# Live *model reasoning* (Groq or Ollama). Keys stay in the environment — names only in toml.
uv run questline lens diff 1.0.0 1.1.0 -p ai_groq --store .questline/store.db
uv run questline lens diff 1.0.0 1.1.0 -p ai_ollama --store .questline/store.db

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
uv run pytest tests/test_lens.py tests/test_lens_cli.py tests/test_lens_extra.py tests/test_lens_implications.py tests/test_migrations.py -q --no-cov

# --store FILE puts artifacts next to the DB (FILE's parent / artifacts / lens / …)
# NOT under .questline\ unless the store itself lives there.
Remove-Item .questline-tmp-lens.db, artifacts\lens -Recurse -Force -ErrorAction SilentlyContinue
uv run questline lens snapshot --pack tests/fixtures/lens/pack-a --version 1.0.0 --store .questline-tmp-lens.db
uv run questline lens snapshot --pack tests/fixtures/lens/pack-b --version 1.1.0 --store .questline-tmp-lens.db
uv run questline lens diff 1.0.0 1.1.0 --store .questline-tmp-lens.db
Get-Content artifacts\lens\1.0.0\balance_snapshot.json | Select-Object -First 30
uv run questline lens snapshot --import artifacts\lens\1.1.0\balance_snapshot.json --id reimport-1.1 --store .questline-tmp-lens.db
uv run questline lens diff 1.0.0 reimport-1.1 --store .questline-tmp-lens.db
Get-Content artifacts\lens\1.0.0__reimport-1.1\implications.json | Select-Object -First 40
```

Expect: `+ entity unit_beta`, numeric Δ on `amber_per_tick` / `dps`, curve change, and
an implications artifact (`status: skipped` / `pending: no-provider` without an AI
profile; `status: ok` with `-p ai_groq` or `-p ai_ollama`). Gaps always list
`combat.damage` (and other reserved KPIs). Sessions with `config_snapshot_id=snap-unset`
appear under `measured.unjoined`, not as a silent join.

### Live implications (Groq / Ollama)

Requires phase-11 profiles. **Mistral remains deferred** (no La Plateforme key).
Do not paste keys into chat. See [`ai-setup.md`](ai-setup.md).

```powershell
cd D:\dev\questline
$env:GROQ_API_KEY = "paste-real-key"   # session only
uv run questline lens diff 1.0.0 1.1.0 -p ai_groq --store .questline-tmp-lens.db
uv run questline lens diff 1.0.0 1.1.0 -p ai_ollama --store .questline-tmp-lens.db
```

**Maintainer live (2026-09-10, fixture store):** both profiles returned `status: ok` and
wrote `artifacts\lens\1.0.0__1.1.0\implications.json`. That DB is pack-a vs pack-b —
**no G3 bot sessions**, so gaps correctly include `session_count=0` and reserved KPIs
(`combat.damage`, …). Groq summarized the typed config diff and the telemetry gap.
Ollama `llama3.2` completed the HTTP path (cost 0) but treated gap strings as “missing
KPIs”; use Groq for readable implications. This does **not** retune the game.

To interpret the G3 matrix, import those sessions into the **same** store as real
snapshots and/or set `QUESTLINE_SNAPSHOT_ID` on later bot runs. Until then,
`snap-unset` stays `unjoined`. `lose` is measured play, not a bot fail.
