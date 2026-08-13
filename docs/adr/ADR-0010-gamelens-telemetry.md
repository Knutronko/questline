# ADR-0010: GameLens thin telemetry schema & store

- **Status:** accepted (implemented in **FP-G2**)
- **Context:** FP-G2 ships genre-agnostic **measured truth**: a thin event API in
  `com.questline.companion`, JSON spools, and store tables beside the run store
  (ADR-0002). Sessions must share GameLens keys with FP-G1 (`game_version`,
  optional `feature_id`, `config_snapshot_id`). AI must not invent numbers.
  ADR-0009 is the snapshot/diff schema — **do not reuse it**.
- **Decision:**
  1. **Event catalog (thin):** dotted lowercase names — `session.start`,
     `session.end`, `session.checkpoint`, `currency.earned`, `currency.spent`,
     `unit.deployed`, `combat.leak`, `wave.started`, `wave.completed`,
     `skill.cast`, `repair.applied`. Ids (`currency_id`, `unit_id`, `skill_id`,
     checkpoint `label`) are opaque game strings. Core never embeds reference-game
     type names.
  2. **Unknown names:** ingest and store (forward-compatible). Session summary
     rollup uses only the thin catalog. Reserved later names (D12 / G2+) live in
     `questline.telemetry.schema.FUTURE_EVENT_NAMES` (`combat.damage`,
     `projectile.*`, `creature.grown`, `buff.picked` / `buff.skipped`,
     `unit.relocated`, `session.revive`, `enemy.spawn`) — later phases **reuse
     these strings**, they do not invent a parallel vocabulary.
  3. **Spool JSON** `schema_version: 1`: `{ session, events[] }` with `seq`, `t`
     (seconds from session start), `name`, `payload`. UTF-8 **without BOM** on
     write; Python reads `utf-8-sig` (INC-0008).
  4. **Store (migration 4):** `telemetry_sessions` + `telemetry_events`. Do not
     reuse run-store `events` (framework traffic). Artifact
     `{artifacts_dir}/telemetry/<id>/spool.json`. Same `--store FILE` artifacts
     rule as `lens`. Re-import of the same session id **replaces**.
  5. **Envelope keys:** `game_version` (required at ingest), optional
     `git_commit`, `feature_id`, `config_snapshot_id` (GameLens snapshot id, no
     FK), `policy_id` (NULL until FP-G3), `seed` (TEXT), `source`
     (`wire` | `spool` | `import`), optional `run_id`.
  6. **Transport:** no Wire `op` / protocol bump. Companion in-memory ring
     (10 000, drop-oldest) drained via hooks `DrainTelemetry` (max 500/call),
     `BeginTelemetrySession` / `SetTelemetryContext` / `EndTelemetrySession` /
     `TelemetryStatus`. Manual play writes a spool under
     `persistentDataPath/questline_telemetry/`. Python helper
     `questline.telemetry.drain.drain_telemetry`.
  7. **CLI:** `questline telemetry import` / `query` (not under `lens`).
     ASCII-only human text (INC-0007).
  8. **HUD:** telemetry view **deferred** (CLI MVP), same pattern as GameLens.
  9. **Summaries:** computed at ingest from events (counts, currency net, first
     leak `t`, waves, duration, outcome, checkpoint labels). Measured facts only.
- **Consequences:**
  - QL-6 maps game debug events onto this catalog (game repo). Questline fixtures
    stay generic.
  - FP-G3 must set `policy_id` + `seed` + `config_snapshot_id` via
    `SetTelemetryContext` / `BeginTelemetrySession` and drain after the session.
  - phase-11 GameLens AI report reads `telemetry_sessions.summary` as *measured*;
    it never fills missing KPIs.
  - D12 / richer G2+ **appends** `FUTURE_EVENT_NAMES` (and summary fields) via a
    new migration if the summary shape must change — do not rewrite migration 4.
- **Alternatives considered:** New Wire op (rejected — protocol bump for a hook
  drain). Store only as run `events` rows (rejected — mixed with framework
  traffic, hard to query by snapshot/policy). Hardcode P1 event names in core
  (rejected — GAME-INTEGRATION §5).
