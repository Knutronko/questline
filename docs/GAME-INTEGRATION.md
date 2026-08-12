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

**Status (2026-08-09):** Editor **and Android** live smoke via `driver = "questline"`
(QuestlineWire) are **green** against the reference game (QL-2b / Dev APK). AltTester
Desktop remains **out** of the happy path (ADR-0005). Android uses **`adb forward`**
(not reverse).

**Game-side exit (`automation/`):** coverage-demo scaffold is **in** the reference game
repo (ElJuegaso). Editor profile green (hooks-first). UI find/tap / `HandleOptional(Popup)`
→ **Wire v2 (fw 09b ✅ / game QL-2c)**; **Poco** remains QL-4 / fw 14 as second UI backend.
Framework `android_local` wire-smoke ✅; optional game-suite Android run remains
maintainer-checked.

Later framework phases EXTEND that suite in maintainer-checked acceptance (07 reporters →
Slack; 08/10 HUD; 09 perf; **09b Wire UI**; 12–13 agents; 14 Poco + UTF).

Exit checklist (historical DoD — now mostly done on Editor):

1. Scaffold `automation/` in the game repo per §2. ✅
2. Coverage-demo exercising phase-05 capabilities:
   - profiles: `editor` ✅ · `standalone` (same Wire contract) · `android_local` ✅ (fw smoke)
   - pages + locator registry (real HUD / smoke GO names) ✅
   - scenario steps + Save / AssertThat / `.call()` ✅; `HandleOptional(Popup)` → Wire v2 / Poco
   - assertions + deliberate death-point demo ✅ (marker-excluded by default)
   - quarantined test + ledger ✅
   - wait probe vs deadline (hooks) ✅
   - artifacts on failure (best-effort; Wire screenshot → 09b ✅; game suite after QL-2c) ✅
   - device provider wiring + live Wire for `android_local` ✅
3. Each later framework phase then EXTENDS this suite.

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
| **09** | Companion perf counters compiled in dev builds | **QL-3** ✅ (2026-08-11) — see [`performance.md`](performance.md) |
| **09b** | Companion Wire v2 UI ops (`hierarchy`/`find`/`tap`/`screenshot`); rebuild Dev APK | **QL-2c** ✅ companion (PR #41); Android APK rebuild optional |
| 10–13 | Nothing new; agents/eval run against the §3 suite and the mock game | — |
| **14** | Test assembly (asmdef) + UTF C# tests + **Poco** SDK (second UI backend) | **QL-4** |
| 15 | Nothing new | — |
| FP-G1 | SO **export manifest** (which ScriptableObjects are balance data) | **QL-5** |
| FP-G2 | Game code calls the telemetry API (existing debug-event convention maps ~1:1) | **QL-6** (thin before FP-G3; richer with D12) |
| FP-G3 | Bot scenarios / policies in `automation/` (hooks-first + Wire UI) | bot suite under `automation/` |
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
balance tooling that duplicates it.

**Maintainer lock (2026-08-12):** automate playtest-driven balance (economy, enemies,
difficulty curve, OP/UP units/skills, …) via the closed loop in
[`BALANCE-AUTOMATION.md`](BALANCE-AUTOMATION.md):

| Step | Framework | Game |
|------|-----------|------|
| Config knobs in SOs | — | **D11** (+ always §1 SO rule) |
| Declare export set | **FP-G1** format | **QL-5** manifest |
| Snapshot / diff | **FP-G1** | — |
| Emit gameplay events | **FP-G2** API | **QL-6** (thin **before bots**, richer with D12) |
| Seeded bot playthroughs | **FP-G3** | `automation/` bot suites |
| AI interpretation / smarter policies | **phase-11+** | — |

Framework sessions touching GameLens must read BALANCE-AUTOMATION and keep the game's
constraint in mind: **the game's design is still open** — GameLens consumes whatever
SOs the manifest declares; it never hardcodes game structure.

**Wire:** bots use Wire v2 + hooks; gesture extension **09c** only if the playability
gate fails (see BALANCE-AUTOMATION §5).

