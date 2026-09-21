# INC-0011: HUD Generate silent MockDriver when game toml has no AI profile

- **Date:** 2026-09-21
- **Phases / triggers:** phase-13 Generate → Launch Editor (HUD `--project-root` at game `automation/`)
- **Status:** fixed
- **Symptom:** Generate reported `verdict=passed · mode=collect · accepted=true` and
  wrote `suites/test_from_spec.py`. Launch Editor ran, Unity Play did not move.
- **Root cause:**
  1. Game `questline.toml` has `editor` / `android_local` only — no `[profile.ai_groq]`.
  2. `build_hud_router` required that profile and returned `None`.
  3. Generate with Demo unchecked **fell back** to canned MockDriver instead of 400.
  4. MockDriver tests do not use `questline_ctx`, so pytest never opens Wire.
     Collect `green=true` is not a live Unity run.
- **Fix:** Env `GROQ_API_KEY` on the HUD process is enough (no AI table required in
  the game toml). Live Generate without an LLM returns 400. Demo never writes into
  `suites/` when `pages/` exist. Launch Editor/Android is hidden for MockDriver files.
- **Prevention:**
  - Summary “canned MockDriver” / `mock_driver=true` means Unity will not move.
  - Restart `questline hud` after setting `GROQ_API_KEY` in that shell.
  - Live steps must match existing pages/hooks (Ping), not the mock “tap Play / coins”.
- **See also:** [`hud-user-guide.md`](../hud-user-guide.md) §Generate, [`ai-eval.md`](../ai-eval.md)
