# INC-0004: Smoke HUD on :8741 shadowed real `questline hud` (Windows)

- **Date:** 2026-08-11
- **Phases / triggers:** 10 (HUD II operator dogfood)
- **Status:** fixed
- **Symptom:** Launch “Wire Editor” still showed Live events `smoke::test_launch`
  and Runs only fixture `run-a`/`run-b`. Operator believed they were on the real HUD.
- **Root cause:**
  1. `scripts/serve_hud_smoke.py` defaulted to port **8741** (same as `questline hud`)
     and kept running after Playwright sessions.
  2. `questline hud` echoed a Unicode arrow (`→`) and crashed under Windows cp1252,
     so a restart attempt failed while smoke kept serving.
- **Fix:** Smoke defaults to **8742**, sets `meta.smoke=true` + SPA banner; CLI echo
  uses ASCII `->`.
- **Prevention:**
  - Before operator dogfood, confirm `GET /api/meta` → `smoke: false` and
    `project_root` is the repo (not `.questline-hud-smoke`).
  - Never leave `serve_hud_smoke.py` on 8741; use 8742 for Playwright only.
  - Avoid non-ASCII in CLI prints that run on Windows consoles.
- **See also:** INC-0003, [`hud-operator-guide.md`](../hud-operator-guide.md)
