# Questline — Architecture

Companion to `00-MASTER-PLAN.md`. This document is the reference every phase brief points to.
It defines the module map, the ports (interfaces), the data model and the key contracts.
Language: Python 3.12, `src/` layout, `pyproject.toml`, strict typing (mypy), ruff.

---

## 1. Monorepo layout

```
questline/
├── pyproject.toml            # package: questline (extras: [alttester,poco,appium,slack,notion,ai,hud])
├── src/questline/
│   ├── core/                 # kernel: config, events, store, errors, waits, health
│   ├── authoring/            # pytest plugin, pages, steps, assertions, markers, quarantine
│   ├── drivers/              # DriverPort + adapters (wire/, alttester/, poco/, appium/, mock/)
│   ├── devices/              # DevicePort + providers (adb/, farms/ stubs)
│   ├── reporters/            # ReporterPort + adapters (slack/, github_issues/, notion/, console/)
│   ├── ci/                   # CIPort + adapters (github_actions/, teamcity/)
│   ├── perf/                 # PerfProbe: samplers, series, threshold assertions
│   ├── ai/                   # LLMPort + providers, agents/, evalharness/
│   ├── hud/                  # FastAPI app + built frontend assets
│   └── cli.py                # `questline` entrypoint (typer)
├── unity-package/            # C# UPM package: com.questline.companion
├── examples/
│   ├── sample-scene/         # minimal Unity scene instructions + prefab notes
│   └── demo-tests/           # example test suite used in docs & CI (mock driver)
├── docs/
│   ├── phases/               # phase briefs (the build plan)
│   └── adr/                  # architecture decision records
└── .github/workflows/ci.yml
```

---

## 2. Core kernel

### 2.1 Config & profiles
`questline.toml` at project root; `[profile.<name>]` tables select driver, device provider,
reporters, LLM provider, wait defaults, artifact policy. Resolution order:
CLI flag > env var (`QUESTLINE_*`) > profile > defaults. Secrets are **never** in the toml —
env vars only, validated at startup with actionable errors.

### 2.2 Event bus
Synchronous in-process pub/sub. Everything meaningful emits a typed event:
`RunStarted, TestStarted, StepStarted, StepFinished, TestFinished, RunFinished,
DriverRecovered, SessionLost, ArtifactSaved, AiCallMade, PerfSample …`
Reporters, the store, HUD live view and the ledger are all subscribers. New integrations
subscribe; they never patch the runner.

### 2.3 Run store
SQLite (file per project, `.questline/store.db`) + artifact directory (`.questline/artifacts/`).
Tables: `runs`, `tests`, `steps`, `events`, `perf_samples`, `ai_calls`, `quarantine`.
Writes are **incremental** (per event, transactional) — a killed process loses nothing prior.
A JSONL mirror (`.questline/ledger.jsonl`, append-only) provides the grep-able flat view.

### 2.4 Error taxonomy
```
QuestlineError
├── InfraError          # driver/device/broker/network — NOT the test's fault
│   ├── SessionLostError(kind, close_code)
│   ├── DeviceError
│   └── ProviderError
├── TestError           # the test or the game contradicts expectations
│   ├── ElementNotFoundError
│   ├── AssertionFailedError
│   └── TimeoutExceededError(kind=probe|deadline)
└── AuthoringError      # the test code is malformed (fails fast at collection)
```
Every failure is classified `infra | test | authoring | unknown` in the store — the verdict
column reporters and AI triage read. Misclassifying infra as red tests is the #1 trust killer
in game automation; this is first-class from day 1.

### 2.5 Wait policy
```python
WaitPolicy(probe: float = 2.0, deadline: float = 15.0, interval: float = 0.5)
```
- `probe`: budget for a single presence check (fast, for optional elements).
- `deadline`: total budget for a required condition.
- Policies compose: profile default < page override < step override. **No API may silently
  reset a caller's configured value** (regression-tested).
- `wait_for(condition, policy, on_timeout=raise|skip|return_false)` — the only wait primitive.
  It catches exceptions from `condition` and counts them as failed probes (retries are real).

### 2.6 Health & recovery (resilience module)
- `HealthMonitor`: cheap liveness checks (driver ping, hierarchy non-empty, device online).
- `RecoveryPolicy`: ordered strategies (`reconnect_driver` → `restart_app` → `restart_session`),
  each logged as events with duration; max attempts; consecutive-failure circuit breaker.
- `Watchdog`: no-progress timer; **every** long operation (recovery included) marks progress.
  On fire: persist state, emit event, exit with distinct code — reporters still run.
- Death-point report: on failure the store answers "last step started/finished, driver health
  at that moment, close code if any" — structured, not inferred from logs.

---

## 3. Ports & adapters

### 3.1 DriverPort (game UI automation)
```python
class DriverPort(Protocol):
    def connect(self, target: ConnectionTarget) -> None
    def disconnect(self) -> None
    def is_alive(self) -> bool
    def find(self, locator: Locator, policy: WaitPolicy | None) -> Element
    def find_all(self, locator: Locator) -> list[Element]
    def hierarchy(self) -> HierarchySnapshot        # normalized tree, driver-agnostic
    def screenshot(self) -> bytes
    def tap(self, element_or_point) / press / swipe / text_input(...)
    def call_game_method(self, hook: GameHook, *args) -> Any   # via companion package
    def app_state(self) -> AppState
```
- `Locator` is an abstract model: `by=id|name|path|text|component`, `value`, `scope`.
  Each adapter compiles it to its native query (AltTester query language, Poco selector,
  Appium locator). Registry: `locators.yaml` → generated typed accessors (codegen, committed).
- **Adapters:** `MockDriver` (CI), **`QuestlineDriver` / QuestlineWire** (happy-path live,
  ADR-0005), **`PocoDriver`** (phase-14 — primary UI hierarchy), `AltTesterDriver`
  (legacy remoto; Desktop), `AppiumDriver` (device-level OS popups — composable alongside
  a game driver).
- **Conformance suite:** one parametrized pytest suite that any adapter must pass
  (connect/find/wait/tap/hierarchy/screenshot semantics, error mapping to the taxonomy).
  This is what makes "easy to switch drivers" a tested claim instead of a slogan.
- Driver access is always via `DriverHandle` (provider indirection): a session reset swaps
  the underlying driver and all pages/steps see the live one. No frozen references.

### 3.2 DevicePort
```python
class DeviceProviderPort(Protocol):
    def acquire(self, spec: DeviceSpec) -> Device    # Device: id, platform, caps
    def release(self, device: Device) -> None
    def install(self, device, artifact: Path) -> None
    def launch/stop/forward_ports/logs/shell(...)
```
Adapters: `LocalAdbProvider` (real: discovery, install, launch, port forward/reverse with
**verified** effects — a failed `adb reverse` raises), farm stubs (`BrowserStackProvider`,
`BitBarProvider`, `FirebaseTestLabProvider`) designed against their public APIs with
`NotImplementedError` + docs, one to be validated later on a free trial.

### 3.3 ReporterPort
Event-bus subscribers with lifecycle `on_event(event)` + `finalize(run)`. Adapters:
- `ConsoleReporter` (rich live output), `HtmlReporter` (static artifact).
- `SlackReporter`: run summary post + per-failure thread replies; templates in repo; webhook
  or bot token; **allow-list rendering** (no raw paths/env leak).
- `GitHubIssuesReporter`: files/updates issues for *test-verdict* failures only (never infra);
  dedupe by failure signature hash (test id + error type + normalized message); labels;
  closes issue when green again (configurable).
- `NotionReporter` (2nd wave): run dashboard database rows. `JiraReporter`, `TestRailReporter`:
  documented stubs of the same port.

### 3.4 CIPort
`detect()` (am I in CI? which?), `annotate(test_result)`, `set_status(...)`, `trigger(build)`
for remote-trigger use cases. Adapters: GitHub Actions (real: annotations, job summaries,
artifact upload), TeamCity (REST: service messages, build trigger, status) — designed +
integration-testable against a Dockerized TC when desired.

### 3.5 LLMPort (AI foundation)
```python
class LLMProvider(Protocol):
    def complete(self, req: LlmRequest) -> LlmResponse   # text + optional image blocks + tools
    def name/model/pricing() -> ...
```
- Adapters: `OpenAICompatProvider` (one adapter covers Mistral free tier — primary, Groq,
  OpenRouter, any OpenAI-style endpoint), `OllamaProvider` (offline), `AnthropicProvider`
  (thin), `CursorCliProvider` (experimental: subprocess to `cursor-agent`; clearly labeled,
  nothing core depends on it).
- `ProviderRouter`: ordered fallback on rate-limit/outage (free tiers churn), per-call
  budget caps, and an `ai_calls` ledger row per call: provider, model, tokens in/out,
  cached, cost estimate, purpose tag, duration.
- Prompt hygiene: system prompts are versioned files in-repo; cache-friendly ordering
  (stable prefix first); image support for screenshots.

---

## 4. Authoring layer

- **pytest plugin** (`questline.authoring.plugin`): session fixture wiring profile → device →
  driver → store; per-test events; markers (`quest.smoke`, `quest.regression`, custom);
  quarantine integration (quarantined = excluded by default, runnable with `--include-quarantined`).
- **Pages**: thin classes; locators from the registry; methods return typed results; driver
  via `DriverHandle`. No waits hardcoded — policies injected.
- **Step pipeline**: declarative steps with runtime tracking:
  ```python
  scenario = (Scenario("buy pack")
      .step(Tap(Shop.open_button))
      .step(WaitFor(Shop.root))
      .call(lambda ctx: ctx.save("coins", Shop(ctx).coins()))   # inline code = a real step
      .step(AssertThat(lambda ctx: ctx["coins"] > 0)))
  scenario.run(ctx)
  ```
  Every step emits `StepStarted/StepFinished` with real timestamps (execution truth).
  Build-time vs run-time confusion is impossible by construction: nothing executes until
  `.run()`, and inline callables are steps like any other.
- **Assertions**: `expect(actual).equals(x)` / `.differs(x)` / `.is_true()` … — constructing
  an assertion with no comparison selected is a hard authoring error at build time.
- **Quarantine ledger** (`quarantine.yaml`, versioned): entry = {test id, reason, date,
  owner, exit criteria, linked issue}. `questline quarantine add|remove|audit` keeps markers
  and ledger in sync; `audit` fails CI on limbo states (marker without ledger or vice versa).

---

## 5. Unity side

### 5.1 Companion package (`com.questline.companion`, UPM)
- `QuestlineHooks`: a registry where the game exposes typed debug hooks
  (`SetLevel(int)`, `GrantCurrency(string,int)`, `SkipTutorial()`, …). The Python side calls
  them via `call_game_method` — one stable contract instead of per-game reflection guessing.
  Hooks declare whether they cause a **soft reload** so the framework knows to re-handshake
  the driver automatically (no silent session death).
- Perf counters: FPS, memory, draw calls exposed for Editor/standalone runs.
- Works with **QuestlineWire** (happy-path live, ADR-0005) and optionally legacy AltTester
  or future **Poco** — same hooks API. Never ship instrumentation in release builds.

### 5.2 Unity Test Framework orchestration
`questline unity-test run` launches Unity in batchmode (`-runTests -testResults results.xml`),
parses NUnit XML, ingests into the same run store → C# unit/integration tests appear in HUD
next to Python UI tests.

---

## 6. HUD (dashboard)

- `questline hud` → FastAPI server on localhost + embedded SPA (single build artifact,
  no Node needed at runtime). Reads the run store; live run view over WebSocket (event bus
  bridge). Wrappable in Tauri later if a native app is ever wanted.
- **Viewer** (Phase 8): run history, filters, test detail (steps timeline, artifacts,
  screenshots, hierarchy snapshots, death-point report), trends, flakiness view
  (pass-rate per test over time), AI cost per run.
- **Control center** (Phase 10): launch/stop runs (profile picker, marker/test selection,
  device picker), quarantine management (ledger-backed), profile/config editor with
  validation, perf graphs (PerfProbe series, threshold overlays), AI actions
  (trigger triage/maintainer on a failed run).

---

## 7. PerfProbe

Background sampler thread during device runs: `dumpsys gfxinfo` (FPS/jank),
`dumpsys meminfo` (PSS), `/proc/stat` CPU, battery/temperature — normalized
`PerfSample(metric, value, ts, test_id)` into the store. Editor/standalone: companion-package
counters over the driver connection. Optional assertions:
`perf.assert_avg("fps", ">=", 55, window="test")`. HUD renders series per run/test with
threshold overlays and build-over-build comparison.

---

## 8. AI layer (agents)

Common agent kernel (Phase 12): tool-use loop over LLMPort with **per-task turn budget**
(explicit task boundary signal — budgets never bleed between tests), incremental persistence
of every intermediate artifact, allow-listed tools, structured final output (JSON schema with
`verdict ∈ {diagnosed, fixed, inconclusive, passed}` — "passed" exists so greens are never
forced into failure buckets).

| Agent | Input | Output | Gate |
|---|---|---|---|
| **Triage** | Run results + events + diffs since last green | Failure clusters, infra-vs-test-vs-game classification, suspect change | Read-only |
| **Maintainer** | One failing test (diagnose-only or fix mode) | Diagnosis JSON; in fix mode a patch | Fix accepted **only** if gate re-runs the test and the parsed runner result is green; screenshots given as image blocks (vision) |
| **Self-healing locators** | ElementNotFound + hierarchy snapshot | Ranked locator candidates as a suggested registry diff | Human approves; never auto-commits |
| **Test generator** | Plain-text/Markdown spec | Test code using authoring layer + registered pages | Generated test must run (at least red-for-the-right-reason) before PR |
| **Unit-test generator** | A framework module | pytest unit tests | Coverage delta reported; human review |
| **Eval harness** | Golden set of known bugs/fixes | Metrics: fix accuracy, false-green rate, iterations-to-converge, cost per task | This *measures the agents* — see `02-AI-ROADMAP.md` |

---

## 9. iOS (designed, not validated)

`AppiumDriver` + XCUITest and the AltTester iOS path are specified in `docs/adr/ios.md`
with the port already platform-agnostic (`DeviceSpec.platform`). No implementation claims
are made until macOS hardware is available. This is an explicit, documented limitation.
