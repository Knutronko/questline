# Phase 15 — CI adapters, farm stubs, iOS design, docs site, v0.1.0 release

> Session preamble: see `phase-00-bootstrap.md`. Read `docs/01-ARCHITECTURE.md §3.2 + §3.4 + §9`.

## Context
Phases 00–14 merged. The framework is functionally complete for the v0.1 scope.

## Objective
Round out the integration surface (CI, farms, iOS design), polish public docs, and cut
the first release.

## In scope
1. **CIPort** (`ci/port.py`): `detect()`, `annotate(result)`, `set_status`, `summary(run)`,
   `trigger(build_ref)`.
   - **GitHubActionsAdapter** (real): CI detection, job-summary rendering (markdown of the
     run), failure annotations, artifact upload helper; the repo's own workflow dogfoods it.
   - **TeamCityAdapter** (designed + testable): service messages (`##teamcity[...]`) for
     live test reporting, REST client for build trigger/status; integration test against
     a Dockerized TeamCity marked `@requires_docker` (runs locally, optional in CI).
2. **Farm stubs** (`devices/farms/`): `BrowserStackProvider`, `BitBarProvider`,
   `FirebaseTestLabProvider` — DeviceProviderPort-conformant, constructor validates
   config, methods raise `NotImplementedError` with a doc link; `docs/device-farms.md`
   maps each provider's API to the port and states exactly what validation is pending.
3. **iOS design doc** (`docs/adr/ios.md`): Appium/XCUITest + AltTester-iOS paths, what
   the port already supports, what is blocked on macOS hardware. Honest limitations.
4. **Docs site**: mkdocs-material from `docs/` (GitHub Pages via Actions); landing page =
   README rewritten for outsiders (install, 10-minute quickstart with MockDriver, Unity
   quickstart, feature matrix incl. what is stub vs real — no overclaiming).
5. **Release engineering**: version 0.1.0; CHANGELOG (phase-per-entry); wheel build +
   `pip install questline[hud]` smoke on a clean venv in CI; GitHub Release with notes;
   PyPI publish workflow (trusted publishing) — actual publish is maintainer-triggered.
6. **Repo hygiene sweep**: BACKLOG.md groomed into GitHub issues with labels
   (`good-first-phase`, `ai`, `drivers`…); phase briefs marked completed with links to
   their PRs (the build history is part of the portfolio).

## Out of scope
Implementing any farm adapter for real; iOS code; MCP server (backlog issue).

## Acceptance criteria
- [ ] Repo's own CI shows GitHubActionsAdapter output (job summary of the demo suite).
- [ ] TeamCity adapter integration test green against local Docker TC (maintainer-run).
- [ ] Farm stubs pass port-conformance construction tests; docs state pending validation.
- [ ] Docs site builds and deploys; quickstart followed start-to-finish on a clean
      Windows machine by the maintainer.
- [ ] `v0.1.0` tagged; wheel installs clean; CHANGELOG complete; feature matrix honest.

## PR checklist
Title `phase-15: integrations + v0.1.0`. Post-merge: maintainer triggers release workflow.
