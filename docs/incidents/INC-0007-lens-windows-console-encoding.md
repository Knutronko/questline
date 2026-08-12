# INC-0007: GameLens CLI text crashed on Windows cp1252 console

- **Date:** 2026-08-12
- **Phases / triggers:** FP-G1 (`questline lens diff`)
- **Status:** fixed
- **Symptom:** After a successful `lens snapshot` / `diff`, PowerShell raised
  `UnicodeEncodeError: 'charmap' codec can't encode character '\u2192'` (and would
  also fail on `Δ`) when Typer echoed the human-readable report. Separately,
  maintainers looking under `.questline\artifacts\...` after `--store .questline-tmp-*.db`
  thought snapshots were missing (artifacts live next to the DB file).
- **Root cause:** Diff/render used Unicode arrows/delta glyphs; default Windows
  console encoding is often cp1252. Artifact path confusion: `--store FILE` uses
  `FILE.parent / artifacts / lens / …`, not always `.questline/artifacts/`.
- **Fix:** ASCII-only text render (`->`, `delta`); docs (`gamelens.md`) clarify
  artifact layout beside `--store`.
- **Prevention:**
  - Human-readable CLI output for maintainer-facing commands: prefer ASCII (or
    force UTF-8 explicitly) — do not assume Unicode consoles on Windows.
  - When documenting `--store`, print the path the CLI echoes; never hardcode
    `.questline/artifacts` unless the store lives under `.questline/`.
- **See also:** [gamelens.md](../gamelens.md), PR #25, ADR-0009
