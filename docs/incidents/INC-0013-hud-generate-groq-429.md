# INC-0013: HUD Generate treated Groq HTTP 429 as “no pytest file”

- **Date:** 2026-09-21
- **Phases / triggers:** phase-13 HUD Generate (live Groq)
- **Status:** fixed
- **Symptom:** Spec “Siguiente Nivel / amber 50” returned
  `verdict=inconclusive · reason=no pytest file written` after
  `LLMPort failed (ProviderError: all LLM providers failed (groq: HTTP 429 …))`.
- **Root cause:** `ProviderRouter` ledgered 429 and immediately tried the next
  provider. The HUD env-Groq list had only Groq, so the kernel failed and the
  generator appended the write-file gate reason. Groq often omits `Retry-After`
  (the wait is in the JSON body). Same-provider retry did not run.
- **Fix:** Retry 429 once on the same provider (`Retry-After` or “try again in
  Ns”, cap 15s, default 2s). Append local Ollama after env Groq. Gate
  `reason=rate_limited` with wait copy. Generate page shows HTTP 429, not a
  missing-write failure.
- **Prevention:** A 429 is quota, not a missing `write_file`. Wait ~20s and
  Generate again (Demo unchecked). Optional: start Ollama (`llama3.2`). Do not
  treat `reason=rate_limited` as a spec/pages problem.
- **See also:** [INC-0011](INC-0011-hud-generate-silent-mockdriver.md),
  [INC-0012](INC-0012-hud-generate-existing-suite-file.md)
