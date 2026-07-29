# ADR-0002: SQLite run store + JSONL ledger mirror

- **Status:** accepted (phase-01)
- **Context:** The kernel must persist runs incrementally (kill-safe) and remain
  grep-friendly for local debugging, without external services. Future modules
  (feature registry, telemetry, eval) will add tables without a store rewrite.
- **Decision:** One SQLite file per project (`.questline/store.db`) is the source of
  truth for structured queries (runs/tests/steps/events/…). An append-only JSONL
  mirror (`.questline/ledger.jsonl`) is written in the same transaction path for
  flat, tool-friendly inspection. Artifacts live on disk under `.questline/artifacts/`.
  Schema evolution uses a `schema_version` table and ordered migrations applied on
  open (`questline.core.migrations`).
- **Consequences:** Reporters/HUD/AI read SQLite; operators can `tail`/`jq` the ledger.
  Dual-write adds a small I/O cost; ledger is not rebuilt automatically if truncated.
  New tables ship as new migration versions — never by mutating migration 1 in place.
