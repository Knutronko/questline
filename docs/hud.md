# Questline HUD — local run viewer

`questline hud` serves a **local-first** dashboard over your run store: history,
run/test detail (verdicts, death-point, artifacts), trends, and a live WebSocket
view of the in-progress run.

This is a **viewer** (phase 08). Launching runs / quarantine UI / perf graphs
arrive in [phase 10](phases/phase-10-hud-control-center.md).

Stack decision: [ADR-0007](adr/ADR-0007-hud-frontend-stack.md).

## Install

```powershell
uv pip install -e ".[hud]"
# or: pip install "questline[hud]"
```

Optional extras pull in FastAPI + uvicorn. The SPA is **embedded in the wheel** —
no Node at runtime.

## Run

```powershell
questline hud
questline hud --port 8741 --open
questline hud --store D:\path\to\.questline\store.db
```

Defaults:

| Flag | Default | Notes |
|------|---------|-------|
| `--host` | `127.0.0.1` | Opt-in for non-localhost binds |
| `--port` | `8741` | |
| `--open` | off | Opens the system browser |
| `--store` | profile `store.db` | Under `.questline/` |

Empty store → API returns `{ "runs": [], "empty": true }` and the UI shows a clear
empty state (not an error).

## Pages

| Route | Content |
|-------|---------|
| `#/` | Runs table — profile, driver, device, pass totals, infra/test split, duration |
| `#/runs/{id}` | Tests grid + **infra vs test** banner (verdicts from store) |
| `#/runs/{id}/tests/{tid}` | Step timeline, death-point, artifacts, history sparkline |
| `#/trends` | Pass-rate / duration charts, flakiness board |
| `#/live` | WebSocket stream (`/live` or `/api/live`) of EventBus events |

## API (local)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/health` | Liveness |
| GET | `/api/runs` | List + `profile` / `status` filters |
| GET | `/api/runs/{id}` | Run detail + tests + verdict banner |
| GET | `/api/runs/{id}/tests/{tid}` | Steps, death-point, artifacts, history |
| GET | `/api/runs/{id}/artifacts` | Artifact list (allow-listed fields) |
| GET | `/api/artifacts/file?path=` | File bytes — **only** under store `artifacts_dir` |
| GET | `/api/trends` | Aggregations |
| WS | `/live` | Live event fan-out |

Secrets never appear in the HUD. Artifact paths are constrained to the store
artifacts directory (path traversal → 403).

## Frontend rebuild (maintainers)

Node is only needed to change the SPA:

```powershell
cd hud/frontend
npm ci
npm run build
```

Build output: `src/questline/hud/static/` (committed / wheel-embedded).

## Screenshots

After a seeded or real Android run history:

1. **Runs** — dense dark table with infra/test columns.
2. **Run detail** — amber infra vs red test banner above the tests grid.
3. **Test detail** — step timestamps, death-point panel, screenshot/logcat links.
4. **Live** — scrolling EventBus types as a suite runs.

(Capture locally with `questline hud --open` over `.questline/store.db`.)

## CI / smoke

```powershell
uv pip install -e ".[dev,hud]"
uv run pytest tests/test_hud_api.py tests/test_hud_cli.py -q

# Playwright (Node): seed + serve, then e2e
uv run python scripts/serve_hud_smoke.py --port 8741
# other shell:
cd hud/frontend
npm ci
npx playwright install chromium
npx playwright test
```
