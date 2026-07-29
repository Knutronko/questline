# Phase 12 — AI agents: kernel, triage, maintainer, self-healing locators

> Session preamble: see `phase-00-bootstrap.md`. Read `docs/02-AI-ROADMAP.md §2–3`
> carefully — the gates there are the whole point of this phase.

## Context
Phases 00–11 merged. LLM layer with routing/budgets/cost ledger works.

## Objective
The agent kernel plus three agents: run triage (read-only), maintainer (diagnose/fix with
anti-false-green gate), and locator self-healing (suggest-only).

## In scope
1. **Agent kernel** (`ai/agents/kernel.py`): tool-use loop over LLMPort with:
   - allow-listed tools per agent (read_file, grep_scoped, run_test, read_screenshot →
     image block, hierarchy_snapshot, store_query; write tools only where stated);
   - **per-task turn budget** with explicit task boundaries (multi-test batch: each test
     gets its budget; one greedy task cannot starve the rest — unit-tested);
   - **incremental persistence**: every intermediate artifact (diagnosis, patch, tool log)
     written to store as produced; kill-at-turn-N test preserves N−1;
   - hermetic **read-only mode**: write tools removed AND shell-style tools guarded against
     write patterns; verified by a test that instructs the model (scripted fake) to write;
   - structured output: versioned JSON schema, `verdict ∈ {diagnosed, fixed, inconclusive,
     passed}`, `cause ∈ {test-bug, game-bug, infra, flaky, unknown}`, evidence list.
2. **Triage agent** (`ai/agents/triage.py`): input = finished run (verdicts, signatures,
   events) + optional git diff since last green; output = failure clusters with shared
   root-cause hypothesis, infra/test/game split, suspect changes ranked; renders a digest
   through ReporterPort (Slack thread + HTML section). Read-only mode enforced.
3. **Maintainer agent** (`ai/agents/maintainer.py`): one failing test at a time;
   - diagnose-only default; fix mode opt-in per invocation;
   - screenshot-first workflow (image block before hierarchy text);
   - **anti-false-green gate**: a fix is accepted ONLY if the gate re-runs the test itself
     and the parsed runner result is green; the agent's own claim is logged but ignored;
   - flaky guard: gate re-runs green fixes twice when configured;
   - quarantine proposals go through the ledger API (never marker edits).
4. **Self-healing locators** (`ai/agents/healer.py`): on ElementNotFound artifacts —
   structural+semantic candidate ranking against the hierarchy snapshot; output = suggested
   `locators.yaml` diff + confidence; never writes; `questline ai heal <run>` CLI.
5. **HUD hooks**: buttons on a failed run/test — "Triage this run", "Diagnose this test"
   (results attached to the run in store, visible in HUD).
6. Docs: `docs/ai-agents.md` — capabilities, gates, budgets, how to trust (and not trust)
   outputs.

## Out of scope
Test generation, unit-test generation, eval harness (Phase 13).

## Acceptance criteria
- [ ] CI (scripted fake LLM — deterministic tool-call sequences): kernel budget tests,
      kill-at-turn-N persistence, hermetic read-only test, false-green rejection test
      (fake model claims success, gate re-run says red → fix rejected, verdict
      `inconclusive`).
- [ ] Maintainer-checked (live, MockDriver broken-on-purpose suite): maintainer diagnoses
      a seeded locator bug and a seeded assertion bug; fix mode repairs at least one with
      gate-verified green; triage clusters a 5-failure run into ≥2 correct groups;
      healer suggests the correct locator for a renamed element.
- [ ] All live-run costs visible per agent in `questline ai costs`.

## PR checklist
Title `phase-12: ai agents`. Update `docs/02-AI-ROADMAP.md` status column.
