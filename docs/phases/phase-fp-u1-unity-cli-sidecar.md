# FP-U1 — Unity CLI sidecar (Editor lifecycle, doctor, HUD chip)

> Session preamble: see `phase-00-bootstrap.md`. Read **before coding:**
> [`STATUS-DUAL.md`](../STATUS-DUAL.md),
> [`unity-cli.md`](../unity-cli.md),
> [`adr/ADR-0012-unity-cli-sidecar.md`](../adr/ADR-0012-unity-cli-sidecar.md),
> [`wire-setup.md`](../wire-setup.md),
> [`hud.md`](../hud.md) (HUD-first),
> [`GAME-INTEGRATION.md`](../GAME-INTEGRATION.md).
>
> **Scheduled:** after numbered **phase-12**. Prefer **before phase-14** so UTF
> can consume the sidecar. Catalog FP — does **not** renumber 12–15.
> **Size:** S–M. **Prereq (live):** game **QL-8** (CLI + Pipeline on the
> maintainer box). Mock/feature-detect CI does **not** wait for QL-8.
> Prompts: [`SESSION-PROMPTS-UNITY-CLI.md`](SESSION-PROMPTS-UNITY-CLI.md).

## Context

Phases 00–11 + G1–G4 merged. Phase-12 test agents are the numbered next step.
Unity now ships an experimental `unity` CLI and `com.unity.pipeline`. Live
game tests already work when a human opens the Editor, presses Play, and Wire
listens on `:13000`. CI and Cursor still treat Unity as a GUI app.

This FP makes Questline **able to find and start that Editor**. It does not
replace Wire, Poco, or hooks.

## Objective

`questline doctor` reports whether the Unity CLI is present; an `editor`
profile can **ensure** the configured project is open and in play mode and then
wait for Wire — with a HUD launcher chip so the operator is not PowerShell-only.
If the CLI is missing, today's manual recipe still works (no hard fail).

## In scope

1. **Sidecar module** (`questline.unity_cli` or equivalent, name in-session):
   subprocess wrapper around `unity` with `--format json` / `--json`.
   Feature-detect: not on PATH → structured `available=false`, no exception
   storm. Parse `editors running`, `editor_status` when Pipeline is up.
   Timeouts, stderr vs stdout, exit 0/1/130. **Never** log tokens.
2. **Doctor:** `questline doctor` row: CLI version, Pipeline reachable
   (yes/no/unknown), Editor running + play mode when known. Allow-listed.
3. **Ensure-editor:** `questline unity ensure-editor` (or profile hook used by
   the HUD launcher / pytest plugin when `unity_cli.ensure_editor = true`):
   `unity open <project>` → `unity command editor_play` (or skip if already
   playing) → poll Wire hello on configured host/port (default `127.0.0.1:13000`).
   Idempotent. Do not bind AltTester. Do not start Android players this way.
4. **Config:** optional `[profile.*.unity_cli]` in `questline.toml` — project
   path, enable ensure-editor, timeouts. Paths stay machine-local; exports
   allow-list them away. Env var **names** only for Unity service accounts
   (not used in this FP beyond documenting the keys).
5. **HUD (required):** launcher / doctor chip: CLI present, Editor running,
   play mode. Optional button **Ensure Editor** calling the same API as CLI.
   No command palette, no arbitrary `unity command` box (BACKLOG).
   Playwright + API tests. Allow-listed JSON — no tokens, avoid raw home paths.
6. **Tests:** CLI missing; fake subprocess JSON for running/playing; timeout;
   Wire wait success/fail. No live Unity in CI.
7. **Docs:** `unity-cli.md` operator recipes filled with whatever QL-8 pinned;
   `wire-setup.md` pointer; STATUS-DUAL; `hud.md` evolution row done.

## Out of scope

- Numbered phase-12 / 13; Poco; Wire 09c; D12; SO writes
- **FP-U2** `[CliCommand]` companion wrappers
- UTF `run_tests` ingestion (phase-14 **uses** this sidecar if present)
- `unity install` CI agents (phase-15)
- `questline mcp` (FP-A1) and configuring Cursor's `unity mcp` (QL-8 / human)
- `driver = "unity-pipeline"`; `eval` as verdict; Pipeline runtime on Android
- Requiring the CLI: missing = skip ensure-editor, tell the operator to open Play

## Who does what

| Layer | Owner | Role |
|-------|-------|------|
| Install CLI + Pipeline + Cursor MCP | **QL-8** (game / human) | Unblocks live ensure-editor |
| Python sidecar + HUD chip | **this FP** | Feature-detect + ensure + doctor |
| CliCommands on companion | **FP-U2** | After this (or overlap if QL-8 done) |
| UTF transport choice | **phase-14** | Prefer Pipeline when sidecar sees it |
| Live pytest / bots | Wire (unchanged) | Still the gameplay path |

## HUD

Operator workflow = **Ensure Editor** + status chip in the **same PR**.
PowerShell how-to is extra. Defer only the command palette / raw CLI box
(already BACKLOG). Self-review: `Verified in HUD: …`.

## Acceptance criteria

- [x] CI: sidecar unit tests with fake `unity` subprocess (present / missing /
      running / playing / timeout). Doctor JSON allow-listed. No live Editor.
- [x] HUD: chip + Ensure Editor API; Playwright; no secrets in payload.
- [ ] Maintainer-checked (after QL-8): ensure-editor on the reference game
      project → Wire hello succeeds without manually pressing Play. **pending game QL-8** — mock-green does not wait.
- [x] Missing CLI: doctor warns; pytest editor profile still documents the
      manual recipe; no crash. `ensure_editor` defaults off.
- [x] STATUS-DUAL + `unity-cli.md` pins/status updated (versions still pending QL-8).
- [x] Self-review + `Incidents: none`. `Verified in HUD: …` (filled at PR close).

## Self-review

- Sidecar is not a DriverPort. Live tests stay Wire. `eval` is not an oracle.
- Missing `unity` CLI warns and skips ensure-editor. Android profiles do not call it.
- HUD chip + Ensure Editor use the same Python entry as `questline unity`.
- Allow-listed JSON: no `evalToken`, no raw home path (project basename only).
- No store migration. No ElJuegaso commits.
- **Incidents: none**.
- **Verified in HUD:** Launch chip on the smoke HUD showed CLI 1.8.0-beta.6, Editor stopped, Play off, Pipeline no. Playwright smoke (9 passed, including Ensure Editor) against port 8742 kept the chip allow-listed. Live Editor open remains **pending game QL-8**.

## PR checklist

Title `fp-u1: Unity CLI editor sidecar`. English PR. Talk to Pablo in Spanish.
Do not merge unless Pablo asks. Do **not** invent ElJuegaso commits.

## Lessons / incidents

(none yet — file INC if live ensure-editor races Wire bind or Hub vs CLI
duplicate installs; cite INC-0001 if perf env leftovers steal Wire lines.)
