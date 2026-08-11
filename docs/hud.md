# Questline HUD — local run viewer

`questline hud` serves a **local-first** dashboard over your run store: history,
run/test detail (verdicts, death-point, artifacts), trends, and a live WebSocket
view of the in-progress run.

This is a **viewer** (phase 08). Launching runs / quarantine UI / perf graphs
arrive in [phase 10](phases/phase-10-hud-control-center.md).

Stack decision: [ADR-0007](adr/ADR-0007-hud-frontend-stack.md).
Architecture overview: [`01-ARCHITECTURE.md`](01-ARCHITECTURE.md) §6.

## Evolution — what later phases add

The HUD is **incremental**. Phase 08 shipped the shell (REST + SPA + live WS over the
store/bus). Later phases **extend** that shell; they do not replace it. Data always lands
in the **run store / event bus first**; the HUD only *reads* (until phase 10 mutators).

| When | Phase | What appears in the HUD |
|------|-------|-------------------------|
| ✅ | **08** Viewer | Runs, filters, run/test detail, verdicts, death-point, artifacts, trends, live WS |
| next | **09** PerfProbe | Samples → `perf_samples` / `PerfSample` events (store). **No graphs yet** — phase 10 |
| after 09 | **09b** Wire v2 | Richer live/automation runs (find/tap) → more steps/artifacts in the same viewer |
| later | **10** HUD II | Launcher, quarantine UI, profile editor, **perf graphs** + run comparison |
| later | **11–13** AI | Cost per run / triage panels (read store `ai_calls`); action buttons with 12 |
| later | **14** Poco + UTF | C# UTF results in the same run store → same Runs/Test detail |

If a phase writes new observables (events, tables, artifacts) and the HUD should show
them, that phase **owns** the HUD delta (API + SPA + `docs/hud.md` + tests) **or**
explicitly defers UI to a numbered phase (as 09 defers graphs to 10) in its brief.

## Integration contract (mandatory for future phase sessions)

Before finishing a PR that adds store fields, event types, or user-visible run data:

1. **Store/bus first** — persist incrementally; HUD never invents verdicts or metrics.
2. **Extend, don’t fork** — new REST under `/api/…`, new SPA routes/pages beside the
   existing hash router; keep dark HUD CSS tokens; rebuild `hud/frontend` →
   `src/questline/hud/static/` when the SPA changes.
3. **Document** — update this file (Pages / API tables + evolution row) and, if status
   changes, [`STATUS-DUAL.md`](STATUS-DUAL.md).
4. **Test** — backend TestClient against a fixture store; extend Playwright smoke when
   there is a new drill-down path; live WS covered if new event types matter to Live.
5. **Allow-list / safety** — anything shown or exported stays allow-listed; artifact
   paths only under `artifacts_dir`; mutating APIs (phase 10+) stay localhost + CSRF /
   `--read-only` as in the phase-10 brief.
6. **Defer explicitly** — if UI is out of scope, say so in the brief (“HUD graphs → 10”)
   so the next session does not assume the viewer already shows the new data.

Paste into phase prompts when the work touches runs/results/perf/AI:

```
If this phase adds store/event data users should see, extend questline hud (API + SPA +
docs/hud.md + tests) or explicitly defer UI to a later phase in the brief / BACKLOG.
```

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

## Maintainer deeper checks (now — HUD I)

Beyond the seeded Playwright smoke, useful real workouts:

1. **Real store** — point at a game or local suite DB:
   ```powershell
   uv run questline hud --open --store D:\Projects\ElJuegaso\.questline\store.db
   # or after running demo/wire-smoke under this repo:
   uv run questline hud --open --store D:\dev\questline\.questline\store.db
   ```
2. **Live dual-terminal** — terminal A: `questline hud --open`; terminal B: run a suite
   with the questline plugin (`examples/demo-tests` or `wire-smoke` with
   `QUESTLINE_LIVE_TARGET=1`). Open `#/live` and watch `TestStarted` / `Step*` /
   `TestFinished` stream; then drill the finished run for verdicts.
3. **Infra vs test banner** — force or reuse a `SessionLostError` (infra) vs assertion
   failure (test) and confirm the run detail banner splits them (amber vs red).
4. **Trends / flaky** — run the same nodeid green then red (or vice versa) across two
   profiles; Trends → flakiness board should list it.
5. **Artifacts** — any `ArtifactSaved` under the store (screenshots/logcat) should open
   from test detail via `/api/artifacts/file` (403 outside `artifacts_dir`).
6. **Perf (after phase 09 merges)** — samples exist in SQLite / events, but **graphs wait
   for phase 10**; until then verify with `questline perf report <run_id>` (09) or SQL,
   not the SPA.

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
