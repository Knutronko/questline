# Questline — AI Roadmap

The AI layer is the differentiator of the project. This document catalogs every AI feature,
its gate (what stops it from lying), its data, and its build phase. Design rules inherited
from `00-MASTER-PLAN.md §3` — especially rule 4 (verdicts from artifacts, never from model
claims) and rule 7 (incremental persistence + cost per call).

---

## 1. Foundation (Phase 11)

- **LLMPort + adapters**: OpenAI-compatible (Mistral free tier primary, Groq secondary,
  OpenRouter), Ollama (offline/zero-cost), Anthropic (thin), Cursor CLI (experimental).
- **ProviderRouter**: fallback chain on rate limit/outage; per-call and per-run budget caps
  (hard stop, not warning); model selection per task class (cheap model for classification,
  strong model for repair).
- **Cost ledger**: every call → `ai_calls` row (provider, model, tokens, cost estimate,
  purpose, duration, cache hit). HUD shows cost per run/agent/feature. Cost is a first-class
  metric from day 1, not an afterthought.
- **Prompt hygiene**: versioned prompt files; stable-prefix ordering for provider-side
  caching; screenshots as native image blocks (agents must never "read" a base64 string).

## 2. Agent kernel (Phase 12)

Shared loop for all agents:
- Allow-listed tools per agent (read_file, grep, run_test, read_screenshot, hierarchy, …).
- **Per-task turn budget** with an explicit task-boundary signal — one greedy task can never
  starve the rest of a batch.
- **Incremental persistence**: each diagnosis/patch/intermediate artifact is written as it is
  produced. Death at turn N preserves everything before N.
- Structured output contract (JSON schema, versioned): `verdict ∈ {diagnosed, fixed,
  inconclusive, passed}` + `cause ∈ {test-bug, game-bug, infra, flaky, unknown}` + evidence.
  A green outcome has its own verdict value — greens are never forced into failure buckets.

## 3. The agents

### 3.1 Run triage agent (Phase 12)
Input: a finished run (events, verdicts, error signatures) + optional change context
(git diff of tests/game since last green). Output: failure clusters ("these 7 share one
cause"), infra/test/game classification per cluster, suspect-change ranking, and a
human-readable digest posted via ReporterPort (Slack thread). Read-only by design.
*This alone removes the biggest daily time sink of run babysitting.*

### 3.2 Maintainer agent (Phase 12)
Modes: **diagnose-only** (default, hermetic — write-tools removed AND write-patterns in
shell tools blocked) and **fix** (patch + re-run). The anti-false-green gate: a fix is
accepted only when the gate itself re-runs the test and parses the runner result — the
agent's claim is never the verdict. Screenshot-first diagnosis (vision). Quarantine-aware:
can propose symmetric quarantine entry/exit through the ledger tooling, never by editing
markers directly.

### 3.3 Locator self-healing (Phase 12)
On ElementNotFound: diff the expected locator against the live hierarchy snapshot, rank
candidate locators (structural + semantic similarity), emit a suggested `locators.yaml`
diff. Human approves. Metric: healing suggestion acceptance rate.

### 3.4 Test generation (Phase 13)
Spec (Markdown/plain text) → test code using the authoring layer and existing pages;
missing pages/locators are generated as explicit TODOs with hierarchy-assisted suggestions.
Gate: generated test must execute (green, or red for the *stated* reason) before it can be
committed. Includes a "rebuild this flaky test" mode.

### 3.5 Unit-test generation for the framework itself (Phase 13)
Agent proposes pytest unit tests for core modules; coverage delta measured; human reviews.
Dogfood value: the framework's own CI consumes its own AI.

### 3.6 Eval harness (Phase 13) — the flagship
A benchmark that measures the agents, built on a **golden set**: intentionally broken tests
(and/or historical bugs) with known root causes and known-good fixes.
Metrics per agent/model/prompt version:
1. **Diagnosis accuracy** (cause matches ground truth)
2. **Fix correctness** (gate-green AND matches expected fix class)
3. **False-green rate** (fix accepted that shouldn't have been)
4. **Iterations-to-converge** and **cost per task**
Runs as `questline ai eval`; results in the store; HUD panel with model-vs-model and
prompt-version-vs-version comparisons. Optional integration: DeepEval/Langfuse exporters.
*This turns "I built agents" into "I built agents and I can prove how good they are" —
the strongest possible portfolio artifact for AI Quality / LLM Evaluation roles.*

## 4. Later candidates (see `03-FUTURE-PHASES.md` for the full catalog)

- **GameLens implications report (FP-G1)**: balance-config diff between game versions →
  AI report of gameplay implications (per-change effects, cross-system interactions, risk
  flags). Framing rule: model reasoning is labeled as such; measured telemetry (FP-G2/G3)
  is labeled *measured* — the report never blends the two silently.
- **Design copilot (FP-G4)**: RAG chat over balance snapshots + telemetry + reports.
- **AI crash triage (FP-T6)**: dedupe + suspect-area analysis of monkey-run crashes.
- **MCP server (FP-A1)**: expose run/query/triage/GameLens as MCP tools. High keyword value.
- **Nightly auto-triage pipeline (FP-A2)**: scheduled run → triage digest → issues filed.
- **Flakiness predictor (FP-A3)**: classic ML (no LLM) over run-store history.
- **Self-healing auto-PR mode (FP-A4)**: agents open PRs autonomously only after the eval
  harness proves them above quality thresholds — the harness gates agent autonomy.
- **Visual regression assist (FP-T3)**: screenshot diffing with LLM intentionality judgment.
- **Perf anomaly detection**: threshold learning from PerfProbe series history.

## 5. Free-tier operating notes (2026-07 state — recheck quarterly, tiers churn)

| Provider | Free tier | Role |
|---|---|---|
| Mistral La Plateforme | ~1B tokens/month | Primary (agents) |
| Groq | Llama 3.3 70B, ~30 RPM / 1k req/day | Secondary / fast classification |
| Gemini API | ~10–15 RPM Flash | Tertiary |
| GitHub Models | daily limits, many models | Experiments |
| Ollama (local) | unlimited, weaker models | Offline demos, CI smoke |
| Cursor CLI | uses Cursor Pro credits | Experimental adapter only |
