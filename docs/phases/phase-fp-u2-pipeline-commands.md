# FP-U2 — Companion Pipeline commands (hooks as `[CliCommand]`)

> Session preamble: see `phase-00-bootstrap.md`. Read **before coding:**
> [`STATUS-DUAL.md`](../STATUS-DUAL.md),
> [`unity-cli.md`](../unity-cli.md),
> [`adr/ADR-0012-unity-cli-sidecar.md`](../adr/ADR-0012-unity-cli-sidecar.md),
> [`adr/ADR-0004-companion-hooks.md`](../adr/ADR-0004-companion-hooks.md),
> [`wire-setup.md`](../wire-setup.md),
> [`GAME-INTEGRATION.md`](../GAME-INTEGRATION.md).
>
> **Scheduled:** **QL-8** landed (ElJuegaso PR #55, 2026-09-21) and **FP-U1**
> is merged (PR #43). After numbered **phase-12**. Catalog FP — does **not**
> renumber 12–15.
> **Size:** S. Prompts: [`SESSION-PROMPTS-UNITY-CLI.md`](SESSION-PROMPTS-UNITY-CLI.md).

## Context

FP-U1 (or QL-8 alone) can talk to a running Editor. Cursor's `unity mcp` already
sees Unity's built-in commands (`editor_play`, `eval`, assets…). Questline's
typed **hooks** are still only on Wire. Agents coding the game cannot call
`Ping` / GameLens export / “ensure Wire” unless we expose the **same** registry
as Pipeline commands.

## Objective

Optional companion slice: `[CliCommand]` wrappers that **only** call existing
`QuestlineHooks` / Wire ensure / documented export entry points. `unity command`
and `unity mcp` then discover them. Games without `com.unity.pipeline` still
compile the core companion.

## In scope

1. **Optional assembly** under `unity-package/` (e.g. `Pipeline/` + asmdef)
   referencing `com.unity.pipeline` **only when present** (version define
   `QL_UNITY_PIPELINE` or asmdef version defines). Core
   `Questline.Companion.asmdef` must **not** hard-require Pipeline.
   Same compile gate: `UNITY_EDITOR || QUESTLINE_DEV`.
2. **Generic commands** (no reference-game type names):
   - list/call registered hooks (names + signatures already on the Wire
     manifest — reuse, do not fork a second registry);
   - `questline_wire_ensure` (port default 13000);
   - optional `questline_lens_export` if the Editor export path is already a
     stable companion API (QL-5) — wrap it, do not reimplement snapshot math.
3. **Python:** if FP-U1 sidecar exists, `unity command` (no name) JSON → list
   Questline-prefixed commands in doctor. Do not add a Pipeline DriverPort.
4. **Tests:** C# is maintainer-checked on the game (QL-8 project). Questline CI:
   document + optional skip if Unity not in CI. Python tests mock command list
   JSON. Prove companion **without** Pipeline still imports (asmdef layout).
5. **Docs:** `unity-cli.md` command table; companion README / `wire-setup.md`
   “optional Pipeline slice”; game trigger remains QL-8 (refresh embed).
6. **HUD:** **deferred** for executing commands (command palette BACKLOG).
   If FP-U1 chip exists, it may show `pipeline_commands: N` (allow-listed names).
   No eval UI. Pablo lock: **no** HUD command runner in this FP.

## Out of scope

- Replacing Wire `call_hook` in pytest (tests keep DriverPort)
- `eval` wrappers, hot reload, `simulate_key` / `simulate_pointer` as bots
- Writing ScriptableObjects / auto-retune (G4 remains priorities-only)
- `questline mcp` (FP-A1)
- UTF ingestion (phase-14)
- Android Pipeline runtime
- Genre-specific commands (`LoadIeb`, `DeployAt`, …) in `src/questline` or
  generic companion — those stay **game** hooks; a game may add its own
  `[CliCommand]` in **its** repo that calls the same hook. Do not duplicate
  P1 names in the framework package.

## Who does what

| Layer | Owner | Role |
|-------|-------|------|
| Pipeline package on the project | **QL-8 ✅** PR #55 | `com.unity.pipeline` `0.7.0-exp.1` |
| Optional companion slice | **this FP** | Generic wrappers |
| Game-specific CliCommands | ElJuegaso (optional, later) | Thin calls to QL-7 hooks — game repo only |
| pytest e2e | Wire | Unchanged |
| Cursor during game coding | `unity mcp` | Discovers built-ins + these wrappers |

## Acceptance criteria

- [ ] Companion core compiles in CI-equivalent layout **without** Pipeline
      (asmdef / define documented; no hard UPM dep on `com.unity.pipeline`).
- [ ] With Pipeline (maintainer, QL-8 project): `unity command` lists the
      Questline wrappers; calling `Ping` (or equivalent registered hook)
      returns the same payload shape as Wire `call_hook`.
- [ ] No `eval` in the wrapper implementation. No P1 type/SO names in
      `unity-package/`.
- [ ] Docs: how to enable the slice; how game-specific commands belong in the
      game, not the framework.
- [ ] HUD: `Verified in HUD: deferred command runner (BACKLOG); chip count
      only if U1 present`. U1 is merged (PR #43).
- [ ] STATUS-DUAL. Self-review + `Incidents: …` or `none`.

## PR checklist

Title `fp-u2: companion Pipeline CliCommands`. English PR. Talk to Pablo in
Spanish. Do not merge unless Pablo asks. Do **not** invent ElJuegaso commits.
QL-8 already installed Pipeline (ElJuegaso PR #55); the game `[CliCommand]`
for sprite import is still this FP's trigger, not a questline commit.

## Lessons / incidents

(none yet — if Pipeline package version lags the CLI, file INC; do not pin a
CLI that needs an unpublished Pipeline — upstream beta.8 already hit that.)
