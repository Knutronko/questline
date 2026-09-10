# AI setup (phase-11 LLMPort)

> **Tiers churn — recheck this page** when a free tier, model id, or base URL
> changes. Cost estimates in `questline.ai.pricing_v1.json` are **not** billing
> truth; they exist so `BudgetExceededError` can fire.

Keys live in the **environment**. `questline.toml` stores **env var names**
(`api_key_env = "MISTRAL_API_KEY"`), never values. Do not paste keys into
chat, PRs, fixtures, or HUD exports.

Install extra (empty marker; HTTP is stdlib urllib):

```powershell
uv pip install -e ".[ai]"
```

## Profiles (same request, flip `-p`)

Repo `questline.toml` ships:

| Profile | Primary | Fallback | Cost |
|---------|---------|----------|------|
| `ai_mistral` | Mistral OpenAI-compat | Groq | estimated |
| `ai_groq` | Groq | Mistral | estimated |
| `ai_ollama` | local Ollama | — | **0** |

```powershell
# PowerShell — session only, do not commit.
# Replace with real keys from La Plateforme / Groq console.
# The literal string "..." is not a key (Mistral 401 / Groq 403 follow).
$env:MISTRAL_API_KEY = "paste-real-key"
$env:GROQ_API_KEY = "paste-real-key"

uv run questline doctor -p ai_mistral
# 1-token ping; prints env *names* and OK/FAIL, never key values

# Same LlmRequest, three backends:
$prompt = "Reply with the single word pong."
uv run questline ai complete -p ai_mistral $prompt
uv run questline ai complete -p ai_groq $prompt
uv run questline ai complete -p ai_ollama $prompt   # Ollama running locally
uv run questline ai costs --run cli
```

`--run` defaults to `cli` and is **append-only** — earlier FAIL rows stay. Look at the
latest `ok` row; Ollama must be `cost=0`.

Skip Mistral (no `MISTRAL_API_KEY`): use `-p ai_groq` and `-p ai_ollama`. Do not use
`-p ai_mistral` — that profile still lists Mistral first (skip is expected).

If Groq returns Cloudflare **1010**, the client User-Agent was blocked (`Python-urllib/…`).
Questline sends `User-Agent: questline`. Retry after pulling that fix; rotate the key
if it was pasted into chat.

### Ollama

1. Install Ollama and pull a small model (`ollama pull llama3.2`).
2. Default `base_url = http://127.0.0.1:11434`.
3. No API key. Doctor ping fails with connection error if the daemon is down.

### Free-tier notes (recheck)

See also [`02-AI-ROADMAP.md`](02-AI-ROADMAP.md) §5. Typical 2026 roles:

- **Mistral La Plateforme** — primary agents / implications (`mistral-small-latest`).
- **Groq** — fast fallback (`openai/gpt-oss-20b`; `openai/gpt-oss-120b` as strong).
  `llama-3.3-70b-versatile` shut down 2026-08-16 for free/developer ([deprecations](https://console.groq.com/docs/deprecations)).
  RPM limits → 429 → router fallback.
- **Ollama** — offline demos and zero-cost smoke.
- **Anthropic** — `kind = "anthropic"`, `api_key_env = "ANTHROPIC_API_KEY"`.
- **Cursor CLI** — experimental `kind = "cursor_cli"` (`cursor-agent --print`).
  Nothing in `questline.core` may import `questline.ai.providers.cursor_cli`
  (import-linter). Limitations: no image blocks, argv surface churns, tokens
  often unknown (cost estimate 0).

## Budgets (hard stop)

```toml
ai.budget_per_call_usd = 0.05
ai.budget_per_run_usd = 1.00
```

Exceeding either ceiling raises `BudgetExceededError` (not a warning). Env
overrides: `QUESTLINE_AI_BUDGET_PER_CALL_USD`, `QUESTLINE_AI_BUDGET_PER_RUN_USD`.

## GameLens `--ai`

`questline lens diff A B` (default `--ai`) calls LLMPort when the profile has
usable providers; otherwise a **skipped / no-provider** stub. The narrative is
*model reasoning*. Numbers come from `telemetry_sessions.summary`. Missing KPIs
(`combat.damage`, `config_snapshot_id=snap-unset`, …) are listed as gaps and
**must not be imputed**. This is not the full design-copilot report.

## HUD

Run detail (`#/runs/:id`) shows an **AI calls** table (provider, tokens, cost,
outcome). Allow-listed API: `GET /api/runs/{id}/ai-calls`. No secret values.

## CI

Adapters are tested with `FakeHttpTransport` / `FakeProvider`. CI must not set
live provider keys. Import-linter: `uv run lint-imports`.
