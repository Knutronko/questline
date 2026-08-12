# Phase 11 — AI foundation: providers, router, cost ledger

> Session preamble: see `phase-00-bootstrap.md`. Read `docs/01-ARCHITECTURE.md §3.5`
> and `docs/02-AI-ROADMAP.md §1`.

## Context
Phases 00–10 merged (07/09/10 not strictly required — this phase depends on 01 only,
parallelizable). No AI code exists.

**Scheduling note (2026-08-12):** for *balance automation*, prefer completing
**FP-G1 → FP-G2 → FP-G3** (deterministic bots collecting measured data) before leaning
on this phase for GameLens AI reports or AI bot policies. See
[`BALANCE-AUTOMATION.md`](../BALANCE-AUTOMATION.md). This brief itself remains valid
anytime LLMPort is needed.

## Objective
A provider-agnostic LLM layer with fallback routing, hard budget caps and per-call cost
accounting — the substrate for every agent in Phases 12–13.

## In scope
1. **LLMPort** (`ai/port.py`): `LlmRequest` (system, messages, tools?, images?,
   max_tokens, temperature, purpose_tag), `LlmResponse` (text, tool_calls, usage);
   provider metadata (name, model, pricing table).
2. **Adapters** (`ai/providers/`, extra `questline[ai]`):
   - `OpenAICompatProvider`: base_url + key + model — one adapter covers Mistral
     (free tier, primary), Groq, OpenRouter, any OpenAI-style endpoint.
   - `OllamaProvider`: local models, zero cost.
   - `AnthropicProvider`: thin, native message format + image blocks.
   - `CursorCliProvider` (experimental, clearly labeled): subprocess to `cursor-agent`
     in print mode; documented limitations; nothing core may depend on it (enforced by
     an import-linter rule).
3. **ProviderRouter** (`ai/router.py`): ordered candidates from config; fallback on
   rate-limit/5xx/timeout with backoff; **budget caps**: per-call and per-run cost ceilings
   from config — exceeding = hard `BudgetExceededError`, never a warning; model classes
   (`fast` vs `strong`) resolvable per task.
4. **Cost ledger**: every call → `ai_calls` store row {provider, model, tokens in/out,
   cached flag, est. cost from versioned pricing file, purpose_tag, duration, outcome};
   `questline ai costs [--run]` CLI summary; HUD viewer table (small addition).
5. **Prompt store** (`ai/prompts/`): versioned prompt files, loaded by name+version;
   stable-prefix composition helper (cache-friendly ordering documented).
6. **Doctor**: `questline doctor` extended — checks configured providers with a 1-token
   ping, reports which are usable (keys via env only).
7. Docs: `docs/ai-setup.md` — getting free-tier keys (Mistral/Groq), Ollama setup,
   budget config, provider table with the "tiers churn — recheck" warning.

## Out of scope
Agents, tool-use loop (Phase 12), eval harness (Phase 13).

## Acceptance criteria
- [ ] CI: adapters green against recorded/fake transports; router fallback + budget-cap
      unit tests; no live keys in CI.
- [ ] Maintainer-checked: live smoke — same `LlmRequest` answered via Mistral, Groq,
      Ollama by flipping profile only; costs ledgered for all three (Ollama = 0).
- [ ] Rate-limit simulation: primary 429s → router falls to secondary → call succeeds,
      both attempts ledgered.
- [ ] `BudgetExceededError` fires at the configured ceiling in a scripted loop.
- [ ] Import-linter rule: `ai/providers/cursor_cli` imported by nothing in core/agents.

## PR checklist
Title `phase-11: ai foundation`. ADR-0007 (provider-agnostic design + budget policy).
