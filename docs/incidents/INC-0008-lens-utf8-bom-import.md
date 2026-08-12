# INC-0008: Unity GameLens export UTF-8 BOM broke `lens snapshot --import`

- **Date:** 2026-08-12
- **Phases / triggers:** FP-G1 / QL-5 (`questline lens snapshot --import`)
- **Status:** fixed
- **Symptom:** Editor **Questline → Export Balance Snapshot** wrote
  `balance_snapshot.json` that Python rejected:
  `Unexpected UTF-8 BOM (decode using utf-8-sig)`.
- **Root cause:** `File.WriteAllText(..., Encoding.UTF8)` in .NET emits a UTF-8
  BOM (`EF BB BF`). `json.loads` + `read_text(encoding="utf-8")` does not strip it.
- **Fix:** Companion writes UTF-8 **without** BOM (`new UTF8Encoding(false)`).
  Python `load_snapshot` / `load_manifest` / pack JSON use `utf-8-sig` so older
  BOM exports still import.
- **Prevention:** Never use `Encoding.UTF8` for files consumed by Python `json`
  on Windows; prefer `UTF8Encoding(false)`. JSON loaders that ingest Unity
  exports should use `utf-8-sig`.
- **See also:** [gamelens.md](../gamelens.md), ADR-0009, INC-0007
