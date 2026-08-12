# Questline Documentation Index

## Core Documents

| Doc | Description |
|-----|-------------|
| [00-MASTER-PLAN.md](00-MASTER-PLAN.md) | Vision, goals, design rules, phase overview |
| [01-ARCHITECTURE.md](01-ARCHITECTURE.md) | Module map, interfaces, data model, contracts |
| [02-AI-ROADMAP.md](02-AI-ROADMAP.md) | AI features catalog: generation, triage, agents |
| [03-FUTURE-PHASES.md](03-FUTURE-PHASES.md) | Post-v0.1 expansion candidates (unnumbered) |

## Guides & ADRs

| Doc | Description |
|-----|-------------|
| [drivers.md](drivers.md) | How to write a DriverPort adapter + conformance |
| [writing-tests.md](writing-tests.md) | Authoring layer: plugin, pages, steps, quarantine |
| [wire-setup.md](wire-setup.md) | **Happy-path live** — QuestlineWire (phase-05b) |
| [unity-setup.md](unity-setup.md) | Legacy AltTester only (Desktop; not €0) |
| [android.md](android.md) | Local adb + Wire `android_local` |
| [resilience.md](resilience.md) | Health, recovery ladder, watchdog, infra vs test verdicts |
| [reporting.md](reporting.md) | Reporters: console, HTML, Slack, GitHub Issues; secrets; allow-list |
| [hud.md](hud.md) | Local HUD control center (`questline hud`): APIs, flags, HUD-first contract |
| [hud-operator-guide.md](hud-operator-guide.md) | **Operator guide:** all current capabilities and how to use them via the HUD |
| [performance.md](performance.md) | PerfProbe: metrics, asserts, `questline perf report`, overhead notes |
| [GAME-INTEGRATION.md](GAME-INTEGRATION.md) | Reference-game dogfood contract (phase ↔ game triggers) |
| [BALANCE-AUTOMATION.md](BALANCE-AUTOMATION.md) | **GameLens loop:** SO → snapshot → bots → telemetry → AI |
| [gamelens.md](gamelens.md) | **FP-G1 operator guide:** manifest, CLI `lens`, fixtures, Editor export |
| [STATUS-DUAL.md](STATUS-DUAL.md) | **Vista de una pasada:** estado + roadmaps questline ↔ P1 + orden propuesto |
| [INCIDENTS.md](INCIDENTS.md) | **Lessons log:** maintainer-visible traps (env/races/sync) for future AI sessions |
| [FEATURE-PIPELINE-PLAN.md](FEATURE-PIPELINE-PLAN.md) | Feature→tests pipeline plan + phase addendums |
| [adr/](adr/) | Architecture decision records |

Agent Cursor rules (always + path-scoped): `.cursor/rules/` — secrets/privacy, dual status,
GameLens/HUD contracts. Do not put tokens or machine-private data in the repo.

## Phase Briefs

| Phase | Title | Brief |
|-------|-------|-------|
| 0 | Repository bootstrap | [phase-00-bootstrap.md](phases/phase-00-bootstrap.md) |
| 1 | Core kernel | [phase-01-core-kernel.md](phases/phase-01-core-kernel.md) |
| 2 | Driver abstraction | [phase-02-driver-abstraction.md](phases/phase-02-driver-abstraction.md) |
| 3 | Authoring layer | [phase-03-authoring-layer.md](phases/phase-03-authoring-layer.md) |
| 4 | AltTester Unity driver (legacy) | [phase-04-alttester-unity.md](phases/phase-04-alttester-unity.md) |
| 5 | Android local | [phase-05-android-local.md](phases/phase-05-android-local.md) |
| 5b | QuestlineWire (happy-path live) | [phase-05b-questline-wire.md](phases/phase-05b-questline-wire.md) |
| 6 | Resilience | [phase-06-resilience.md](phases/phase-06-resilience.md) |
| 7 | Reporters | [phase-07-reporters.md](phases/phase-07-reporters.md) |
| 8 | HUD viewer | [phase-08-hud-viewer.md](phases/phase-08-hud-viewer.md) |
| 9 | PerfProbe | [phase-09-perfprobe.md](phases/phase-09-perfprobe.md) |
| 9b | QuestlineWire v2 (find/hierarchy/tap) | [phase-09b-wire-v2.md](phases/phase-09b-wire-v2.md) |
| 9c | Wire play gestures (schedule on gate) | [phase-09c-wire-play-gestures.md](phases/phase-09c-wire-play-gestures.md) |
| 10 | HUD control center | [phase-10-hud-control-center.md](phases/phase-10-hud-control-center.md) |
| 11 | AI foundation | [phase-11-ai-foundation.md](phases/phase-11-ai-foundation.md) |
| 12 | AI agents | [phase-12-ai-agents.md](phases/phase-12-ai-agents.md) |
| 13 | AI generation & eval | [phase-13-ai-generation-eval.md](phases/phase-13-ai-generation-eval.md) |
| 14 | **Poco** / UTF (second UI backend) | [phase-14-poco-utf.md](phases/phase-14-poco-utf.md) |
| 15 | Integrations & release | [phase-15-integrations-release.md](phases/phase-15-integrations-release.md) |
| FP-G1 | GameLens snapshot/diff | [phase-fp-g1-gamelens-snapshot.md](phases/phase-fp-g1-gamelens-snapshot.md) |

Joint-wave prompts: [SESSION-PROMPTS-D11-QL5-FPG1.md](phases/SESSION-PROMPTS-D11-QL5-FPG1.md).
Balance loop: [BALANCE-AUTOMATION.md](BALANCE-AUTOMATION.md).

