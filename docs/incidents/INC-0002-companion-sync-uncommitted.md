# INC-0002: Game companion QL-3 / QL-2c left uncommitted in working tree

- **Date:** 2026-08-11
- **Phases / triggers:** phase-09 → QL-3; phase-09b → QL-2c
- **Status:** fixed
- **PRs:** ElJuegaso [#41](https://github.com/Knutronko/ElJuegaso/pull/41)

## Symptom

1. Framework Wire v2 live failed with clear `AuthoringError`: companion does not
   advertise UI (`protocol_version < 2` / missing `features: ui`) while questline
   PR already had v2.
2. Maintainer believed game “phases were closed” but `git status` on ElJuegaso still
   showed dirty companion files + Unity noise — looked like unfinished D-work.

## Root cause

- **QL-3:** `QuestlinePerfProvider.cs` (+ meta) and a small WireServer hook were
  copied into the embedded package for maintainer C/D and **never got a game PR**.
- **QL-2c:** WireServer v2 + `QuestlineWireUi.cs` were copied the same day for live
  AC; still only local until PR #41.
- Unrelated Unity asset / ProjectSettings / `.utmp` noise made the WT look larger
  than the real sync debt.

Canonical game path: `D:\Projects\ElJuegaso` (not under `C:\Users\…`).

## Fix

- Dedicated branch/PR from `main` with **only** companion + docs
  (`EMBEDDED.md`, `integracion-questline.md`); discard URP/ProjectSettings/`.utmp`.
- Merged as ElJuegaso PR #41 (QL-2c + QL-3 companion embed).

## Prevention

- After any “copy companion from questline → game” step: **open a game PR the same
  day** (or explicitly note “local-only dogfood — PR pending” in STATUS / chat).
- `git status` on the game repo before declaring QL-n done; do not treat “framework
  phase ✅” as “game embed committed”.
- Separate branches: gameplay/proto ≠ companion sync PR when possible.
- Never commit Unity `.utmp/`, accidental URP churn, or `UnityConnectSettings`
  toggles in a companion PR.
- Wire live AC for 09b requires game companion **v2 on disk and loaded in Play**
  (`[QuestlineWire] listening … (v2)`); framework CI alone is not enough.

## See also

- INC-0001 (perf env race) — same live window
- [`docs/GAME-INTEGRATION.md`](../GAME-INTEGRATION.md), [`docs/wire-setup.md`](../wire-setup.md)
- questline `unity-package/Runtime/` ↔ ElJuegaso `unity/Packages/com.questline.companion/`
