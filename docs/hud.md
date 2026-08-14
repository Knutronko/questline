# Questline HUD — local control center

`questline hud` serves a **local-first** dashboard over your run store: history,
run/test detail (verdicts, death-point, artifacts), trends, live WebSocket view,
**run launcher**, **quarantine management**, **profile editor**, and **perf graphs**
(phase 10).

Stack decision: [ADR-0007](adr/ADR-0007-hud-frontend-stack.md).
Architecture overview: [`01-ARCHITECTURE.md`](01-ARCHITECTURE.md) §6.
**Operator walkthrough (all capabilities → HUD flows):**
[`hud-operator-guide.md`](hud-operator-guide.md).

## Evolution — what later phases add

The HUD is **incremental**. Phase 08 shipped the viewer shell (REST + SPA + live WS).
Phase 10 turns it into the **control center** (mutators + graphs). Later phases
**extend** that shell; they do not replace it. Data always lands in the **run store /
event bus first**; the HUD reads (and, from phase 10, mutates via the same public APIs
the CLI uses — no UI-only code paths).

| When | Phase | What appears in the HUD |
|------|-------|-------------------------|
| ✅ | **08** Viewer | Runs, filters, run/test detail, verdicts, death-point, artifacts, trends, live WS |
| ✅ | **09** PerfProbe | Samples → `perf_samples` / `PerfSample` events (store) |
| ✅ | **09b** Wire v2 | Richer live/automation runs. **HUD:** no dedicated Wire panel — screenshots via `ArtifactSaved`; launcher picks profile/device |
| ✅ | **10** HUD II | Launcher, quarantine UI, profile editor, **perf graphs** + run comparison, CSRF + `--read-only` |
| ❌ deferred | **FP-G1** GameLens | CLI `questline lens` only — **no HUD panel yet** (see BACKLOG). Browse after FP-G2/G3 data exists |
| ❌ deferred | **FP-G2** Telemetry | CLI `questline telemetry` only — **no HUD panel** (BACKLOG). G3 bots did not add one. |
| ❌ deferred | **FP-G3** bots | Same telemetry CLI; **no HUD panel** (explicit defer). |
| later | **11–13** AI | Cost per run / triage panels (read store `ai_calls`); GameLens AI implications after 11; action buttons with 12 |
| later | **14** Poco + UTF | C# UTF results in the same run store → same Runs/Test detail |

### Gap audit (05b–09b → HUD after 10)

| Capability | HUD after 10 |
|------------|--------------|
| Runs / tests / verdicts / death-point / artifacts | ✅ Viewer (08) |
| Live WS events | ✅ Auto-attach when launched from HUD (event forward) |
| Quarantine ledger | ✅ Manage in HUD (parity with CLI) |
| Profiles / `questline.toml` | ✅ Edit + validate + diff; secrets = env **names** only |
| PerfProbe series | ✅ Graphs + compare two runs |
| Wire / drivers / devices | ✅ Launcher profile + device picker (no Wire-specific chrome) |
| Reporters | ✅ Toggles on launch |
| GameLens snapshot / diff | ❌ Deferred — CLI (`questline lens`); HUD panel after G2/G3 (BACKLOG) |
| Telemetry sessions / KPIs | ❌ Deferred — CLI (`questline telemetry`); G3 bots did not add a HUD panel (BACKLOG) |
| Command palette / arbitrary CLI | ❌ Deferred — CLI until a future BACKLOG item; not a full terminal |

If something cannot fit, defer in this evolution table + [`phases/BACKLOG.md`](phases/BACKLOG.md)
with a numbered owner phase.

## HUD-first verification (mandatory after phase 10)

**Default for humans and AI sessions:** prove acceptance via HUD flows when a surface
exists (launch mock/real run, watch live, stop, open run/perf/quarantine, edit profile).

PowerShell / `uv run pytest` / `questline …` remain valid for CI, scripting, and anything
not yet exposed in the HUD — but phase PRs must say which checks were done **in HUD** vs
CLI-only.

### Contract for future phase sessions

After phase 10, any phase that adds user-visible run/operator capability must:

1. **Expose or extend it in the HUD** when applicable (same public APIs as CLI — no
   UI-only paths).
2. **Include HUD verification** in the PR test plan / Self-review
   (`Verified in HUD: …`).
3. **If HUD UI is deferred**, say so explicitly in the brief + this evolution table +
   BACKLOG with an owner phase. Do not leave new operator workflows PowerShell-only by
   default.

Paste into phase prompts:

```
If this phase adds store/event data or operator workflows users should see, extend
questline hud (API + SPA + docs/hud.md + tests) or explicitly defer UI to a later phase
in the brief / BACKLOG. Prefer HUD verification in the PR Self-review
(Verified in HUD: …). Keep STATUS/INCIDENTS paste from docs/phases/README.md.
```

Store/bus integration rules (still mandatory):

1. **Store/bus first** — persist incrementally; HUD never invents verdicts or metrics.
2. **Extend, don’t fork** — new REST under `/api/…`, new SPA routes beside the hash
   router; rebuild `hud/frontend` → `src/questline/hud/static/` when the SPA changes.
3. **Document** — update this file + [`STATUS-DUAL.md`](STATUS-DUAL.md) when status changes.
4. **Test** — TestClient + Playwright when there is a new drill-down / control flow.
5. **Safety** — allow-listed exports; artifact paths under `artifacts_dir`; mutating APIs
   stay localhost + CSRF / `--read-only`.

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
questline hud --read-only   # viewer only (phase-08 behavior; safe on --host LAN)
```

Defaults:

| Flag | Default | Notes |
|------|---------|-------|
| `--host` | `127.0.0.1` | Opt-in for non-localhost binds |
| `--port` | `8741` | |
| `--open` | off | Opens the system browser |
| `--store` | profile `store.db` | Under `.questline/` |
| `--read-only` | off | Disables launcher / quarantine / config mutators |

Empty store → API returns `{ "runs": [], "empty": true }` and the UI shows a clear
empty state (not an error).

## Pages

| Route | Content |
|-------|---------|
| `#/` | Runs table — profile, driver, device, pass totals, infra/test split, duration |
| `#/launch` | Compose + start/stop a managed pytest session (profile, tests, device, reporters) |
| `#/quarantine` | Ledger list; add/remove; limbo audit |
| `#/profiles` | Edit `questline.toml` profiles (validate + diff preview); secrets = env names |
| `#/perf` | PerfProbe series graphs + build-over-build compare |
| `#/runs/{id}` | Tests grid + **infra vs test** banner |
| `#/runs/{id}/tests/{tid}` | Step timeline, death-point, artifacts, history sparkline (`tid` may be a pytest nodeid with `/`) |
| `#/trends` | Pass-rate / duration charts, flakiness board, duration-vs-pass correlation |
| `#/live` | WebSocket stream (`/live` or `/api/live`) of EventBus (+ forwarded) events |

## API (local)

### Read (viewer)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/health` | Liveness |
| GET | `/api/meta` | `read_only`, paths, known reporters |
| GET | `/api/runs` | List + `profile` / `status` filters |
| GET | `/api/runs/{id}` | Run detail + tests + verdict banner |
| GET | `/api/runs/{id}/tests/{tid}` | Steps, death-point, artifacts, history (`{tid:path}` — slash-safe nodeids) |
| GET | `/api/runs/{id}/artifacts` | Artifact list (allow-listed fields) |
| GET | `/api/artifacts/file?path=` | File bytes — **only** under store `artifacts_dir` |
| GET | `/api/trends` | Aggregations |
| GET | `/api/perf/{run_id}` | Perf series + summary |
| GET | `/api/perf/compare?a=&b=` | Build-over-build deltas + series |
| GET | `/api/perf/correlation` | Duration-vs-pass points for flaky board |
| GET | `/api/devices` | Live adb device list |
| GET | `/api/profiles` | Profile names |
| GET | `/api/profiles/{name}` | Public fields + secret env names |
| GET | `/api/quarantine` | Ledger entries |
| GET | `/api/launcher` | Managed-run status |
| GET | `/api/csrf` | Issue CSRF cookie + token |
| WS | `/live` | Live event fan-out |

### Mutating (localhost + CSRF; disabled with `--read-only`)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/launcher/start` | Start managed pytest subprocess |
| POST | `/api/launcher/stop` | Graceful cancel |
| POST | `/api/quarantine` | Add/update ledger entry (same as CLI) |
| DELETE | `/api/quarantine?test_id=` | Remove entry |
| POST | `/api/quarantine/audit` | Limbo audit |
| POST | `/api/profiles/{name}/validate` | Validate with pydantic `load_settings` |
| POST | `/api/profiles/{name}` | Diff preview (`apply=false`) or save |
| POST | `/api/live/ingest` | Forwarded events from HUD-launched pytest |

Mutators require cookie `questline_csrf` matching header `X-CSRF-Token`. Non-loopback
clients receive 403 on mutators.

Secrets never appear in the HUD (env **names** only). Artifact paths are constrained to
the store artifacts directory (path traversal → 403).

## HUD Cómo probarlo

PowerShell only to start the server:

```powershell
uv pip install -e ".[dev,hud]"
uv run questline hud --open
# or fixture smoke:
uv run python scripts/serve_hud_smoke.py --port 8742
```

Then in the browser:

1. **Launch** → pick profile `mock` → Launch → confirm redirect to **Live** → **Stop**.
2. **Runs** → open a run → test detail (verdicts / death-point / artifacts).
3. **Perf** → load series → Compare two runs (fixture smoke has `run-a` / `run-b`).
4. **Quarantine** → add a nodeid → Limbo audit → remove.
5. **Profiles** → load → Validate (invalid wait → same errors as CLI) → Diff preview.
6. Optional maintainer: Launch against a real device (profile + serial); watch Live; stop.

**Verified in HUD vs CLI:** note which of the above you clicked vs which you only ran via
`pytest` / `questline` in the PR Self-review.

## Frontend rebuild (maintainers)

Node is only needed to change the SPA:

```powershell
cd hud/frontend
npm ci
npm run build
```

Build output: `src/questline/hud/static/` (committed / wheel-embedded).

## Maintainer deeper checks

1. **Real store** — `questline hud --open --store D:\Projects\ElJuegaso\.questline\store.db`
2. **HUD-launched live** — Launch from `#/launch` (not a second terminal); Live should
   show forwarded `TestStarted` / `Step*` / `TestFinished`.
3. **`--read-only`** — mutator nav hidden / APIs 403; useful with `--host` on LAN.
4. **Infra vs test banner** — same as phase 08.
5. **Perf compare** — two real runs with `perf.enabled` samples.

## CI / smoke

```powershell
uv pip install -e ".[dev,hud]"
uv run pytest tests/test_hud_api.py tests/test_hud_cli.py tests/test_hud_control.py tests/test_hud_queries.py -q

# Playwright (Node): seed + serve, then e2e
uv run python scripts/serve_hud_smoke.py --port 8742
# other shell:
cd hud/frontend
npm ci
npx playwright install chromium
npx playwright test
```
