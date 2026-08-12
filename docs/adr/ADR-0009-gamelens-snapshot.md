# ADR-0009: GameLens balance snapshot schema & store

- **Status:** accepted (implemented in **FP-G1**)
- **Context:** FP-G1 ships genre-agnostic balance **snapshot + typed diff** driven by a
  game-declared manifest (QL-5). Snapshots must persist beside the run store (ADR-0002),
  be CI-testable without Unity, and never hardcode reference-game type names in
  `src/questline`. AI implications report is deferred until phase-11 (LLMPort).
- **Decision:**
  1. **Manifest (game declares WHAT):** JSON document `schema_version: 1` with
     `entries[]` (`id`, `system` tag, `asset_path` and/or `source_file`) and optional
     `supplementary[]` (markdown/csv paths — context only, not numerically diffed).
     Optional companion attribute may mark SOs; the authoritative export set is the
     manifest asset/file. Questline core never embeds ElJuegaso (or any game) type names.
  2. **Normalized snapshot JSON** (`balance_snapshot.json`, `schema_version: 1`):
     - `meta`: `game_version`, optional `git_commit` / `feature_id`, `captured_at`
     - `entities`: map `id → { id, system, kind, fields }`
     - Field shapes: `number` | `string` | `bool` | `curve` (list of `[t,v]` or
       keyed points) | `series` (list of numbers) | `object` (nested fields) |
       `null`
     - Stable key paths: entity id + dotted field path (e.g. `hp.max`)
  3. **Store (ADR-0002 migration 3):** table `balance_snapshots`
     (`id`, `game_version`, `git_commit`, `feature_id`, `artifact_path`, `created_at`,
     `meta` JSON). Artifact file under `.questline/artifacts/lens/<id>/balance_snapshot.json`.
     CLI keys `diff <vA> <vB>` resolve by snapshot `id` or by `game_version` (latest).
  4. **Diff kinds (first-class):** `changed` (numeric Δ + %, string/bool),
     `added_entity`, `removed_entity`, `curve_changed` / `series_changed`. Group by
     manifest `system` tags. Optional `feature_id` on snapshots for future FP-F impact.
  5. **Capture paths:** (a) Companion Editor / `QUESTLINE_DEV` exporter writes normalized
     JSON from SOs listed in the manifest; (b) Python CLI imports a fixture pack or
     pre-exported snapshot without Unity (CI happy path).
  6. **AI report:** interface + stub returning `pending phase-11`; no live LLM in FP-G1.
- **Consequences:**
  - QL-5 must ship a real manifest matching this schema; FP-G1 owns format + tooling.
  - HUD GameLens panel deferred; CLI is the MVP surface.
  - FP-G2/G3 reuse `game_version` / `feature_id` / snapshot id as config truth keys.
- **Alternatives considered:** Diff raw Unity YAML (rejected — unstable). Store only
  as run artifacts without a table (rejected — hard to query by version). Hardcode P1
  SO type list in core (rejected — GAME-INTEGRATION §5).
