# ADR-0012: Unity CLI + Pipeline as Editor/CI sidecar (not a driver)

- **Status:** accepted (docs 2026-09-20; implementation = **FP-U1** / **FP-U2**)
- **Context:** Unity shipped an experimental standalone `unity` CLI (Hub replacement:
  install Editors, open projects, auth, structured JSON) and `com.unity.pipeline`
  (localhost HTTP API inside a running Editor or Development standalone Player:
  play mode, `run_tests`, `build`, `[CliCommand]`, Roslyn `eval`, `unity mcp`).
  Questline already has a happy-path live driver ([ADR-0005](ADR-0005-questline-wire.md)
  / [ADR-0008](ADR-0008-wire-v2-ui.md)), typed hooks ([ADR-0004](ADR-0004-companion-hooks.md)),
  and a planned UTF ingestion path (phase-14). Treating Pipeline as a second game
  driver would duplicate Wire, break Android live, and let agents invent verdicts
  via `eval`.
- **Decision:**
  1. **Sidecar, not DriverPort.** The Unity CLI and Pipeline package orchestrate the
     **Editor and CI** (install, open, play/stop, UTF, Player builds, Cursor MCP).
     They do **not** implement `DriverPort`. Live gameplay automation stays
     `driver = "questline"` (Wire) on Editor play and Android. Poco remains the
     second UI backend (phase-14). AltTester stays legacy remoto.
  2. **One game API.** `QuestlineHooks` remain the allow-listed contract Python
     tests call. Optional `[CliCommand]` wrappers in the companion **delegate** to
     those hooks (and GameLens export / Wire ensure-started). No second hook
     registry. Games without Pipeline still compile: Pipeline is an **optional**
     companion slice (separate asmdef / version define), never a hard UPM
     dependency of `com.questline.companion`.
  3. **`eval` is not a test oracle.** Arbitrary Roslyn `eval` / `eval_file` must
     never produce a Questline green/red. Agent claims that used eval are logged
     at most as *model/editor side effects*; the anti-false-green gate (phase-12)
     still re-runs pytest / UTF and parses the runner. Do not teach bots or
     locators to drive UGUI via `simulate_pointer`.
  4. **Android live stays Wire + adb.** Pipeline's runtime server is documented for
     Development **standalone** Players (localhost descriptor, ports ~7900–7949).
     It is **not** the device path. Optional later dogfood of Windows standalone
     Pipeline runtime is BACKLOG, not a substitute for `android_local`.
  5. **Two MCP servers.** `unity mcp` speaks to the Editor (play, assets, eval,
     custom CliCommands). **FP-A1** `questline mcp` speaks to the run store /
     triage / GameLens. Clients may load **both**. Do not proxy Unity through
     Questline or Questline through Unity.
  6. **Experimental + fallback.** CLI and Pipeline are beta/exp. Feature-detect
     (`unity` on PATH, `unity command` / `editors running` JSON). If missing,
     today's manual Editor + Wire recipe and phase-14 batchmode `-runTests`
     remain valid. Pin versions in operator docs when QL-8 lands; do not require
     Hub to be uninstalled.
  7. **Secrets / privacy.** Pipeline bearer `evalToken`, Unity service-account
     id/secret, and Hub credentials are env-only. Never persist tokens in the run
     store, HUD exports, fixtures, or Slack/GH payloads. HUD shows allow-listed
     Editor status (CLI present, project name, play-mode bool) — no raw home
     paths when avoidable (same rule as reporters).
- **Consequences:**
  - **QL-8** (game) installs CLI + Pipeline + Cursor `unity mcp` and records what
    works on the maintainer's Unity 6 Windows box. Questline sessions do not
    invent ElJuegaso commits.
  - **FP-U1** adds a Python sidecar (`questline.unity_cli` or equivalent): doctor,
    ensure-editor (open + `editor_play` + wait Wire `:13000`), HUD launcher chip.
  - **FP-U2** adds optional companion CliCommands. Phase-14 **prefers**
    `unity command run_tests` when the sidecar sees Pipeline; else batchmode.
    Phase-15 documents `unity install` for CI agents.
  - Future sessions must not add a `driver = "unity-pipeline"` without a new ADR.
- **Alternatives considered:** Replace Wire with Pipeline runtime (rejected —
  no Android path, no locator model, eval unbounded). Use Hub `--headless` only
  (rejected — slower, Hub-dependent; CLI is the migration target). Merge
  `unity mcp` into FP-A1 (rejected — different data plane). Hard-require Pipeline
  in the companion (rejected — breaks games not on Unity 6 / not on the beta).
- **See also:** [`unity-cli.md`](../unity-cli.md) ·
  [`phase-fp-u1-unity-cli-sidecar.md`](../phases/phase-fp-u1-unity-cli-sidecar.md) ·
  [`phase-fp-u2-pipeline-commands.md`](../phases/phase-fp-u2-pipeline-commands.md) ·
  [`STATUS-DUAL.md`](../STATUS-DUAL.md)
