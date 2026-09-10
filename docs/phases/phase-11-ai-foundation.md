# Phase 11 — AI foundation: providers, router, cost ledger

> Session preamble: see `phase-00-bootstrap.md`. Read `docs/01-ARCHITECTURE.md §3.5`
> and `docs/02-AI-ROADMAP.md §1`.

## Context
Phases 00–10 merged (07/09/10 not strictly required — this phase depends on 01 only,
parallelizable). No AI code exists.

**Scheduling note (2026-08-12, telemetry contract 2026-08-13):** for *balance
automation*, prefer completing **FP-G1 → FP-G2 → FP-G3** before leaning on this
phase for GameLens AI reports or AI bot policies. See
[`BALANCE-AUTOMATION.md`](../BALANCE-AUTOMATION.md).

**Measured data (when wiring GameLens implications / later agents):**

- Read `telemetry_sessions.summary` and optional event series (ADR-0010 /
  [`telemetry.md`](../telemetry.md)). Label every figure *measured*.
- If a KPI is absent (no checkpoint, no `combat.damage` yet), say so — **never
  fill gaps** with model estimates presented as data.
- Join keys: `game_version`, `config_snapshot_id`, `policy_id`, `seed`.
- Thin catalog only until D12; reserved future names must not be treated as
  present. Game checkpoints that exist today: `post_3_deploy`, `between_wave`,
  `prep_end`, `end` (see ElJuegaso `integracion-questline.md` §10.4).

This brief itself remains valid anytime LLMPort is needed.

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
- [x] CI: adapters green against recorded/fake transports; router fallback + budget-cap
      unit tests; no live keys in CI.
- [x] Maintainer-checked live smoke (2026-09-10): same `LlmRequest` via **Groq**
      (`-p ai_groq`, `openai/gpt-oss-20b`) and **Ollama** (`-p ai_ollama`, `llama3.2`,
      cost 0). How-to: [`ai-setup.md`](../ai-setup.md).
- [ ] **Mistral live smoke deferred** (no La Plateforme key yet). Profile `ai_mistral`
      stays in `questline.toml`. Retry: set `MISTRAL_API_KEY` and
      `uv run questline ai complete -p ai_mistral "Reply with the single word pong."`
      — tracked in [`BACKLOG.md`](BACKLOG.md).
- [x] Rate-limit simulation: primary 429s → router falls to secondary → call succeeds,
      both attempts ledgered.
- [x] `BudgetExceededError` fires at the configured ceiling in a scripted loop.
- [x] Import-linter rule: `ai/providers/cursor_cli` imported by nothing in core
      (`.importlinter`; `questline.agents` does not exist yet — phase 12).

## PR checklist
Title `phase-11: ai foundation`. **ADR-0011** (not 0007 — HUD). Python 3.11+ (`pyproject`).

## Self-review

- Substrate only: port, adapters, router, hard budgets, `ai_calls` migration 5,
  versioned prompts, doctor ping, HUD cost table, thin GameLens `--ai` consumer.
  **Not** shipped: phase-12 tool loop, phase-13 eval, AI bot policies, design copilot.
- CI: fake transports; no live keys. Import-linter isolates `cursor_cli`.
- HUD: run-detail AI calls table (`Verified in HUD:` Playwright smoke + API tests).
- Live smoke: Groq + Ollama 2026-09-10. **Mistral postponed** (maintainer; not a merge
  blocker). Groq model id is `openai/gpt-oss-20b` after Llama 3.3 shutdown.
- **Incidents: none** (INC-0010 remains open from G3; out of scope).
- Accepted risk: pricing file is an estimate; free-tier model ids churn.

## Lessons / incidents

- Brief said ADR-0007 for this design — that id is HUD. Landed **ADR-0011**.
- `ai_calls` already existed in migration 1; phase-11 **appends** migration 5
  (cached / outcome / pricing_version) — never rewrite v1.
- Nested `api_key_env` must not be treated as a secret value (`*_key` rejector
  would false-positive without an `_env` exception).
- HUD Playwright must open fixture `run-a` (AI calls live there); the runs
  table is newest-first so `.first()` is `run-b`.
- Router `models.fast|strong` applies to the **primary** only; fallbacks keep
  each provider's vendor model id (do not send `mistral-small-latest` to Groq).
- Doctor pings pin `req.model` to that provider (one-provider router would
  otherwise apply profile `models.fast` to Groq).
- Urllib sends `User-Agent: questline` — Groq/Cloudflare **1010** on the
  default `Python-urllib/3.x` UA.
- Groq shut down `llama-3.3-70b-versatile` on 2026-08-16 (free/developer);
  live profiles use `openai/gpt-oss-20b` (see Groq deprecations).
- HUD `_reconcile_finished` must copy `error`/`log_tail` (same path as the waiter)
  or CI flakes when `status()` wins the race.
- **Incidents:** none.
