# INC-0010: Watchdog `pytest.exit` from a daemon thread during a long live cell

- **Date:** 2026-09-09
- **Phases / triggers:** FP-G3 live matrix (`suites/test_g3_matrix.py`, cell `3-balanced-44`)
- **Status:** open (run still green; warning only)
- **Symptom:** After ~75 live cells, pytest printed
  `PytestUnhandledThreadExceptionWarning: Exception in thread questline-watchdog`
  with `_pytest.outcomes.Exit: questline watchdog fired (exit 140)`.
  The matrix still finished **75 passed** (~1h48).
- **Root cause:** Plugin watchdog default is 120s with no `mark_progress`. A single
  IEB combat can exceed that. `pytest.exit` from the daemon thread does not abort
  the main pytest process (it becomes a thread exception warning).
- **Fix:** not in this close-out. Follow-up: `mark_progress()` on each bot tick /
  Wire call, or a higher timeout on `g3_matrix` / live Editor.
- **Prevention:** Long live suites can warn even when cells pass. Do not treat
  exit 140 in a thread warning as a failed matrix if pytest reports passed.
  Do not Stop Unity mid-cell to “unstick” the watchdog.
- **See also:** [`resilience.md`](../resilience.md), ADR-0006
