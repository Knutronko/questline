# Questline MCP (`questline mcp`) — Cursor / LLM hosts

FP-A1. Brief: [`phases/phase-fp-a1-mcp.md`](phases/phase-fp-a1-mcp.md).
Two-server rule: [`ADR-0012`](adr/ADR-0012-unity-cli-sidecar.md) · [`unity-cli.md`](unity-cli.md).

`questline mcp` exposes the **run store**, locators, GameLens, and (opt-in) phase-12
agents as MCP tools so Cursor can query Questline without scraping the HUD.

This is **not** Unity's `unity mcp` (Editor play / assets / `eval` / CliCommands).
After QL-8 you may enable **both** in Cursor. Do not proxy one through the other.

## Install

```powershell
uv pip install -e ".[mcp]"
# or: pip install "questline[mcp]"
```

Extra: official Python SDK `mcp>=1.12,<2` (FastMCP). Core `questline` stays
dependency-light; the CLI prints `pip install 'questline[mcp]'` if the extra is
missing.

`questline doctor` shows `mcp extra: installed` or `missing`.

## Run

```powershell
# Read-only (default) — list runs, diffs, locators. No LLM spend.
uv run --extra mcp questline mcp --config questline.toml

# Invoke triage / diagnose / heal / GameLens Ask (uses [profile] LLM + env keys)
uv run --extra mcp questline mcp --allow-write -p ai_groq

# Diagnose --fix (pytest gate still owns green)
uv run --extra mcp questline mcp --allow-write --allow-fix -p ai_groq
```

The process speaks **stdio JSON-RPC**. Anything on stdout besides the protocol
breaks Cursor. Diagnostics go to **stderr** only.

| Flag | Effect |
|------|--------|
| *(none)* | Read tools only |
| `--allow-write` | Persist agent tasks; spend LLM budget |
| `--allow-fix` | Implies write; maintainer fix mode (`--fix`). Gate re-runs pytest. |
| `--config` / `--profile` / `--store` / `--project-root` | Same resolution as HUD/CLI |

## Cursor config

Committed example for **this repo**: [`.cursor/mcp.json`](../.cursor/mcp.json).

**Questline workspace** (framework):

```json
{
  "mcpServers": {
    "questline": {
      "command": "uv",
      "args": ["run", "--extra", "mcp", "questline", "mcp"]
    }
  }
}
```

**Game repo** (e.g. ElJuegaso) once `questline[mcp]` is on that venv — point at the
game `questline.toml`, not a hardcoded home path:

```json
{
  "mcpServers": {
    "questline": {
      "command": "uv",
      "args": [
        "run", "--no-sync",
        "questline", "mcp",
        "--config", "automation/questline.toml"
      ]
    }
  }
}
```

Restart Cursor MCP after changing the file. Optional later: add `--allow-write`
to the `args` array when you want Cursor to run triage from chat.

`unity mcp` is configured separately (`unity mcp configure` during QL-8). Keep
both enabled; names do not overlap (`questline_*` vs Unity's tools).

Do not put API keys, `.env` values, or `D:\Users\…` paths in `mcp.json`.
`GROQ_API_KEY` / `MISTRAL_API_KEY` stay in the user environment.

## Tools

All names start with `questline_`. Return JSON `{ok: true, …}` or
`{ok: false, error, message}`. **Numbers and verdicts are store-owned.**

### Always on (read)

| Tool | Use |
|------|-----|
| `questline_capabilities` | Flags, tool lists, phase-13 planned vs available |
| `questline_doctor` | Profile, driver, relative store path. No secrets |
| `questline_list_runs` / `get_run` / `get_test` | History, banner split, death-point |
| `questline_list_artifacts` / `read_artifact` | Allow-listed names; path jailed to `artifacts_dir` |
| `questline_trends` | Pass-rate / flakiness board |
| `questline_list_agent_tasks` / `get_agent_task` | Triage/diagnose/heal (and later generate) |
| `questline_list_snapshots` / `get_snapshot` / `lens_diff` | GameLens config truth |
| `questline_list_implications` / `get_implications` | Persisted *model reasoning* |
| `questline_list_sessions` / `get_session` | Measured telemetry (`lose` = play, not a bot fail) |
| `questline_list_balance_turns` / `get_balance_turn` | G4 Ask history |
| `questline_list_locator_pages` / `get_locator_page` | `locators.yaml` for writing tests |
| `questline_collect_tests` | `pytest --collect-only` jailed to project root |

### Opt-in (`--allow-write`)

| Tool | Notes |
|------|-------|
| `questline_run_triage` | Clusters a finished run |
| `questline_run_diagnose` | Default diagnose-only. `fix=true` needs `--allow-fix` |
| `questline_run_heal` | Suggests locators.yaml; **never writes** |
| `questline_run_balance_ask` | Retune *priorities* only; does not write SOs |

Without `--allow-write` these return `error: write_disabled`.

### After phase-13 (auto-register)

If this install contains `questline.ai.agents.generator` / `unit_gen` /
`questline.evalharness.runner`, the server also registers:

| Tool | Notes |
|------|-------|
| `questline_generate_test` | Spec → pytest. **Gate owns execute.** Needs `--allow-write`. Dest jailed |
| `questline_unit_gen` | Framework unit-test patch artifact. Never auto-commits |
| `questline_run_eval` | Golden harness. Metrics are harness-owned |

On current `main` (pre-13) `questline_capabilities` lists them as `planned`.
Call `questline_capabilities` first when writing tests from Cursor so you know
whether generate is live.

## Implications

1. **Anti-false-green.** MCP does not add a third oracle. Diagnose fix still
   re-runs pytest. Generate (when present) still requires the phase-13 gate.
2. **Privacy.** Tool results strip raw home paths (`public_path` / basename).
   Doctor prints env **names** never values. Artifact jail refuses `..`.
3. **Budget.** Read-only Cursor chats are free. `--allow-write` uses the same
   LLMPort budgets as HUD/CLI (`BudgetExceededError` still hard-stops).
4. **HUD.** No new SPA page. Humans keep `questline hud`. Cursor is the MCP
   client. Deferred on purpose (this doc + `hud.md` + BACKLOG).
5. **Game vs framework workspace.** Point `--config` at the suite that owns
   `store.db`. A Cursor window on ElJuegaso should not silently use the
   questline repo store.
6. **Not a shell.** There is no `run_command` tool. Collect-only is the only
   pytest subprocess, and it cannot escape `project_root`.

## Later phases (tests and other tasks)

Typical Cursor flows once this server is enabled:

- **Investigate a red run:** `list_runs` → `get_run` → `get_test` →
  `read_artifact` (hierarchy.json) → optional `run_triage` / `run_heal`.
- **Write a new test (before generate exists):** `list_locator_pages` +
  `get_locator_page` + `collect_tests` + author the file in the repo. The
  authoring layer and locators.yaml are the contract; MCP does not invent
  locators.
- **Write a new test (after phase-13):** `questline_generate_test` with a
  short spec; treat `gate` as the verdict, not the model summary.
- **Balance question:** `lens_diff` + `list_sessions` (measured) then optional
  `run_balance_ask` (priorities only).

## Maintainer test plan

Automated: `uv pip install -e ".[dev,hud,mcp]"` then `uv run pytest tests/test_mcp_service.py tests/test_mcp_cli.py tests/test_mcp_server.py`.

**Hands-on (Cursor), read-only first:**

1. `uv pip install -e ".[mcp]"` in `D:\dev\questline-fp-a1` (this branch) or
   after merge, `D:\dev\questline`.
2. Confirm `.cursor/mcp.json` is loaded: Cursor Settings → MCP → **questline**
   shows tools (or restart MCP).
3. New chat: “List recent Questline runs and summarize failures using MCP.
   Do not invent verdicts.”
4. Expect `questline_list_runs` / `questline_get_run`. Counts must match HUD
   `#/` for the same store.
5. “Show locators for the MainMenu page” → `questline_get_locator_page` (needs
   `locators.yaml` at project root).
6. “Collect tests under examples/demo-tests” → nodeids, not a green/red run.
7. Ask for an API key or `C:\Users\…` path — the server must not return one.
   Doctor paths stay relative.

**Write path (optional, spends Groq):**

8. Restart MCP with `--allow-write` `-p ai_groq` (env `GROQ_API_KEY` already
   in the user environment — do not paste it into chat or mcp.json).
9. “Triage run `<id>` from the last HUD smoke.” Task appears in HUD agent
   panel and `questline_get_agent_task`.
10. Confirm `--allow-fix` is **off**: asking to “fix the test” returns
    `fix_disabled`.
11. After phase-13 merge: `questline_capabilities` shows generate `available`;
    a 5-line spec against MockDriver must still go through the collect/execute
    gate.

**Unity:** `unity mcp` (when QL-8 exists) still talks to the Editor. A prompt
about Play mode should use Unity tools, not `questline_*`.

**Verified in HUD:** deferred — `questline doctor` line `mcp extra:` only.

## See also

- [`ai-agents.md`](ai-agents.md) — how to trust triage/diagnose/heal
- [`gamelens.md`](gamelens.md) / [`telemetry.md`](telemetry.md)
- [`hud.md`](hud.md) — human operator surface (MCP does not replace it)
