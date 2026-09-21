# INC-0016: Generate used `expect(x).to_equal` so Launch would AttributeError

- **Date:** 2026-09-21
- **Phases / triggers:** phase-13 HUD Generate (live, after INC-0015 hooks)
- **Status:** fixed
- **Symptom:** Collect passed on a test that called `ensure_in_combat` +
  `get_amber`, then `expect(amber).to_equal(50)` with no `.evaluate()`.
- **Root cause:** Collect does not execute the function body. The Questline
  assertion API is `expect(x).equals(y).evaluate()`. The model used a
  unittest-style `to_equal`. Launch would fail before the amber number.
- **Fix:** Copy-shape + prompt: only `expect(x).equals(y).evaluate()` (or
  `.differs` / `.is_true` / `.is_false`). Never `to_equal`, never omit
  `.evaluate()`.
- **Prevention:** Open `test_gen_*.py` before Launch. Assertions must chain
  `.equals` / `.differs` / `.is_true` / `.is_false` and end with `.evaluate()`.
- **See also:** [INC-0015](INC-0015-hud-generate-skip-instead-of-hooks.md)
