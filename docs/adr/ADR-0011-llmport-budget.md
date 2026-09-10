# ADR-0011: Provider-agnostic LLMPort and hard budget policy

- **Status:** accepted (implemented in **phase-11**)
- **Context:** Phases 12–13 (agents, eval) and the GameLens implications report
  need a single LLM seam with fallback, cost accounting, and a hard stop when
  spend exceeds a ceiling. ADR-0007 is the HUD frontend stack — **do not reuse
  it**. Free-tier providers churn; keys must never live in `questline.toml`.
- **Decision:**
  1. **LLMPort** (`questline.ai.port`): `LlmRequest` / `LlmResponse` /
     `LLMProvider`. Adapters: `OpenAICompatProvider` (Mistral, Groq, OpenRouter,
     any OpenAI-style endpoint), `OllamaProvider` (local, cost 0),
     `AnthropicProvider`, `CursorCliProvider` (experimental subprocess;
     import-linter forbids `questline.core` / CLI / HUD / … from importing it).
  2. **ProviderRouter** (`questline.ai.router`): ordered `ai.candidates`;
     fallback on 429 / 5xx / timeout. **BudgetExceededError** is a hard stop
     (per-call and per-run USD ceilings from config), never a warning.
  3. **Cost ledger:** every attempt (including failed 429s) writes `ai_calls`
     via `AiCallMade`. Store **migration 5** extends the v1 `ai_calls` table
     (`cached`, `outcome`, `pricing_version`) — never rewrite migration 1
     (ADR-0002). Estimated USD from versioned `pricing_v1.json` (Ollama = 0).
  4. **Config:** nested `[profile.*.ai]` — `candidates`, budgets, `models.fast`
     / `models.strong`, `providers.*.api_key_env` (**env var names only**).
     Values come from the environment. Extra `questline[ai]` is empty; HTTP
     uses stdlib urllib (same pattern as Slack).
  5. **Prompts:** versioned files in `questline.ai.prompts`, loaded by
     name+version; stable-prefix composition for provider-side caches.
  6. **GameLens consumer:** `build_implications` may call LLMPort. Output is
     *model reasoning*. Figures come from `telemetry_sessions.summary`.
     Missing KPIs (e.g. `combat.damage`, `snap-unset`) are listed as gaps —
     never imputed. The G1 implications **live report** persists JSON/MD + a
     `lens_implications` index (migration 6). Design-copilot chat remains FP-G4.
  7. **HUD:** run-detail `ai_calls` table + `GET /api/runs/{id}/ai-calls`
     (allow-listed fields). CLI: `questline doctor` ping, `questline ai
     complete`, `questline ai costs`.
- **Consequences:**
  - Phase 12 agents import LLMPort + router only; they must not import
    `cursor_cli`.
  - Maintainer live smoke: **Groq** (`ai_groq`) and **Ollama** (`ai_ollama`) verified
    2026-09-10. **Mistral (`ai_mistral`) postponed** until a La Plateforme key exists
    — not a merge blocker; retry recipe in `docs/ai-setup.md`. CI uses fake
    transports; no live keys.
  - Pricing rows are estimates; free tiers churn — recheck `ai-setup.md`.
- **Alternatives considered:** Vendor SDKs as required extras (rejected —
  urllib + empty `[ai]` extra matches Slack/GitHub). Soft budget warnings
  (rejected — master plan cost-per-call is a hard ledger). Rewriting
  migration 1 `ai_calls` (rejected — ADR-0002).
