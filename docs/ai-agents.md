# Questline AI agents (phase 12)

Test agents for **failing pytest runs**. This is not the GameLens balance
copilot (that is FP-G4: `questline.lens.agent`, HUD `#/lens` Ask).

Operator surface: **questline hud** — **Triage this run** / **Diagnose this test**.
CLI (`questline ai triage|diagnose|heal`) is for CI/scripting.

Setup / keys / budgets: [`ai-setup.md`](ai-setup.md) · [`ADR-0011`](adr/ADR-0011-llmport-budget.md).
Roadmap gates: [`02-AI-ROADMAP.md`](02-AI-ROADMAP.md) §2–3.

## What they do

| Agent | Default | Writes? | Gate |
|-------|---------|---------|------|
| **Triage** | Cluster a finished run | No (hermetic read-only) | Store-owned clusters; model adds hypotheses |
| **Maintainer** | Diagnose one test | Fix is **opt-in** (`--fix` / HUD confirm) | Anti-false-green: the **gate re-runs pytest**; the model claim is logged and ignored |
| **Healer** | Suggest `locators.yaml` | **Never** | Ranking is code (structural + semantic). Human applies the diff |

Structured output (schema v1): `verdict ∈ {diagnosed, fixed, inconclusive, passed}`,
`cause ∈ {test-bug, game-bug, infra, flaky, unknown}`, plus evidence.

A green outcome uses `passed` / `fixed` only when the **runner** said so.

## How to trust (and not trust)

- **Trust** store verdicts, death-point, artifacts, gate `returncode`.
- **Do not trust** the model saying a test is green. HUD shows `gate.accepted`.
- Kill at turn N keeps N−1 on disk (`artifacts/agents/<id>/task.json` + `log.jsonl`).
- Read-only mode strips write tools **and** blocks shell write patterns (`>`, `rm`, …).
- Healer never writes `locators.yaml`.
- Costs: `questline ai costs --run <pytest-run-id>` (`purpose` starts with `agent.`).
- No P1 type/SO names. No auto-PRs. Mistral live smoke remains deferred.

## HUD

On a failed run: **Triage this run**. On a failed test: **Diagnose this test**
(default) and **Fix this test** (confirm). ElementNotFound: **Suggest locator**.
Disabled in `--read-only`. CSRF + localhost, same as Ask.

## CLI (extra)

```powershell
uv run questline ai triage RUN_ID -p ai_groq
uv run questline ai diagnose RUN_ID TEST_ID -p ai_groq
uv run questline ai diagnose RUN_ID TEST_ID --fix --flaky-guard
uv run questline ai heal RUN_ID --test TEST_ID
uv run questline ai costs --run RUN_ID
```

`--fix` accepts a patch only if the gate’s pytest re-run is green (twice with
`--flaky-guard`).

## Budgets

Per-task turn cap (default 8; triage 6; healer 4). A greedy test in a batch
cannot spend another test’s turns. USD ceilings are still ADR-0011
(`BudgetExceededError`).

## Store

Migration **8** adds `agent_tasks`. Artifacts under `artifacts/agents/<id>/`.
GameLens turns stay in `lens_agent_turns` (migration 7).

Spec→test, unit-gen, and the eval harness are **phase 13** — [`ai-eval.md`](ai-eval.md).
