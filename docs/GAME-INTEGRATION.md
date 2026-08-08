# Questline — Reference Game Integration (dogfood contract)

> **Where this lives:** `docs/GAME-INTEGRATION.md` in the questline repo.
> **Audience:** every phase session (00–15 and future FPs) + the maintainer.
> **Purpose:** questline is validated end-to-end against a private **reference game**
> (a Unity tower-defense + creature-raising prototype, maintainer-owned, built in its own
> AI-phased process). This document is the contract between the two projects: what each
> framework phase needs from the game, what the game guarantees, and where the game's
> real test suite lives. Phase briefs defer to this doc for anything game-related.
>
> **Dual status board:** [`STATUS-DUAL.md`](STATUS-DUAL.md) — one-pass view of both
> roadmaps, mutual dependencies, and suggested implementation order. **Every phase PR
> that changes status must update it** (see that file §5).

---

## 1. The reference game (what framework sessions may assume)

| Fact | Guarantee |
|---|---|
| Engine | Unity, landscape 2400×1080, single main scene + a sandbox "Designer" mode |
| Balance data | 100% in ScriptableObjects (combat, grid, waves, levels, unit stats, economy, meta timers) with code defaults and `enable` toggles |
| Debug | An in-game debug/event system (typed events + full-state dump to console/file) and a cheat HUD (win, kill-all, skip-wave, grant resources, reset save, new game) |
| Save | JSON + checksum in `persistentDataPath`, two checkpoint slots |
| Testability rules | The game's AI-phase process bakes questline testability rules into every new feature (stable object names, hooks per feature, seedable RNG for new systems) — see the game repo's `integracion-questline.md` |
| What sessions must NOT assume | Game design details (units, waves, economy values) — the design is still in flux. Consume the game ONLY through the companion-package contract (hooks manifest, telemetry, SO export), never by reading game code paths. |

Game-specific knowledge (scene names, hook names, locator values) belongs in the game
repo's automation suite — never in questline core, examples excepted only if generic.

## 2. Where the game's real tests live — the `automation/` convention

The game repo contains a **self-contained** `automation/` folder:

```
<game-repo>/
├── unity/ …                    # the game
└── automation/                 # the questline test suite for this game
    ├── pyproject.toml          # own project; depends on questline (pinned version)
    ├── questline.toml          # profiles: editor / standalone / android_local
    ├── locators.yaml           # game locator registry (+ generated module)
    ├── pages/                  # game page objects
    ├── suites/                 # e2e/smoke/perf tests
    └── README.md               # how to run (venv, profiles, device setup)
```

**Lift-out rule (industry portability):** `automation/` must stay extractable as a
standalone repo at any time — own dependency manifest, no imports from game code, no
relative paths that escape the folder except the configured game-repo/APK paths in
`questline.toml`. Co-located tests (solo dev: tests travel with the game version, one PR
= feature + its tests) and split-repo tests (industry teams) are the SAME layout —
this convention is documented for framework users, not just the reference game.

## 3. ⚠️ First green live smoke → then create the real suite (do not skip)

**Status (2026-08-08):** Editor live smoke via `driver = "questline"` (QuestlineWire) is
**green** against the reference game (QL-2b). AltTester Desktop remains **out** of the
happy path (ADR-0005). Android Wire live still needs a Dev APK rebuild that includes
the Wire listener.

The maintainer should now run the **game-side exit session** (not a numbered framework
phase) with this scope:

1. Scaffold `automation/` in the game repo per §2.
2. Write the **coverage-demo suite**: real tests against the game exercising EVERY
   framework capability shipped through phase 05 —
   - profiles: same test green on `editor`, `standalone`, `android_local`;
   - pages + locator registry (real game HUD elements);
   - scenario steps incl. `HandleOptional` (a tutorial popup is the natural target),
     inline `.call()` steps and context data flow;
   - assertions (equals/differs/is_true) + one deliberately-failing test to show the
     death-point report;
   - one quarantined test with ledger entry (exit criteria documented);
   - wait policies (probe vs deadline) on a slow-appearing element;
   - artifacts: screenshot + logcat on failure, visible in the store;
   - device provider: discovery, install, launch, lock on the maintainer's phone.
3. Each later framework phase then EXTENDS this suite in its maintainer-checked
   acceptance (07 reporters → suite posts to Slack; 08/10 HUD → suite visible/launchable;
   09 → perf samples from the game; 12–13 → agents run against this suite; 14 → game's
   C# tests ingested).

## 4. Framework-phase ↔ game dependency table

Triggers are event-based (no dates). "Game session QL-n" = a small session in the GAME
repo's AI process, specified in the game's `integracion-questline.md`.

| Fw phase | Needs from the game | Trigger to game side |
|---|---|---|
| 00–03 | Nothing (mock driver) | — |
| **04** | Editor-runnable scene + companion + hooks. AltTester was an early transport; **Wire is happy-path live**. | **QL-1** ✅ |
| **05** | Instrumented **dev APK** (`QUESTLINE_DEV`) | **QL-2** ✅ (rebuild after Wire for device) |
| **05b** | **QuestlineWire** listener + `driver=questline`; Editor live smoke | **QL-2b** ✅ |
| 06 | Nothing new (fault injection mock-based; optional live reuses Wire) | — |
| 07–08 | Nothing new (consume the suite of §3) | — |
| **09** | Companion perf counters compiled in dev builds | **QL-3** (tiny) |
| 10–13 | Nothing new; agents/eval run against the §3 suite and the mock game | — |
| **14** | Test assembly (asmdef) + UTF C# tests + **Poco** SDK in a dev build (UI hierarchy; prefer over AltTester) | **QL-4** |
| 15 | Nothing new | — |
| FP-G1 | SO **export manifest** (which ScriptableObjects are balance data) | **QL-5** |
| FP-G2 | Game code calls the telemetry API (its existing debug-event convention maps ~1:1) | **QL-6** |
| FP-F1+ | Game repo path configured; feature descriptions at scan time | — |

**Rule for phase sessions:** if your phase's acceptance needs game-side work that is not
yet done, do NOT block or improvise game changes — mark the acceptance item
`pending game QL-n`, finish everything mock-checkable, and flag it in the PR. The
maintainer sequences the game side.

**Status board rule:** when a framework phase (or game QL-n) lands or its acceptance
state changes, update [`STATUS-DUAL.md`](STATUS-DUAL.md) in the same PR (or a follow-up
docs PR before the next phase starts). Do not leave the dual semáforo stale.

## 5. Balance intelligence alignment (design-tool synergy)

The game's roadmap has an **economy/measure-tools phase** and an **infinite-mode phase
that explicitly needs telemetry for retunes**. Questline's GameLens (FP-G1/G2/G3) is the
intended implementation of those measuring tools — the game should NOT build ad-hoc
balance tooling that duplicates it. When the game reaches its economy phase, the
maintainer decides whether to schedule FP-G1/G2 so both land together. Framework
sessions touching GameLens must read this section and keep the game's constraint in
mind: **the game's design is still open** — GameLens consumes whatever SOs the manifest
declares; it never hardcodes game structure.
