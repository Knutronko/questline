# FP-A1 — Questline MCP server (`questline mcp`)

> Session preamble: see `phase-00-bootstrap.md`. Read **before coding:**
> [`03-FUTURE-PHASES.md`](../03-FUTURE-PHASES.md) Group A · FP-A1,
> [`ADR-0012`](../adr/ADR-0012-unity-cli-sidecar.md) (two MCP servers),
> [`unity-cli.md`](../unity-cli.md),
> [`02-AI-ROADMAP.md`](../02-AI-ROADMAP.md),
> [`ai-agents.md`](../ai-agents.md),
> [`hud.md`](../hud.md) HUD-first contract (**this phase defers a HUD page**),
> [`STATUS-DUAL.md`](../STATUS-DUAL.md).
>
> **Scheduled:** parallel with phase-13 (does not wait on generate/eval).
> **Size:** S–M. Catalog FP with a full brief.
> **Base:** `origin/main` (phase-12 merged). Do not mix with the phase-13 working tree.

## Context

Phases 10–12 shipped the data plane Cursor wants to ask about: run store, HUD
query DTOs, triage / diagnose / heal, GameLens snapshots/diff/implications,
telemetry sessions, balance-agent turns. There is no MCP server. Cursor today
talks to Questline only by reading the repo or by the human running CLI/HUD.

Unity's `unity mcp` (QL-8 / FP-U2) speaks to the **Editor**. This FP speaks to
the **framework store**. Clients may load both. Do not proxy one through the
other (ADR-0012).

## Objective

Ship `questline mcp`: a stdio MCP server so Cursor (or any MCP host) can query
runs, failures, locators, GameLens, and optionally invoke the phase-12 agents.
Thin wrappers over existing store / `hud.queries` / `lens.browse` / agent
entrypoints. No second verdict channel.

## In scope

1. Optional extra `questline[mcp]` (`mcp>=1.12,<2` — FastMCP / protocol Cursor
   already speaks). Core install stays light.
2. CLI `questline mcp` (stdio). **Default is read-only.** `--allow-write` enables
   triage / diagnose / heal / GameLens Ask. `--allow-fix` opts into maintainer
   `--fix` (anti-false-green gate still owns green). **No bytes on stdout except
   the MCP protocol.**
3. Tool surface (names prefixed `questline_` so they never collide with
   `unity mcp`):
   - Session: `capabilities`, `doctor` (no secrets, no raw home paths).
   - Runs: `list_runs`, `get_run`, `get_test`, `list_artifacts`, `read_artifact`
     (jail = `artifacts_dir`, text cap), `trends`.
   - Agents (read): `list_agent_tasks`, `get_agent_task`.
   - GameLens: snapshots, diff, implications, telemetry sessions, balance turns.
   - Authoring helpers (for later test-writing in Cursor): `list_locator_pages`,
     `get_locator_page`, `collect_tests` (`pytest --collect-only`, path jailed
     to `project_root`).
   - Write-gated: `run_triage`, `run_diagnose`, `run_heal`, `run_balance_ask`.
4. **Forward-compatible optional tools:** if `questline.ai.agents.generator` /
   `unit_gen` / `questline.evalharness` exist (phase-13+), register
   `generate_test` / `unit_gen` / eval tools automatically. On this branch they
   stay `planned` in `capabilities`.
5. Docs: `docs/mcp.md` (install, Cursor config, tool table, implications,
   maintainer test plan). STATUS-DUAL, AI-ROADMAP, architecture, unity-cli,
   hud evolution **deferral**, BACKLOG, README index.
6. Tests: service layer (no SDK required) + CLI stdout hygiene + FastMCP tool
   names when the extra is installed. CI installs `[mcp]`.
7. Project `.cursor/mcp.json` example (no secrets, no absolute home paths).

## Out of scope

- `unity mcp` / QL-8 / FP-U1 / FP-U2 / Pipeline / `eval` as a test oracle
- HUD SPA page or “MCP connected” chip (doctor row is enough)
- Streamable HTTP / SSE transports (stdio only; Cursor launches a subprocess)
- Arbitrary shell / `questline` CLI passthrough (too easy to leak secrets or
  invent greens)
- Auto-PR, nightly pipeline (FP-A2/A4)
- Merging this into the phase-13 PR
- Game-genre types/SOs in `src/questline`

## Implications (locked)

| Topic | Decision |
|-------|----------|
| Verdicts | Tools return **store** fields. Models must not be asked to invent pass/fail. Diagnose `--fix` still requires the pytest gate. |
| Secrets | No env values, tokens, or raw home paths in tool results. Artifact paths via `public_path`. `api_key_env` **names** only on doctor. |
| Write default | Read-only. Cursor can browse a game repo without spending LLM budget or mutating the store. |
| HUD | **Deferred.** Human operator path remains `questline hud`. Cursor is the MCP client. Pablo lock is this brief + hud.md + BACKLOG. |
| Layering | `questline.mcp` may import store, `hud.queries`, `lens.browse`, agents. HUD / core / lens must not import `questline.mcp`. No `cursor_cli` from MCP (the host *is* Cursor). |
| Two servers | Load `questline` + `unity` MCP side by side after QL-8. Different data planes. |
| Phase-13 | Generate/eval tools appear when those modules exist. Do not block this FP on 13. |
| Stdio | `typer.echo` on stdout would corrupt JSON-RPC. Diagnostics go to stderr only. |

## Acceptance criteria

- [ ] `uv pip install -e ".[mcp]"` then `questline mcp --help` lists `--allow-write` / `--allow-fix`.
- [ ] Missing extra: `questline mcp` exits 1 with `pip install 'questline[mcp]'`.
- [ ] Service tests: list/get run from the HUD fixture store; write tools refuse
      without `--allow-write`; path jail on `read_artifact` / `collect_tests`.
- [ ] FakeProvider triage via `--allow-write` persists an `agent_tasks` row
      (same ScriptedBalanceProvider as HUD).
- [x] `capabilities` lists generate/eval as `available` once phase-13 is on the same tree.
- [ ] Docs + STATUS-DUAL + HUD deferral + Self-review.
- [ ] CI green with `[mcp]` extra.

## PR checklist

Title `fp-a1: questline mcp server`. Do not merge unless asked.
Update AI-ROADMAP status. Self-review below.

Operator acceptance is **Cursor MCP** (not HUD). HUD UI deferred in this brief.

```
Verified in HUD: deferred (FP-A1) — doctor prints `mcp extra:`; no new SPA route.
```

## Self-review (this PR)

- **Findings (fixed):** stdio must not use `typer.echo` (JSON-RPC). MCP must not import
  `questline.ai.factory` (import-linter → cursor_cli). `find_spec` on a missing parent
  package raises `ModuleNotFoundError` (optional generate/eval). Artifact/collect paths
  are jailed. `--allow-fix` is a separate flag so Cursor cannot silently patch.
- **Accepted risk:** FastMCP tool wrappers are thin; coverage lives in `service.py`.
  Generate/eval tools register because phase-13 is on this tree; service/server tests
  assert `available`. Hands-on Cursor connect is maintainer-checked (see `docs/mcp.md`).
- **HUD:** deferred — doctor `mcp extra:` only. Cursor is the client.
- **Incidents:** none
- **Verified in HUD:** deferred (FP-A1) — `questline doctor` prints `mcp extra:`.
