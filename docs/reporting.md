# Reporting — console, HTML, Slack, GitHub Issues

Reporters subscribe to the event bus and seal a run via `finalize(RunSummary)`.
They never patch the runner. Verdicts come from the store (`infra` | `test` |
`authoring` | `unknown`), not from raw pytest outcomes alone.

See architecture [`01-ARCHITECTURE.md`](01-ARCHITECTURE.md) §3.3 and design rule
**sanitize by allow-list** in [`00-MASTER-PLAN.md`](00-MASTER-PLAN.md) §3.8.

## Enable reporters

```toml
[profile.ci]
reporters = ["console", "html", "slack", "github_issues"]
slack_channel = "C01234567"          # non-secret
github_repo = "acme/questline-sandbox"  # owner/name; non-secret
github_issues_auto_close = true
github_issues_labels = ["questline", "test-failure"]
```

Env overrides: `QUESTLINE_REPORTERS`, `QUESTLINE_SLACK_CHANNEL`,
`QUESTLINE_GITHUB_REPO`, `QUESTLINE_GITHUB_ISSUES_AUTO_CLOSE`,
`QUESTLINE_GITHUB_ISSUES_LABELS`.

Unknown reporter names fail fast at session start (`AuthoringError`).

| Name | Module | Notes |
|------|--------|--------|
| `console` | `reporters.console` | Rich live progress (pass/fail/infra counters) |
| `html` | `reporters.html` | Static `.questline/artifacts/report-<run_id>.html` |
| `slack` | `reporters.slack` | Start post + finish update/thread; `questline[slack]` surface |
| `github_issues` / `github` | `reporters.github_issues` | **test** verdict only; signature dedupe |
| `notion` / `jira` / `testrail` | stubs | Port-conformant `NotImplementedError` |

## Secrets (env only — never toml)

| Variable | Used by |
|----------|---------|
| `QUESTLINE_SLACK_TOKEN` | Slack Web API (bot token) |
| `QUESTLINE_SLACK_WEBHOOK` | Incoming webhook (start + finish posts) |
| `QUESTLINE_GITHUB_TOKEN` | GitHub Issues REST |

Doctor / config reject secret keys inside `questline.toml`. Prefer bot token when
you need threaded failure replies; webhook mode posts discrete messages.

### Maintainer live checks (optional — not required for CI/merge)

```powershell
# Slack (bot): set QUESTLINE_SLACK_TOKEN + QUESTLINE_SLACK_CHANNEL, reporters include slack
$env:QUESTLINE_SLACK_TOKEN = "xoxb-..."
$env:QUESTLINE_SLACK_CHANNEL = "C..."
.\.venv\Scripts\python.exe -m pytest path\to\suite -q --questline-profile ci

# GitHub sandbox: QUESTLINE_GITHUB_TOKEN + github_repo in profile
$env:QUESTLINE_GITHUB_TOKEN = "ghp_..."
```

Force a **test** failure → one issue; rerun → comment (same signature). Force an
**infra** failure (`SessionLostError`) → **no** issue.

## Allow-list rendering

Slack / issue / HTML export fields pass through `reporters.allowlist` — only
whitelisted keys (`run_id`, `nodeid`, `verdict`, `error_message`, …) are
interpolated into templates. Artifact paths, env dumps, and tokens are never
template fields. Unit test: `tests/test_reporters_allowlist.py`.

## GitHub Issues policy

1. File **only** when `verdict=test` (never infra/authoring/unknown).
2. Signature = `sha256(nodeid|error_type|normalized_message)[:16]` embedded as
   `<!-- questline:signature=… -->` in the issue body.
3. Open issue with same marker → comment on rerun (no duplicate).
4. Optional `github_issues_auto_close`: on an all-green run, close open
   questline-signature issues (fake transport in CI; live close is conservative).

## Crash isolation

`EventBus.publish` isolates `on_event` exceptions. `finalize_all` isolates
`finalize` exceptions. One exploding reporter does not stop the run or other
reporters (`tests/test_reporters_isolation.py`).

## CI

All adapters are unit-tested with `FakeSlackTransport` /
`FakeGitHubIssuesTransport`. No live Slack or GitHub calls in CI (€0).

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_reporters_allowlist.py tests/test_reporters_isolation.py tests/test_reporters_slack.py tests/test_reporters_github.py tests/test_reporters_registry.py -q --no-cov
.\.venv\Scripts\python.exe -m pytest -q
```

## Stubs (2nd wave)

| Stub | Intended mapping |
|------|------------------|
| `NotionReporter` | One database row per run + child pages per failed test |
| `JiraReporter` | Same test-verdict + signature-dedupe policy as GitHub Issues |
| `TestRailReporter` | Push run results; case ids via markers / `feature_id` |

## Out of scope here

HUD live viewer (phase 08), AI digests posted through reporters (phase 12).
