# Unity CLI + Pipeline — Editor/CI sidecar (not Wire)

Operator guide for the experimental Unity **CLI** (`unity` binary) and
**Pipeline** package (`com.unity.pipeline`). Product decision:
[`ADR-0012`](adr/ADR-0012-unity-cli-sidecar.md).

**Happy-path live tests stay QuestlineWire** — [`wire-setup.md`](wire-setup.md).
This page is how we *start, observe, and test the Editor*, and how Cursor talks
to Unity. It is **not** a second UI driver.

**Status (2026-09-21):** **FP-U1** is merged (PR #43): `questline unity`,
doctor row, HUD **Ensure Editor** chip. **QL-8** is merged (ElJuegaso PR #55).
Pins are in §7, copied from the game doc. **FP-U2** (`[CliCommand]`) is next.
Mock CI does not need the CLI: a missing `unity` binary is a warning.

CLI and Pipeline are **experimental** (beta / exp). APIs will move. Always
feature-detect; keep the manual Editor + Wire recipe.

Official docs (recheck when implementing):

- CLI: <https://docs.unity.com/en-us/unity-cli/use-unity-cli>
- Announcement: <https://unity.com/blog/meet-the-unity-cli>
- Pipeline package: <https://docs.unity3d.com/Packages/com.unity.pipeline@0.6/manual/index.html>

Requires **Unity 6.0 LTS+** for Pipeline. The reference game is already Unity 6.

---

## 1. Two layers (do not mix)

| Layer | What it is | Questline use |
|-------|------------|----------------|
| **`unity` binary** | Hub-less install / open / auth / doctor / VCS. JSON/TSV, exit codes, service-account env for CI. | Fresh machines, CI agents (phase-15), `questline doctor`, ensure-editor (FP-U1). |
| **`com.unity.pipeline`** | Local HTTP API in a running Editor (or Dev **standalone** Player). Built-in commands + `[CliCommand]` + `eval` + `unity mcp`. | Play/stop, UTF `run_tests`, `build`, Cursor MCP, optional companion wrappers (FP-U2). |

```
Cursor / scripts / CI
        │
        ▼
   unity (CLI) ── install Editors, open project, auth
        │
        ▼
   Editor (+ Pipeline server, localhost + bearer token)
        ├── editor_play / run_tests / build / screenshot / console
        ├── [CliCommand] → QuestlineHooks (FP-U2, optional)
        └── Play mode
                │
                ▼
         QuestlineWire :13000  ← pytest / bots / HUD launcher (unchanged)
```

Android device live: **Wire + `adb forward`**. Pipeline runtime is not that path.

---

## 2. What to use when

| Job | Use | Do not use |
|-----|-----|------------|
| pytest e2e, bots G3, find/tap, hooks, telemetry drain | Wire (`driver = "questline"`) | `eval`, `simulate_pointer`, Pipeline runtime on device |
| Open project + enter Play so Wire can connect | `unity open` + `unity command editor_play` (FP-U1) | Asking a human every smoke (once sidecar exists) |
| C# UTF EditMode/PlayMode | `unity command run_tests` when Pipeline is up; else `-batchmode -runTests` (phase-14) | Claiming green from eval |
| Dev APK / standalone build from terminal | `unity command build` (QL-8 dogfood; phase-15 CI notes) | Replacing game Build Profiles without confirm |
| Cursor while coding the **game** | `unity mcp` | `questline mcp` (framework store — FP-A1) |
| Cursor asking about **runs / triage / GameLens / locators** | `questline mcp` (FP-A1) | `unity mcp` |
| Balance retune | GameLens HUD / G4 agent (priorities only) | `eval` writing ScriptableObjects |

---

## 3. Install (maintainer / QL-8)

Windows (PowerShell), official beta channel:

```powershell
$env:UNITY_CLI_CHANNEL = 'beta'
irm https://public-cdn.cloud.unity3d.com/hub/prod/cli/install.ps1 | iex
unity --version
unity self-update   # alias: unity upgrade
```

Then, **from the Unity project root** (game repo, not questline):

```powershell
unity pipeline install
unity command            # list commands (Editor must be open with Pipeline)
```

Cursor: `unity mcp configure` (or the CLI's current MCP helper — confirm during QL-8).
Load **Unity MCP** for Editor work. Keep Questline's own tools as they are. After
FP-A1, both MCP servers may be enabled at once — see [`mcp.md`](mcp.md).

Auth for unattended CI (phase-15): env var **names**
`UNITY_SERVICE_ACCOUNT_ID` / `UNITY_SERVICE_ACCOUNT_SECRET` — values from the
environment only. Never commit them.

`unity doctor` diagnoses CLI/Editor/credentials. `questline doctor` wraps a
subset: CLI on PATH, version, Pipeline reachable (`yes` / `no` / `unknown`),
Editor running, play mode, project **basename**. A missing CLI is a yellow
warning and exit 0 — open the Editor and press Play (see
[`wire-setup.md`](wire-setup.md)).

Service-account env **names** (values never in toml, HUD, or the doctor line):
`UNITY_SERVICE_ACCOUNT_ID`, `UNITY_SERVICE_ACCOUNT_SECRET`. This FP does not
read those values.

### Questline sidecar (FP-U1)

From the suite root (the Unity project path lives only in that machine's
`questline.toml` or `QUESTLINE_UNITY_CLI_PROJECT`):

```powershell
questline doctor --profile editor
questline unity status --profile editor
questline unity ensure-editor --profile editor
```

`ensure-editor` is idempotent: `unity open <project>` when that project is not
already open, `unity command editor_play` unless Play is already on, then poll
Wire `hello` on the profile host/port (default `127.0.0.1:13000`). It does not
start Android players and it does not bind AltTester.

Opt-in for pytest (default **off**, so mock CI never launches Unity):

```toml
[profile.editor.unity_cli]
ensure_editor = true
project = "<unity-project>"   # machine-local; do not commit
command_timeout_s = 120
wire_timeout_s = 60
probe_timeout_s = 8
```

`QUESTLINE_UNITY_CLI_ENSURE_EDITOR=true` overrides the flag.
`QUESTLINE_UNITY_CLI_PROJECT` overrides the path. HUD Launch shows the same
status and an **Ensure Editor** button (`GET /api/unity/status`,
`POST /api/unity/ensure-editor`). No command palette.

Commands above use `--json` (shorthand for `--format json`), `--non-interactive`,
and `--no-banner`. Re-check upstream docs when QL-8 pins a CLI build; the
experimental surface can move.

---

## 4. Security

- Pipeline and `eval` are **localhost + bearer token**. Dev/QA only.
- Companion Wire already compiles only under `UNITY_EDITOR || QUESTLINE_DEV`.
  CliCommands follow the same gate.
- **Never** enable Pipeline runtime / eval in store/release players.
- Do not paste `evalToken`, service-account secrets, or `.env` into issues, HUD
  exports, fixtures, or chat dumps.
- HUD (FP-U1): allow-listed fields only (CLI present, editor running, play mode,
  project display name). No token, no raw home path if a project name suffices.

---

## 5. Implementation map (when scheduled)

| Id | Repo | What |
|----|------|------|
| **QL-8** | ElJuegaso | ✅ PR #55. CLI + Pipeline installed; `editor_play` / `editor_stop` proved; pins in game `integracion-questline.md` §13. `run_tests` and Android `build` were not run. **No questline core commits.** |
| **FP-U1** | questline | ✅ PR #43. Python sidecar: detect CLI, ensure-editor, wait Wire, HUD launcher chip, `questline doctor` row. |
| **FP-U2** | questline companion | Optional `[CliCommand]` → existing hooks / lens export / Wire ensure. Compiles without Pipeline. |
| **phase-14** | questline | UTF: prefer Pipeline `run_tests` if sidecar says so; fallback batchmode. Ingest into store/HUD unchanged. |
| **phase-15** | questline | Docs/CI: `unity install <version> -m android --accept-eula --yes`. |
| **FP-A1** | questline | `questline mcp` for store/agents — **this PR**. Not a wrapper around `unity mcp`. [`mcp.md`](mcp.md). |

Genre-agnostic rule still applies: no reference-game type/SO names in
`src/questline`. Game hook names stay in the game repo / companion generic API.

---

## 6. Hard non-goals

- `driver = "unity-pipeline"` (needs a new ADR if anyone ever proposes it).
- Replacing Wire find/hierarchy/tap with Pipeline scene hierarchy / input sim.
- Using `eval` to mint pytest or UTF verdicts.
- Requiring Hub uninstall.
- Shipping Pipeline in production players.
- Inventing ElJuegaso commits from a questline session.

---

## 7. Version pins

Copied from ElJuegaso `integracion-questline.md` §13 (QL-8, PR #55, 2026-09-21).
Do not guess a newer build.

| Tool | Version observed | Date |
|------|------------------|------|
| `unity` CLI | `1.0.0-beta.10` (Windows beta; was `1.0.0-beta.6`) | 2026-09-21 |
| `com.unity.pipeline` | `0.7.0-exp.1` | 2026-09-21 |
| Unity Editor (reference game) | `6000.3.20f1` (`c9ba695d4f07`) | 2026-09-21 |
| Pipeline HTTP server field | `0.0.1` (`data.server.version` on `unity command`; not the package) | 2026-09-21 |

Measured on that dogfood, not by this sidecar:

- `editor_play` entered Play; a follow-up `editor_status` reported `playing`. `editor_stop` exited. Wire logged listen on `127.0.0.1:13000`.
- A Hub-opened Editor did not appear in `unity status` (`STATUS_NO_INSTANCES`) until the command passed `--project-path`. The sidecar probe still calls `editors running` and `status` without that flag, and sends `UNITY_PROJECT_PATH` on `editor_play`.
- The first `editor_play` during domain reload can fail (`Thread was being aborted` in Pipeline `0.7.0-exp.1`). A retry succeeded. The sidecar does not retry that failure.
- `list_tests` returned 4 Input System PlayMode tests. `run_tests` and `unity command build` were not run.
