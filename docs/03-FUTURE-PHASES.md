# Questline — Future Phases (post-v0.1 expansion catalog)

Unnumbered candidate phases. Each becomes a numbered phase (16, 17, …) only when the
maintainer schedules it; a scheduled FP gets a full brief in `docs/phases/` following the
same template and rules (self-review, revision round, acceptance criteria). Sizes:
S = 1–2 sessions, M = 3–4, L = 5+.

**Maintainer's recommended GameLens-first wave (2026-08-12):** see
[`BALANCE-AUTOMATION.md`](BALANCE-AUTOMATION.md). Short form:

**D11 + QL-5 + FP-G1** → **FP-G2 / QL-6** → **FP-G3** (deterministic bots; Wire 09c
only if playability gate fails) → **phase-11** AI foundation → AI implications +
AI bot policies → then other FPs (T2/T1/P3/…) as curiosity allows.

Older catalog wave (FP-T* interleaved before bots) is **superseded** for the reference
game's balance goals. iOS (FP-P1) whenever curiosity wins.

---

## Group G — GameLens (design & balance intelligence) 🔭

The most original module of the project: **balance regression testing**. Collects game
data per version, detects every changed variable, and reports the gameplay implications.
Reference genre for examples: tower defense + creature raising (towers, waves, economy,
creature growth curves) — but the module is genre-agnostic by design.

**Vision / loop / balance axes:** [`BALANCE-AUTOMATION.md`](BALANCE-AUTOMATION.md).
**FP-G2 brief:** [`phases/phase-fp-g2-telemetry.md`](phases/phase-fp-g2-telemetry.md).
**FP-G3 brief:** [`phases/phase-fp-g3-bots.md`](phases/phase-fp-g3-bots.md).
**FP-G2 brief:** [`phases/phase-fp-g2-telemetry.md`](phases/phase-fp-g2-telemetry.md) · operator [`telemetry.md`](telemetry.md).
**FP-G3 brief:** [`phases/phase-fp-g3-bots.md`](phases/phase-fp-g3-bots.md).

### FP-G1 — Balance snapshot, diff & AI implications report · **M · priority ALTA**
- **Extractor**: editor script in `com.questline.companion` serializes designated
  ScriptableObjects to normalized JSON (`balance_snapshot.json`) — the game marks what
  to export via an attribute or a manifest asset (**QL-5**); supplementary sources:
  JSON/CSV files and Markdown design docs from the game repo (context only, not diffed
  numerically).
- **Snapshot store**: snapshots keyed by game version/commit in the run store; CLI
  `questline lens snapshot / diff <vA> <vB>`.
- **Diff engine**: typed diffs (numeric deltas with %, added/removed entities, curve
  changes rendered as series), grouped by system tags from the manifest.
- **AI implications report** (via LLMPort): input = diff + design-doc context + optional
  telemetry (post-FP-G2/G3); output = structured report with risk flags and suggested
  playtest focus. Framing: *model reasoning* vs *measured* — never mixed.
- **Scheduling split:** ship **snapshot + diff now** (with D11/QL-5). AI report is
  **deferred acceptance** until **phase-11** (do not block G1 or bots on LLMPort).
- **Status:** FP-G1 snapshot/diff ✅ (ADR-0009 / [`gamelens.md`](gamelens.md)); AI
  stub pending phase-11. QL-5 still supplies real manifest contents.
- Prereqs (MVP): phases 4 / companion path. Prereqs (AI report): phase 11 (+ ideally G2/G3 data).

### FP-G2 — Gameplay telemetry · **M · priority ALTA (immediately after G1)**
- Companion package gains `QuestlineTelemetry`: thin dotted names (`currency.earned`,
  `unit.deployed`, `combat.leak`, `wave.completed`, … — see [`telemetry.md`](telemetry.md))
  + session envelope (version, **policy id** when bots run, seed, snapshot id);
  transport via existing `call_hook` drain during automated runs, or local file spool
  for manual play (CLI import).
- Ingestion into the store (`telemetry_sessions` + `telemetry_events`, ADR-0010);
  session summaries; HUD telemetry view **deferred** (CLI `questline telemetry`).
- Comparison: same scenario across versions → metric deltas (time per wave, economy
  inflow/outflow, …) via summaries + optional `--compare`.
- **Pull-forward:** required before meaningful FP-G3 “data extraction”; **not** only with
  game D12. Game **QL-6** maps existing debug events → this API (thin first).
- **Richer later (D12 / G2+):** reserved names in [`telemetry.md`](telemetry.md)
  (`combat.damage`, projectile.*, `creature.grown`, buff pick/skip, relocate, revive,
  `enemy.spawn`). Reuse those strings; new migration if summaries grow.
- **Status:** FP-G2 thin ✅ (ADR-0010). **QL-6 ✅** (game emit + Editor import 2026-08-13). Next: FP-G3.
- Prereqs: FP-G1 (shares versioning/context model), phase 8 (HUD optional for MVP).

### FP-G3 — Bot playthroughs & measured difficulty curves · **L · priority ALTA (after G2)**
- Scripted playthrough bots (**deterministic policies first**: "always cheapest", "rush",
  "balanced", skill on/off, …) run N seeded sessions per version via Wire + hooks
  (`driver = "questline"`). Prefer hooks + Tap-deploy; see BALANCE-AUTOMATION §5.
- **Must** attach `policy_id`, `seed`, `config_snapshot_id` on telemetry sessions and
  drain with `questline.telemetry.drain.drain_telemetry` (see
  [`phase-fp-g3-bots.md`](phases/phase-fp-g3-bots.md) + [`telemetry.md`](telemetry.md)).
- Metrics per version: waves survived, time-to-fail, economy curves, unit/skill
  contribution → **measured** difficulty / power curves, overlaid on FP-G1 config diffs
  (*cause → effect*). Thin events only until D12; do not invent damage/ranch KPIs.
- **AI-policy bots** are a **later add-on** after phase-11 (optional phase-12 tools):
  compare against deterministic baselines; never the sole acceptance gate.
- Reuses “run matrix, compare configurations” patterns; **does not require phase-13**
  eval harness (that harness measures *agents*, not game balance).
- Wire **09c** (gestures) only if the playability gate fails — 
  [`phases/phase-09c-wire-play-gestures.md`](phases/phase-09c-wire-play-gestures.md).
- Prereqs: FP-G1 + FP-G2, Wire v2 (09b); **not** phase 11/13 for deterministic bots.

### FP-G4 — Design copilot · **M · priority BAJA (visionary)**
- Chat interface (HUD panel) over GameLens history: "what changed between 0.3 and 0.4
  that made wave 12 harder?", "which creature stat has never been touched?".
  RAG over snapshots + `telemetry_sessions` + reports. Prereqs: G1–G3 mature + phase-11.
  Event names: thin catalog now; D12 reserved names when present — do not invent aliases.

---

## Group P — Platform reach

### FP-P1 — iOS stage 1: build & simulator validation on CI · **M · priority MEDIA**
- No Mac owned — use **GitHub Actions macOS runners (free for public repos)**:
  Unity iOS build (license via secrets), Xcode archive, boot iOS Simulator, run the smoke
  suite against the simulator (AltTester or XCUITest path — investigate in-phase, record
  ADR). Validates the port's platform-agnostic claims without hardware.
- Honest scope: simulator ≠ device; perf metrics out of scope.
- Prereqs: phases 4–5; Apple developer account not required for simulator.

### FP-P2 — iOS stage 2: real device · **L · priority BAJA (gated on hardware)**
- Physical iPhone or cloud Mac + device farm trial. Appium/XCUITest device layer,
  perf sampling (instruments). Explicitly gated: do not schedule without hardware access.

### FP-P3 — HUD desktop app (Tauri) · **S · priority MEDIA-ALTA**
- Wrap HUD in Tauri: native Windows/macOS installers, embedded server auto-start, tray
  icon, file associations for `.questline` stores. The SPA is untouched (that was the
  point of the browser-first decision). CI matrix builds both installers on tag.
- Prereqs: phase 10.

### FP-P4 — Appium device-level driver · **M · priority MEDIA**
- The composable second driver for OS-level interactions: permissions dialogs, keyboard,
  notifications, deep links, app switching. Runs *alongside* the game driver in one test.
  Also the foundation FP-T5 (interruptions) builds on. Prereqs: phases 2, 5.

---

## Group T — Test-type expansion (full game-dev lifecycle coverage)

### FP-T1 — API & backend testing module · **M · priority ALTA**
- `questline.api`: fluent HTTP client with assertion integration (`api.get(...).expect_status(200).expect_schema(...)`);
  **contract testing against OpenAPI specs** (request/response validation, drift detection);
  **Postman collection import** → generated test suites; **mock server** (spec-driven) so
  the game client can be tested with no real backend; analytics-event validation (the
  game fires events → schema-checked against a registry).
- Works standalone (pure API suites) and inside e2e tests (game action → backend state
  assert). Reports/verdicts flow through the same store/reporters/HUD.
- Prereqs: phases 1, 3. (Mock server useful from the first game prototype.)

### FP-T2 — Save/load integrity & migration testing · **S-M · priority ALTA**
- Save-state capture/restore through companion hooks; golden saves library (versioned
  fixtures); **migration matrix**: load every older save format in the newest build →
  assert integrity; corrupted-save fuzzing (truncated/mutated files → game must not crash);
  PlayerPrefs + JSON save coverage (matches the reference game's storage).
- One of the highest-value tests during active game development. Prereqs: phase 4.

### FP-T3 — Visual regression · **M · priority MEDIA**
- Screenshot baselines per screen/resolution; perceptual diff (SSIM + masks for dynamic
  regions); AI judgment pass for "intentional vs regression" suggestions (human decides);
  HUD side-by-side viewer with baseline management. Prereqs: phases 4, 8, 11 (AI part).

### FP-T4 — Localization sweep · **S-M · priority MEDIA**
- Missing-key detection (static: string tables vs usage), runtime overflow/truncation
  detection (text bounds vs container bounds via hierarchy), per-language screenshot
  batches for review, pseudo-locale run (lengthened strings) as a cheap canary.
  Prereqs: phase 4.

### FP-T5 — Chaos & interruption testing · **M · priority MEDIA**
- Scenario decorators injecting: network loss/latency (emulator controls), app
  backgrounding/foregrounding, incoming call/notification simulation, low battery, storage
  pressure, device clock changes (time-travel cheats/anti-cheat checks), locale/timezone
  switches. Assert graceful behavior + state preservation. Prereqs: phases 5, 6, FP-P4
  for some interruptions.

### FP-T6 — Monkey/fuzz testing + crash triage · **M · priority MEDIA-ALTA**
- Random-input bot (weighted taps/swipes over the live hierarchy — smarter than raw
  monkey), seeded for reproducibility; crash/ANR capture (logcat + tombstones) with
  **signature dedupe**; AI triage of unique crashes (stack → suspect area); soak-friendly
  (run for hours). During early game dev this finds more bugs per hour than any scripted
  test. Prereqs: phases 5, 6; 11–12 for AI triage.

### FP-T7 — Soak & leak detection · **S · priority MEDIA**
- Long-session runs (loop scenarios for N hours) with PerfProbe trend analysis: memory
  growth slope detection, FPS degradation over time, handle leaks. Report flags leak
  suspects with the series attached. Prereqs: phases 5, 9.

### FP-T8 — Build validation & budgets · **S · priority MEDIA**
- Per-build checks: APK/AAB size vs budget (+ per-asset-category breakdown delta vs last
  version), cold-start time budget, permissions manifest diff (new permission = fail
  until acknowledged), shader/asset stripping sanity. Runs in CI on every game build.
  Prereqs: phases 5, 15 (CI adapters).

### FP-T9 — Compatibility matrix · **S-M · priority BAJA-MEDIA**
- Emulator matrix runs (API levels × resolutions × aspect ratios; notch/cutout cases);
  layout assertion helpers (safe-area violations); HUD matrix report. Cloud farm adapters
  (from phase 15 stubs) plug in here when validated. Prereqs: phases 5, 8.

### FP-T10 — Monetization & ads flows · **S-M · priority BAJA (until the game monetizes)**
- IAP sandbox flows (Google Play billing test tracks), ad lifecycle via mockable hooks in
  the companion package (no real ad SDK dependency in tests), reward-grant assertions,
  restore-purchases flow. Prereqs: phases 4–5, FP-T1 (receipt validation mocks).

---

## Group A — AI & automation expansion

### FP-A1 — MCP server · **S-M · priority MEDIA**
- `questline mcp`: expose runs/results/triage/GameLens queries as MCP tools so any MCP
  client (Claude, Cursor, custom agents) can drive the framework conversationally.
  High keyword value; thin layer over existing APIs. Prereqs: phases 10–12.

### FP-A2 — Nightly autonomous pipeline · **S · priority MEDIA-ALTA**
- Scheduled (Task Scheduler/cron/CI): build or fetch latest game build → run suite →
  triage agent digest → Slack + issues filed → HUD morning view. The full closed loop,
  unattended. Prereqs: phases 7, 12; FP-T8 pairs well.

### FP-A3 — Flakiness predictor · **S · priority BAJA**
- Classic ML (no LLM) over run-store history: flag tests trending flaky before they block.
  Prereqs: months of accumulated store data.

### FP-A4 — Self-healing auto-PR mode · **M · priority BAJA (trust-gated)**
- Maintainer agent + healer graduate from suggest-only to opening PRs automatically
  (never merging). Gate: eval-harness metrics above thresholds for N consecutive evals —
  the harness literally decides when the agent has earned autonomy. Prereqs: phases 12–13
  mature.

---

## Game-dev lifecycle coverage map

What a solo Unity game needs tested at each stage, and where Questline covers it:

| Dev stage | Need | Coverage |
|---|---|---|
| Prototype | Does core loop work? Crashes? | Smoke e2e (P4), monkey bot (FP-T6) |
| Systems build-out | Logic correctness | UTF unit tests ingested (P14), save/load (FP-T2) |
| Content/balance iteration | What changed & what it does to gameplay | **GameLens (FP-G1–G3)** |
| Feature growth | Regressions | e2e suites (P3–5), visual (FP-T3), impact-aware selection (backlog) |
| Perf hardening | FPS/memory/leaks | PerfProbe (P9), soak (FP-T7), build budgets (FP-T8) |
| Release prep | Devices, locales, stores | Compat matrix (FP-T9), localization (FP-T4), monetization (FP-T10), iOS (FP-P1/P2) |
| Live | Backend, analytics, nightly confidence | API module (FP-T1), analytics validation (FP-T1), nightly pipeline (FP-A2) |
