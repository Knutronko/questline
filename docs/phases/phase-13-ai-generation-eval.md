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
MCP server, flakiness predictor, visual regression (BACKLOG.md).

## Acceptance criteria
- [ ] CI (fake LLM): generator gate test — generated test that fails to execute is
      reported as failure, never written as success; unit-gen patch flow works.
- [ ] Golden set: ≥10 cases across ≥4 failure classes, each reproducible offline.
- [ ] Maintainer-checked (live): full eval run on the golden set with 2 providers →
      comparison report renders; false-green rate correctly catches a sabotaged gate
      (test fixture where the gate is bypassed → metric flags it).
- [ ] `questline ai eval` results appear in HUD.
- [ ] Spec→test demo: a 5-line spec produces a running test against the MockDriver game.

## PR checklist
Title `phase-13: ai generation + eval harness`. Update AI-ROADMAP status.
