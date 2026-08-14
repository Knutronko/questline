# INC-0009: Hatch `force-include` duplicated HUD static in the wheel

- **Date:** 2026-08-14
- **Phases / triggers:** FP-G3 live Editor (`uv run pytest` from ElJuegaso `automation/`)
- **Status:** fixed
- **Symptom:** `uv run pytest` never started Unity tests. uv tried to build the
  questline git pin as a wheel and hatch failed:

  `ValueError: A second file is being added to the wheel archive at the same path:
  questline/hud/static/index.html`

  The most likely cause cited `tool.hatch.build.targets.wheel.force-include`.
- **Root cause:** `src/questline/hud/static` (and Slack templates) already ship via
  hatch src-layout. `force-include` copied the same paths again. Editable installs
  from disk (`uv pip install -e D:\dev\questline`) skip the wheel and work; `uv run`
  without `--no-sync` rebuilds from the git pin and dies.
- **Fix:** drop the duplicate `force-include` entries. ADR-0007 now says src-layout
  is enough. ElJuegaso `automation/` live commands use `uv run --no-sync` after an
  editable local install so a stale git pin cannot rebuild the broken wheel.
- **Prevention:** never `force-include` paths already under `src/<package>/`. After
  hatch/package layout changes, `uv build` (or install from a git URL) must succeed
  — editable-only CI does not catch this. Game `automation/` that pins questline
  from git should `uv run --no-sync` when dogfooding a local clone.
- **See also:** [ADR-0007](../adr/ADR-0007-hud-frontend-stack.md),
  ElJuegaso `automation/README.md`
