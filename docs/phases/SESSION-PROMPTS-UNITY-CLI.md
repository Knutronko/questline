# Session prompts — Unity CLI / Pipeline / MCP (QL-8 + FP-U1 + FP-U2)

> Paste **one prompt per Cursor chat**. Canonical:
> [`STATUS-DUAL.md`](../STATUS-DUAL.md) §4,
> [`unity-cli.md`](../unity-cli.md),
> [`ADR-0012`](../adr/ADR-0012-unity-cli-sidecar.md).
>
> **Do not start FP-U1 or FP-U2 before numbered phase-12.**
> **QL-8 may run in parallel** with phase-12 (ElJuegaso workspace), like D11
> playtest. Do not start 09c, phase-13, phase-14, or D12 from these chats.

| Chat | Workspace | When |
|------|-----------|------|
| **QL-8** | ElJuegaso | Parallel with phase-12 (optional now) |
| **FP-U1** | questline | After phase-12; live needs QL-8 |
| **FP-U2** | questline | After QL-8; after or overlap FP-U1 |

---

## Prompt QL-8 — ElJuegaso · Unity CLI + Pipeline + MCP dogfood

Talk to Pablo in **Spanish**. Docs/PR/commits in English. Workspace:
`D:\Projects\ElJuegaso` (**not** `C:\Users\Pablo\Projects\ElJuegaso`).
Questline agents in *this* repo must **not** invent Unity commits; this prompt
is for a **game** session.

```
Project: ElJuegaso (D:\Projects\ElJuegaso). QL-8 — Unity CLI + com.unity.pipeline
+ Cursor unity mcp dogfood.

Talk to Pablo in Spanish. Docs, PR title/body, and commit messages in English.

Canonical (questline, read-only contract):
- docs/STATUS-DUAL.md
- docs/unity-cli.md
- docs/adr/ADR-0012-unity-cli-sidecar.md
- docs/GAME-INTEGRATION.md (QL-8 row)
- docs/wire-setup.md (Wire stays the live test path)

Hard rules:
- Do not replace QuestlineWire. Do not add a second hook system.
- Do not use eval to write ScriptableObjects or to mint test verdicts.
- Do not start D12, Poco/QL-4, Wire 09c, or questline FP-U1/U2 from this chat.
- Secrets: no tokens, service-account values, or .env in git/docs/chat.
- UNITY_EDITOR || QUESTLINE_DEV only for any new runtime servers.

Scope:
1. Install Unity CLI (Windows beta channel) if missing; unity --version.
2. From the Unity project root: unity pipeline install (Unity 6 required).
3. Configure Cursor unity mcp (unity mcp configure or current CLI helper).
4. With Editor open: unity command  (list); editor_status; editor_play / stop;
   list_tests (do not need a full UTF suite if none exists — record outcome).
5. Optional: unity command build for the existing Dev APK path — only if Pablo
   wants; do not redesign IL2CPP/ARM64.
6. Pin exact CLI + pipeline + Editor versions in game integracion-questline.md
   (new § Unity CLI). Note what failed (Windows pager, Hub vs CLI duplicate,
   token after domain reload).
7. Do not embed questline FP-U2 companion slice yet unless Pablo asks — that
   is a questline PR. Game may note "Pipeline installed; waiting FP-U2".

Out of scope: questline Python, HUD, phase-12, GameLens SO writes.

Start with a short plan (install vs already present, MCP, which commands to
prove) and wait for OK before changing the Unity project.
Do not merge unless Pablo asks.
```

---

## Prompt FP-U1 — questline · Unity CLI sidecar

Talk to Pablo in **Spanish**. Docs/PR/commits in English.

```
Project: questline (D:\dev\questline). FP-U1 — Unity CLI sidecar
(Editor lifecycle, doctor, HUD chip).

Talk to Pablo in Spanish. Docs, PR title/body, and commit messages in English.

Read first (do not reinvent):
- docs/STATUS-DUAL.md
- docs/unity-cli.md
- docs/adr/ADR-0012-unity-cli-sidecar.md
- docs/phases/phase-fp-u1-unity-cli-sidecar.md  (this brief — follow it)
- docs/hud.md (HUD-first: Ensure Editor + status chip in this PR)
- docs/wire-setup.md
- ElJuegaso path D:\Projects\ElJuegaso is dogfood only — never invent Unity commits

Hard product rules:
- Genre-agnostic core: no P1 type/SO names in src/questline
- Sidecar is NOT a DriverPort; live tests stay Wire
- eval is not a test oracle
- Store schema: append-only migrations if you persist anything (prefer not to)
- Secrets: env var NAMES only; never persist evalToken
- HUD-first: chip + Ensure Editor (API + SPA + Playwright). No command palette.
- Feature-detect: missing unity CLI is a warning, not a crash

Scope: Python unity CLI wrapper, doctor row, ensure-editor → wait Wire,
HUD chip, docs pins if QL-8 already recorded versions.

Out of scope: FP-U2 CliCommands, phase-14 UTF ingestion, phase-15 unity install,
questline mcp, 09c, Poco, D12, SO writes.

Start with a short plan (module layout, HUD surface, Wire wait) and wait for OK
before coding.
PR title: fp-u1: Unity CLI editor sidecar. Do not merge unless Pablo asks.
Self-review + Incidents: INC-… or none. Close-out STATUS-DUAL if status changed.
Verified in HUD: required.
```

---

## Prompt FP-U2 — questline · companion Pipeline commands

Talk to Pablo in **Spanish**. Docs/PR/commits in English.

```
Project: questline (D:\dev\questline). FP-U2 — optional companion [CliCommand]
wrappers over existing QuestlineHooks / Wire ensure / lens export.

Talk to Pablo in Spanish. Docs, PR title/body, and commit messages in English.

Read first:
- docs/STATUS-DUAL.md
- docs/unity-cli.md
- docs/adr/ADR-0012-unity-cli-sidecar.md
- docs/adr/ADR-0004-companion-hooks.md
- docs/phases/phase-fp-u2-pipeline-commands.md (this brief — follow it)
- docs/hud.md — HUD command runner DEFERRED (BACKLOG). Chip count only if U1 exists.

Hard product rules:
- Companion core must compile WITHOUT com.unity.pipeline (optional asmdef/define)
- Wrappers delegate to existing hooks; no second registry
- No P1 type/SO names in unity-package
- Game-specific commands (LoadIeb, DeployAt, …) stay in the GAME repo if at all
- eval is not a test oracle; do not wrap simulate_pointer as a bot driver
- Never invent ElJuegaso commits; live proof is pending game QL-8

Out of scope: DriverPort, questline mcp, UTF ingestion, Android Pipeline runtime,
HUD command executor, phase-12 agents.

Start with a short plan (asmdef/define strategy, command list) and wait for OK.
PR title: fp-u2: companion Pipeline CliCommands. Do not merge unless Pablo asks.
Self-review + Incidents: INC-… or none. Verified in HUD: deferred runner.
```
