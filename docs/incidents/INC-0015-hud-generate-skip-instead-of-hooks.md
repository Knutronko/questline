# INC-0015: Generate skipped the spec instead of using listed Page hooks

- **Date:** 2026-09-21
- **Phases / triggers:** phase-13 HUD Generate (live, game `pages/`)
- **Status:** fixed
- **Symptom:** Collect passed on `test_gen_….py` whose body was
  `pytest.skip` (“deferred tap”). Spec was combat loaded + amber amount.
  Launch would skip, not call `ensure_in_combat` / `get_amber`.
- **Root cause:** The prompt treated deferred UI as “skip or fail”. The model
  matched “tap” to a Poco method and skipped the whole test instead of the
  listed hooks that implement the **outcome** (load combat, read amber).
- **Fix:** HOOKS_FIRST in the generator user prefix + prompt: implement the
  spec with PAGE_METHODS; do not skip when a hook matches; 1-based level N →
  `level_index=N-1`. Deferred UI: do not call it, use the hook equivalent.
- **Prevention:** Collect of a skip-only test is not spec coverage. Open the
  `test_gen_*.py` before Launch: it must call listed hooks, not `pytest.skip`.
- **See also:** [INC-0014](INC-0014-hud-generate-questline-ctx-import.md)
