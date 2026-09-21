# INC-0012: Generate gated an existing suite module instead of a new test

- **Date:** 2026-09-21
- **Phases / triggers:** phase-13 HUD Generate → Launch Editor
- **Status:** fixed
- **Symptom:** Spec “Siguiente Nivel / amber 50” collected `suites/test_coverage_demo.py`
  (6 existing tests). Launch Editor ran that module, not a new test from the spec.
- **Root cause:** If `write_file` was missing or unmatched, the collect gate globbed
  `dest/test_*.py` and took the first file alphabetically.
- **Fix:** Assign `WRITE_TEST_TO` (`test_gen_<taskid>.py`) before the model runs.
  Gate only that new file. Never fall back to pre-existing suite tests.
- **Prevention:** HUD file line must be `suites/test_gen_….py`, not `test_coverage_demo.py`
  or another hand-authored module. Collect of 6 functions means the wrong file.
- **See also:** [INC-0011](INC-0011-hud-generate-silent-mockdriver.md)
