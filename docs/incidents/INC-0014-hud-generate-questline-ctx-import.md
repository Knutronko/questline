# INC-0014: Generate wrote `from questline_ctx import` so collect failed

- **Date:** 2026-09-21
- **Phases / triggers:** phase-13 HUD Generate (live Groq, game `pages/`)
- **Status:** fixed
- **Symptom:** `suites/test_gen_….py` collected with
  `ModuleNotFoundError: No module named 'questline_ctx'`. Gate stayed
  `inconclusive` (`executed=false`). Task summary: turn budget reached.
- **Root cause:** The generator prompt said “prefer `questline_ctx`, Tap,
  WaitFor, expect”. The model treated `questline_ctx` as a module and skipped
  reading `pages/`. `questline_ctx` is a pytest fixture (`Context`), not an
  import. Game pages take `SomePage(questline_ctx)`. UI tap methods are
  deferred until Poco.
- **Fix:** Inject PAGE_METHODS / import shape from `pages/` + `locators.yaml`
  + existing suite headers. Prompt: never `from questline_ctx import …`.
  write_file from that inventory, then JSON (no extra listing turns).
- **Prevention:** Collect must import. A `ModuleNotFoundError` on
  `questline_ctx` means the model invented imports — Generate again after this
  fix (new `test_gen_*.py`). Do not Launch that file.
- **See also:** [INC-0012](INC-0012-hud-generate-existing-suite-file.md),
  [INC-0013](INC-0013-hud-generate-groq-429.md)
