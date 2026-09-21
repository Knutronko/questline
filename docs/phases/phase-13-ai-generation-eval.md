# Phase 13 — AI generation + evaluation harness

> Session preamble: see `phase-00-bootstrap.md`. Read `docs/02-AI-ROADMAP.md §3.4–3.6`.
> The eval harness is the flagship deliverable of the AI layer — budget your effort
> accordingly (generator: adequate; harness: excellent).

## Context
Phases 00–12 merged. Agents run gated; costs ledgered.

## Objective
Two generators (scenario tests, framework unit tests) and the **evaluation harness** that
measures every agent with reproducible metrics.

## In scope
1. **Test generator** (`ai/agents/generator.py`): input = Markdown/plain-text spec
   ("when the player buys the starter pack, coins increase…"); output = a test file using
   the authoring layer + existing pages/locators; unknown pages/locators become explicit
   TODO stubs with hierarchy-assisted locator suggestions (from a live snapshot when
   available). **Gate**: the generated test must execute — green, or red with the failure
   matching the spec's expectation — before the generator reports success. Includes
   `--rebuild <test_id>` mode (regenerate a flaky test from its own history + spec).
2. **Unit-test generator** (`ai/agents/unit_gen.py`): target a framework module → proposes
   pytest tests; runs them; reports coverage delta; output lands as a patch for human
   review (never auto-commit).
3. **Eval harness** (`ai/evalharness/`):
   - **Golden set format** (`goldens/*.yaml`): {broken test or scenario, ground-truth cause,
     expected fix class, setup script} — seeded with ≥10 cases built on the MockDriver fake
     game (locator renames, timing bugs, assertion bugs, infra simulations, real green);
   - runner: `questline ai eval [--agent] [--provider] [--prompt-version]` executes the
     matrix, computing: diagnosis accuracy, fix correctness (gate-green AND matching
     expected class), false-green rate, iterations-to-converge, cost per task;
   - results → store (`eval_results`) + JSON export; comparison report between two
     configurations (model A vs B, prompt v1 vs v2);
   - HUD panel: eval history, metric trends, config comparison table;
   - optional exporters: DeepEval/Langfuse formats (stub acceptable, documented).
4. Docs: `docs/ai-eval.md` — how to add a golden, how to read the metrics, honest-limits
   section (n, variance, what these numbers do and don't claim).

## Out of scope
MCP server (`questline mcp` = FP-A1; `unity mcp` = QL-8 / not this phase), flakiness predictor, visual regression (BACKLOG.md).

## Acceptance criteria
- [x] CI (fake LLM): generator gate test — generated test that fails to execute is
      reported as failure, never written as success; unit-gen patch flow works.
- [x] Golden set: ≥10 cases across ≥4 failure classes, each reproducible offline.
- [ ] Maintainer-checked (live): full eval run on the golden set with 2 providers →
      comparison report renders; false-green rate correctly catches a sabotaged gate
      (test fixture where the gate is bypassed → metric flags it). **Deferred** (same
      as Mistral live smoke) — CI uses FakeProvider; sabotage golden is covered offline.
- [x] `questline ai eval` results appear in HUD.
- [x] Spec→test demo: a 5-line spec produces a running test against the MockDriver game.
- [x] Live Generate (2026-09-21): HUD `--project-root` at ElJuegaso `automation/`,
      spec Siguiente Nivel / Amber 50 → `suites/test_gen_4a18993bcece48f7.py` →
      Launch Editor → `RunFinished passed` (measured `get_amber()==50`).

## PR checklist
Title `phase-13: ai generation + eval harness`. Update AI-ROADMAP status.

## Self-review (this PR)

- Generator success is owned by pytest execution (`executed` + `expect:` match). A model
  `passed` claim on a file that does not collect stays `inconclusive`.
- Eval goldens are MockDriver (shop/coins/HUD), not P1 types/SOs. Sabotage golden must
  flag `false_green`.
- HUD Eval is the operator path; CLI is extra. HUD still does not import
  `questline.ai.factory` / `cursor_cli`.
- Unit-gen never auto-commits.
- Live two-provider eval is maintainer-checked (`questline ai eval --live`), not CI.
- **Incidents:** INC-0011 (silent MockDriver when game toml has no AI profile);
  INC-0012 (Generate must write `test_gen_*.py`, never gate an existing suite file);
  INC-0013 (Groq HTTP 429 is rate limit — retry / wait, not “no pytest file”);
  INC-0014 (`questline_ctx` is a fixture, not `from questline_ctx import`);
  INC-0015 (Generate must use listed Page hooks, not `pytest.skip` for “tap”);
  INC-0016 (`expect(x).equals(y).evaluate()`, not `to_equal`)
- **Verified in HUD:** Eval table (`eval-a`/`eval-b`) + Compare B−A. **Generate**
  Demo execute (Playwright; Launch buttons absent on smoke). Collect gate +
  launcher argv (TestClient). **Live Editor 2026-09-21:** Generate (Demo off) →
  `suites/test_gen_4a18993bcece48f7.py` → Launch Editor → `TestFinished` +
  `RunFinished passed` (Amber 50 measured). Collect ≠ live green. MockDriver
  files do not show Launch Editor.

## Lessons / incidents

- [INC-0011](../incidents/INC-0011-hud-generate-silent-mockdriver.md) — game
  `questline.toml` without `[profile.ai_groq]` must not fall back to Demo.
  `GROQ_API_KEY` in the HUD process is enough; Unity does not move for MockDriver.
- [INC-0012](../incidents/INC-0012-hud-generate-existing-suite-file.md) — Generate
  writes `test_gen_<id>.py`. Collect of an existing suite module is not success.
- [INC-0013](../incidents/INC-0013-hud-generate-groq-429.md) — Groq HTTP 429 is
  quota. Wait ~20s and Generate again (or Ollama); do not treat it as a missing
  write_file.
- [INC-0014](../incidents/INC-0014-hud-generate-questline-ctx-import.md) —
  `questline_ctx` is a pytest fixture. Collect of `from questline_ctx import`
  is not success.
- [INC-0015](../incidents/INC-0015-hud-generate-skip-instead-of-hooks.md) —
  Collect of a skip-only test is not the spec. Use listed hooks, not deferred UI taps.
- [INC-0016](../incidents/INC-0016-hud-generate-expect-to-equal.md) —
  Collect does not run `expect`. `to_equal` without `.evaluate()` fails on
  Launch. Use `expect(x).equals(y).evaluate()`.

