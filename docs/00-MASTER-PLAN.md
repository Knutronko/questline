# Questline — Master Plan

> **Questline** is an open-source, AI-native test automation framework for games (Unity-first),
> built from scratch in public. Python + pytest core, driver-agnostic (QuestlineWire / Poco / Appium;
> AltTester legacy),
> pluggable reporters (Slack, GitHub Issues, Notion…), CI adapters (GitHub Actions, TeamCity…),
> device providers (local adb, cloud farms), a local-first web dashboard (**HUD**), and a
> first-class AI layer (test generation, maintenance, triage, evaluation).

**Status:** planning complete — build starts at Phase 0.
**License:** MIT. **Repo:** public from day 1. **Package:** `pip install questline` (PyPI name verified free, 2026-07-28).

---

## 1. Goals

1. A real, working framework validated end-to-end against the author's own Unity games
   (Editor play mode, Windows standalone build, Android device).
2. Every integration behind a **port** (interface) with swappable **adapters** — switching
   UI driver, reporter, CI, device provider or LLM provider is a config change, not a rewrite.
3. An AI layer that is **not a demo**: agents with anti-false-positive gates, cost tracking,
   and an evaluation harness that measures them.
4. Built **in phases by independent AI coding sessions** (Cursor), each phase ending in a PR
   reviewed and merged by the maintainer. The phase briefs live in `docs/phases/`.

### Non-goals (v0.1) — all covered as future phases in `03-FUTURE-PHASES.md`
- iOS execution (port is platform-agnostic; CI-simulator validation planned as FP-P1).
- Hosted/multi-user dashboard (HUD is local-first; desktop packaging planned as FP-P3).
- Backend/API testing module (planned as FP-T1), GameLens balance intelligence (FP-G1–G4),
  chaos/monkey/soak/visual/localization testing (FP-T3–T7).

---

## 2. Locked decisions

| Decision | Choice | Rationale (short) |
|---|---|---|
| Language / runner | Python 3.12 + pytest (framework = library + pytest plugin) | Ecosystem (fixtures, markers, xdist), market relevance |
| Repo model | Public monorepo: `core/`, `drivers/`, `ai/`, `hud/`, `unity-package/`, `examples/`, `docs/` | Solo maintainer, phase-per-PR flow |
| First live driver | **QuestlineWire** (`driver = "questline"`) — hooks-first, no Desktop; **Wire v2 (09b)** adds Unity find/hierarchy/tap. AltTester = **legacy remoto**. **Poco** (Phase 14) = second UI backend (+ UTF). Appium = device layer post-v0.1. | €0 live; DriverPort stays swappable |
| Game targets | Unity Editor play mode, Windows standalone, Android (adb) | What can be validated on a Windows PC |
| Unit tests (C#) | Orchestrate Unity Test Framework in batchmode, ingest results into the same run store | One dashboard for Python + C# results |
| CI dogfood | GitHub Actions (real merge gate) + TeamCity adapter vs REST API (designed, Docker-validatable) | Free, gates every phase PR |
| Reporters v1 | Slack + GitHub Issues (bug filing with dedupe); Notion 2nd wave; Jira/TestRail stubs | Free, immediately useful |
| Device farms | Local adb provider (real); BrowserStack/BitBar/Firebase Test Lab adapters designed as stubs, one validated later via free trial | Farms are not where the value is |
| LLM providers | Provider-agnostic `LLMProvider` port. OpenAI-compatible adapter → Mistral free tier primary, Groq secondary; Ollama (offline); Cursor CLI (experimental) | €0 to run; free tiers churn, so abstraction is survival |
| Dashboard (HUD) | Local-first web app served by the framework CLI (`questline hud`); full control center (viewer + run launching + quarantine management), built in two phases | Browser = max portability; Tauri wrap possible later |
| Performance | `PerfProbe` module: adb metric sampling (FPS/mem/CPU/battery) as time series + threshold assertions + HUD graphs | Real perf-testing capability |
| Phases | 16 small phases (0–15), each fits 1–2 evening sessions and ends in a reviewable PR | Small briefs = less drift in memoryless AI sessions |

---

## 3. Design rules (hard-learned, non-negotiable)

These encode lessons from years of maintaining a production game-automation stack. Every phase
brief inherits them; PR review checks them.

1. **No silent failures.** No bare `except`, no `check=False` without asserting the effect,
   no fallback expressions whose result is discarded. Errors are typed (`QuestlineError`
   taxonomy) and every recovery action is logged as an event.
2. **Explicit wait semantics.** Two distinct concepts, never mixed: `probe` (short check:
   "is it there *now-ish*?") and `deadline` (total budget: "it must appear within X").
   A configured timeout that is silently overridden anywhere is a bug.
3. **Execution truth, not build-time truth.** Steps are tracked at *execution* time with real
   timestamps. The "where did the test die" answer is a framework datum (last started /
   last finished step + driver health at that instant), not a log grep.
4. **Verdicts come from artifacts, not from claims.** A test is green because the runner's
   parsed result says so. This applies doubly to AI agents: an agent's "it passes now" is
   never trusted — the gate re-runs and parses. (Anti-false-green rule.)
5. **Drivers are never frozen.** Pages/steps resolve the driver through a live provider at
   call time. No object caches a driver reference across a session reset.
6. **Quarantine is a ledger, not a comment.** Entering and leaving quarantine are symmetric,
   tooled operations recorded with reason, date and exit criteria. No test may be in "limbo".
7. **Everything observable.** Every run appends structured events (JSONL) and persists to the
   run store *incrementally* — a process that dies at step N keeps N−1 results. AI calls log
   tokens and cost per call.
8. **Sanitize by allow-list.** Anything exported off the machine (reports, issues, Slack)
   passes an allow-list of fields — never a blacklist.
9. **Config over code.** One `questline.toml` with named profiles (`editor`, `standalone`,
   `android_local`, `ci`, `farm`). Switching driver/device/reporter/LLM = switching profile.
10. **Docs ship with code.** A phase is done when its docs (`docs/`) and its brief's acceptance
    checklist are green in CI.

---

## 4. Architecture at a glance

Full detail in `01-ARCHITECTURE.md`.

```
                    ┌────────────────────────────────────────┐
                    │              questline CLI              │
                    │  run · hud · devices · quarantine · ai  │
                    └───────────────┬────────────────────────┘
        pytest plugin ──────────────┤
                                    ▼
   ┌──────────────────────── CORE KERNEL ─────────────────────────┐
   │ config(profiles) · event bus · run store(SQLite+artifacts)  │
   │ error taxonomy · wait policies · health/recovery · ledger   │
   └───┬──────────────┬───────────────┬──────────────┬───────────┘
       ▼              ▼               ▼              ▼
  DriverPort    DevicePort      ReporterPort      LLMPort
  ─ Wire*       ─ LocalAdb      ─ Slack           ─ OpenAI-compat (Mistral/Groq)
  ─ Poco (UI)   ─ BrowserStack* ─ GitHubIssues    ─ Ollama
  ─ AltTester†  ─ BitBar*       ─ Notion*         ─ CursorCLI (exp.)
  ─ Mock        ─ Firebase*     ─ Jira*/TestRail*
  ─ Appium*
       ▼                                               ▼
  Unity companion package (C#)                   AI agents: triage ·
  Wire listener · hooks · UTF                    maintainer · generator ·
  (* happy path; † legacy remoto; * stub/optional)
  perf counters                                  self-healing · eval harness

  HUD (FastAPI + web UI): viewer + live run + control center + perf graphs
  CIPort: GitHub Actions (real) · TeamCity (REST adapter)      * = designed stub
```

---

## 5. Phase overview

Each phase = one self-contained brief in `docs/phases/` = one Cursor session = one PR.
Merge gate: GitHub Actions (lint + type check + unit tests + phase acceptance tests).

| # | Phase | Produces | Validated against |
|---|---|---|---|
| 0 | Bootstrap | Repo scaffold, CI gate, contribution & clean-room rules | CI green on empty package |
| 1 | Core kernel | Config/profiles, event bus, run store, error taxonomy, ledger | Unit tests |
| 2 | Driver abstraction | DriverPort, locator model, wait policies, MockDriver + conformance suite | Contract tests vs mock |
| 3 | Authoring layer | pytest plugin, pages, step pipeline, assertions, markers + quarantine ledger | Unit + mock e2e |
| 4 | AltTester adapter + Unity package | Early companion + legacy adapter (Desktop live abandoned) | Author's Unity game |
| 5 | Android local | DevicePort + adb provider, APK flows | Author's phone/emulator |
| 5b | QuestlineWire | Happy-path live driver (TCP+NDJSON); Editor smoke green | Author's Unity game + Dev APK |
| 6 | Resilience | Health monitor, session-loss recovery, watchdog, infra-vs-test verdicts | Fault-injection tests |
| 7 | Reporters | Slack + GitHub Issues adapters over event bus | Real Slack ws + repo |
| 8 | HUD I (viewer) | Run history/detail/artifacts + live view | Local runs |
| 9 | PerfProbe | adb metrics sampler, thresholds, series in store | Author's game on device |
| 9b | QuestlineWire v2 UI | find / hierarchy / tap / screenshot on Wire (ADR-0008) | Author's Unity game + Dev APK (QL-2c) |
| 10 | HUD II (control center) | Launch runs, quarantine mgmt, profile editor, perf graphs | Local runs |
| 11 | AI foundation | LLMPort + adapters (Mistral/Groq/Ollama/Cursor CLI), cost ledger, failover | Live free-tier calls |
| 12 | AI agents | Triage agent, maintainer agent (diagnose/fix + gates), self-healing locators | Broken-on-purpose tests |
| 13 | AI generation + eval | Spec→test generator, unit-test generator, eval harness + metrics | Golden set |
| 14 | **Poco** + UTF | **Second** UI backend (conformance) + Unity Test Framework ingestion | Example game via Poco |
| 15 | Integrations & release | CIPort + TeamCity adapter, farm stubs, iOS design doc, docs site, v0.1.0 | Tagged release |

Dependency notes: 8→10 (HUD), 11→12→13 (AI), 2→4→5→**5b**→**9b**, 4→9, 9→9b (before GameLens bots),
3→12/13. Phase **5b**+**9b** = €0 Unity live (hooks + UI). **Poco** (14) = second UI
adapter — not AltTester. Phases 7, 9, 11 can start out of order if blocked elsewhere.
Inserted lettered phases do not renumber later briefs.

---

## 6. Operating model (how phases are executed)

1. Maintainer opens a **fresh Cursor session** and pastes the phase brief (or points it at
   `docs/phases/phase-NN-*.md` in the checked-out repo). Read `docs/STATUS-DUAL.md` for
   cross-project status (questline ↔ reference game).
2. The session works **only within the brief's scope**; anything discovered out-of-scope goes
   to `docs/phases/BACKLOG.md`, never into the PR.
3. **Mandatory self-review before finishing:** the session audits its own implementation —
   future failure modes, inconsistencies with `01-ARCHITECTURE.md` and the design rules,
   unhandled edge cases, weak tests — and writes a **Self-review** section in the PR
   description: findings (fixed vs accepted-risk) + improvement proposals (→ BACKLOG.md).
   A PR without this section is not ready for review.
4. **Update `docs/STATUS-DUAL.md`** when the phase changes done/next/blocked state (semáforo
   + roadmap row + date). Include the update in the phase PR. Cross-links:
   `docs/GAME-INTEGRATION.md`.
5. The session ends with: branch pushed, PR description filled from the brief's checklist +
   self-review, CI green. **The maintainer reviews and merges — the session never merges.**
6. **Revision round (on the branch, before merge):** the maintainer checks out the PR branch,
   tests the phase hands-on, and leaves requested changes (PR comments or a list). The same
   session — or a fresh one given the brief + the change list — applies them on the same
   branch until CI is green and the maintainer is satisfied. One phase = one PR, and nothing
   reaches `main` untested by a human.
7. A phase is *done* when its acceptance criteria are demonstrably met (CI + manual check
   where hardware is involved). "It should work" is not done.
8. Briefs are immutable once merged; scope changes create a revision commit with reasoning.
   (`STATUS-DUAL.md` is a **living** doc — not a phase brief.)

## 7. Beyond v0.1

The expansion catalog (iOS, HUD desktop app, API/backend testing module, GameLens
design-and-balance intelligence, chaos/monkey/soak/visual/localization testing, MCP server,
nightly autonomous pipeline…) lives in `03-FUTURE-PHASES.md` as unnumbered candidate phases.
An FP is scheduled by giving it the next phase number and a full brief — same template,
same rules.
