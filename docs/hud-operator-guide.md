# Questline through the HUD — operator guide

This guide explains **what Questline can do today** (framework phases **00–10**,
including **05b** Wire and **09b** Wire v2) and **how to exercise those capabilities
from the local HUD** (`questline hud`).

Canonical status: [`STATUS-DUAL.md`](STATUS-DUAL.md).  
HUD reference (APIs, flags, contracts): [`hud.md`](hud.md).  
Deep dives: [writing-tests](writing-tests.md), [wire-setup](wire-setup.md),
[performance](performance.md), [resilience](resilience.md), [reporting](reporting.md),
[android](android.md).

**Rule of thumb after phase 10:** prefer proving workflows in the HUD when a surface
exists. Use PowerShell / CLI for CI, scripting, and anything not yet exposed in the UI.

---

## 1. What Questline is (today)

Questline is a **local-first game-automation framework** for Unity (and mock/CI):

| Layer | What shipped | How it shows up |
|-------|----------------|-----------------|
| **Core** | Profiles (`questline.toml`), event bus, SQLite run store, artifacts | Every HUD page reads the store |
| **Drivers** | `mock` (CI), `questline` Wire (live happy path), `alttester` (legacy) | Choose via **profile** on Launch |
| **Authoring** | Pytest plugin, pages/steps, markers, quarantine ledger | Launch runs tests; Quarantine UI manages ledger |
| **Devices** | Local adb provider, device locks | Device picker on Launch |
| **Resilience** | Infra vs test verdicts, recovery, watchdog | Run/test banners + death-point tags |
| **Reporters** | console, html, slack, github_issues (+ stubs) | Toggles on Launch |
| **PerfProbe** | Time-series samples + asserts + CLI report | **Perf** graphs + compare |
| **HUD** | Viewer (08) + control center (10) | This app |

**Not in the HUD yet (use CLI / later phases):** `questline doctor`, arbitrary shell /
command palette, AI triage buttons (phase 12), Poco/UTF (phase 14), GameLens FP-G*.

---

## 2. Start the HUD

### Install (once)

```powershell
cd D:\dev\questline
uv pip install -e ".[dev,hud]"
```

### Normal operator session

```powershell
uv run questline hud --open
# Optional: point at a game store
uv run questline hud --open --store D:\Projects\ElJuegaso\.questline\store.db
```

Defaults: `http://127.0.0.1:8741/`, store from the active profile’s `.questline/store.db`.

| Flag | Meaning |
|------|---------|
| `--open` | Open the system browser |
| `--port` / `--host` | Bind (default localhost-only) |
| `--store` | Override SQLite path |
| `--config` / `--profile` | Resolve store paths from a profile |
| `--read-only` | Viewer only — no Launch / Quarantine / Profiles mutators |

### Fixture smoke (no prior runs needed)

```powershell
uv run python scripts/serve_hud_smoke.py --port 8741
```

Seeds two demo runs (`run-a`, `run-b`) with verdicts, artifacts, and perf samples —
useful for Perf compare and drill-down without a live game.

---

## 3. HUD map (pages)

| Nav | Route | Purpose |
|-----|-------|---------|
| **Runs** | `#/` | History: profile, driver, device, pass totals, infra/test counts, duration |
| **Launch** | `#/launch` | Compose and start/stop a managed pytest session |
| **Quarantine** | `#/quarantine` | Ledger add/remove + limbo audit |
| **Profiles** | `#/profiles` | Edit/validate/`questline.toml` (secrets = env **names** only) |
| **Perf** | `#/perf` | PerfProbe series + build-over-build compare |
| **Trends** | `#/trends` | Pass-rate / duration charts, flakiness, duration-vs-pass |
| **Live** | `#/live` | WebSocket stream of run events |
| *(drill)* | `#/runs/{id}` | Tests grid + infra vs test banner |
| *(drill)* | `#/runs/{id}/tests/{tid}` | Steps, death-point, artifacts, history (`tid` = pytest nodeid; may contain `/` — INC-0003) |

Mutating nav (Launch / Quarantine / Profiles) is hidden under `--read-only`.

---

## 4. Capability → how to use it in the HUD

### 4.1 Run history, verdicts, death-point, artifacts (phases 01–08)

**What it is:** Every pytest session with the Questline plugin writes runs/tests/steps
into the store. Failures are classified **infra** (session/device/transport) vs **test**
(assertions) vs **authoring** — see [resilience.md](resilience.md).

**In the HUD:**

1. Open **Runs** (`#/`). Filter by profile / status if needed.
2. Click a run → **infra vs test** banner + tests table.
3. Open a failed test → **step timeline**, **death-point** (last started step + health
   tags), **artifacts** (screenshots/logcat under the store jail).
4. History sparkline on the test page shows the same nodeid across runs.

Nodeids like `examples/wire-smoke/…::test_…` are valid drill-down ids (INC-0003). If you
see `test not found: examples`, the SPA/API build is stale — restart `questline hud` and
hard-refresh.

**Empty store?** Use **Launch** (below) or run a suite once, then refresh.

**Wrong HUD?** Before dogfood, `GET /api/meta` must show `smoke: false` and your repo
`project_root` (INC-0004 — smoke demo uses port **8742**, not 8741).

---

### 4.2 Launch a run (control center — phase 10)

**What it is:** Same public path as CLI pytest + plugin flags (`--questline-profile`,
config, device serial via env, reporters). The HUD starts a **managed subprocess**,
honors **device locks** (phase 05), and forwards live events into **Live**.

**Important:**
- **Profiles** come from `questline.toml` (and the config picker), **not** from Unity
  being open. Root repo toml includes `mock`, `editor`, `android_local`.
- **Device** is **adb only**. “(no adb pin)” is normal for **Unity Editor Wire** —
  Editor is not an adb device. Pick a serial only for `android_local`.

**In the HUD:**

1. Go to **Launch**.
2. Use a **preset** (Mock demo / Wire Editor / Wire Android) or choose **config** +
   **profile** manually.
3. For Wire Editor: check **QUESTLINE_LIVE_TARGET=1**, leave device on
   *(no adb pin)*, tests `examples/wire-smoke`.
4. Click **Launch** → **Live**. Use **Stop** to cancel.
5. Only **one** managed run at a time. If Launch is disabled or you see 409
   “already running”, use **Open Live** or **Stop** (INC-0005 — older builds could
   leave a wedged pytest if stdout was piped unread; restart HUD after upgrading).

**Suggested first dogfood (mock, no Unity):**

| Field | Value |
|-------|--------|
| profile | `mock` (or `default`) |
| tests | `examples/demo-tests` |
| reporters | `console` (optional) |

**Wire / Editor live** (happy path — [wire-setup.md](wire-setup.md)):

1. Unity Editor with companion Wire listening (`127.0.0.1:13000`).
2. In a shell (once per window): `$env:QUESTLINE_LIVE_TARGET = "1"` if your suite skips
   without it — or use a profile that does not require that env.
3. HUD **Launch** with profile `editor` / Wire config path as in
   `examples/wire-smoke/questline.toml`, tests `examples/wire-smoke`.
4. Watch **Live**; after finish, open **Runs** for screenshots (`ArtifactSaved`) and
   verdicts. There is **no separate Wire UI panel** — find/tap/screenshot land in the
   same run store as other drivers.

**Android device** ([android.md](android.md)):

1. Device online (`adb devices`).
2. **Stop Unity Editor Play** (or anything else on host `:13000`). Android uses
   `adb forward tcp:13000` — if the Editor owns that port, session setup fails in
   &lt;1s and Live only shows `RunStarted` → `RunFinished failed` with **0 tests**.
3. APK open on the phone with `[QuestlineWire] listening …` (or set
   `QUESTLINE_APK_PATH` + `QUESTLINE_APP_PACKAGE=com.eljuegaso.p1` **before** starting
   the HUD so Launch can install/cold-start).
4. Launch with preset **Wire Android**, pick **serial**, `QUESTLINE_LIVE_TARGET=1`.
5. If it fails again: Launch **Status** → `error` / `log_tail` (pytest traceback).
   Concurrent runs on the same serial are blocked by the device lock.

HUD Launch clears the repo’s pytest `addopts` (coverage gate) so live smokes are not
failed by `--cov-fail-under=85` and Status is not flooded with coverage tables.

---

### 4.3 Live event stream (phase 08 + forward in 10)

**What it is:** `EventBus` events (`RunStarted`, `TestStarted`, `Step*`, `TestFinished`,
`PerfSample`, …) fan out over WebSocket `/live`.

**In the HUD:**

- Open **Live** while a HUD-launched run is active (auto-redirect after Launch).
- For runs started **outside** the HUD, events only appear on Live if that process
  forwards to the HUD (HUD Launch sets `QUESTLINE_HUD_FORWARD_URL` automatically).

---

### 4.4 Quarantine ledger (phase 03 + HUD UI in 10)

**What it is:** Versioned `quarantine.yaml` entries (reason, owner, exit criteria,
issue). Marker `@quest.quarantined` must stay in sync — **limbo** = mismatch.
Same code path as `questline quarantine add|remove|audit`.

**In the HUD:**

1. **Quarantine** → see ledger path + entries.
2. **Add:** test_id (pytest nodeid), owner, reason, exit criteria, optional issue.
3. **Limbo audit** → summary of ledger-only / marker-only.
4. **Remove** when exit criteria are met (also remove the marker in code).

Remember: quarantined tests are **excluded by default** unless you check
**include quarantined** on Launch (or pass `--include-quarantined` on CLI).

---

### 4.5 Profiles & config (core + HUD editor in 10)

**What it is:** `[profile.<name>]` in `questline.toml` — driver, waits, resilience,
perf, reporters, android/wire targets. Secrets **never** in TOML (env only).

**In the HUD:**

1. **Profiles** → pick a name → **Load**.
2. Edit JSON fields (no `*_token` / `*_key` / secret keys).
3. **Validate** — same pydantic/`load_settings` errors as CLI.
4. **Diff preview** then **Save** when ready.
5. Secret slots are listed as env **names** only (`QUESTLINE_API_KEY`, Slack/GitHub
   tokens, …) — never values.

After saving, use the profile name on **Launch**.

---

### 4.6 Drivers & devices (phases 02, 05, 05b, 09b)

| Driver | Role | HUD usage |
|--------|------|-----------|
| `mock` | CI / demo | Launch `mock` + `examples/demo-tests` |
| `questline` (Wire) | Live Editor/Android — hooks + find/hierarchy/tap/screenshot | Launch Wire profile; inspect artifacts/steps after |
| `alttester` | Legacy remote | Only if you still need Desktop; not the €0 happy path |
| `poco` | Phase 14 | Not available yet |

Devices: **Launch → device** dropdown calls live adb discovery. No separate
“devices” page.

---

### 4.7 Resilience & infra vs test (phase 06)

**What it is:** Session loss / empty hierarchy / dead driver → **infra**; assertion
failures → **test**. Recovery ladder + watchdog (exit 140/141) — details in
[resilience.md](resilience.md).

**In the HUD:**

- Run banner splits **infra** (amber) vs **test** (red) counts.
- Failed test page shows verdict + death-point / health tags.
- Trends flakiness board helps spot unstable nodeids over time.

Tune resilience knobs in **Profiles** (`resilience.watchdog_timeout_s`, etc.).

---

### 4.8 Reporters (phase 07)

**What it is:** Bus subscribers — console, HTML under artifacts, Slack / GitHub Issues
(secrets via env). See [reporting.md](reporting.md).

**In the HUD:**

- Enable reporters with checkboxes on **Launch** (or set `reporters = [...]` in
  **Profiles**).
- HTML reports appear under the store artifacts dir; screenshots also open from test
  detail.
- Slack/GitHub still need env tokens set in the shell that started `questline hud`
  (HUD never shows secret values).

---

### 4.9 PerfProbe (phase 09 + graphs in 10)

**What it is:** Background sampling (`fps`, `memory_pss_mb`, …) into `perf_samples`.
Enable with `perf.enabled = true` in a profile. CLI: `questline perf report <run_id>`.

**In the HUD:**

1. Run a suite with perf enabled (Launch or CLI) so samples exist.
2. **Perf** → select a run → **Load series** (sparklines + avg/n).
3. Pick baseline **A** and candidate **B** → **Compare** (Δ avg + overlays).
4. **Trends** also shows **duration vs pass** correlation for flaky nodeids.

**Caution (INC-0001):** `QUESTLINE_PERF_ENABLED=true` in PowerShell overrides toml for
the whole window and can contend with Wire UI on the shared TCP port. Clear perf env
when isolating Wire debugging — see [INCIDENTS.md](INCIDENTS.md) / [performance.md](performance.md).

---

### 4.10 Trends & flakiness (phase 08 / 10)

**In the HUD → Trends:**

- Pass-rate bars across recent runs.
- Duration bars.
- Flakiness board (nodeids that both pass and fail).
- Duration-vs-pass dots (green pass / red fail per run).

---

## 5. End-to-end recipes

### A. Mock dogfood (no Unity)

1. `uv run questline hud --open`
2. **Launch** → profile `mock` → tests `examples/demo-tests` → Launch → Live → Stop (or wait).
3. **Runs** → open latest → drill a failure if any.
4. **Quarantine** optional: add a flaky nodeid, audit, remove.

### B. Fixture UI without writing a suite

1. `uv run python scripts/serve_hud_smoke.py --port 8741`
2. **Runs** → `run-a` / `run-b` → infra banner + death-point.
3. **Perf** → compare `run-a` vs `run-b`.
4. **Launch** → Start/Stop (smoke uses a fake process; does not pollute fixture runs).

### C. Wire Editor smoke

1. Editor + companion Wire on `:13000` ([wire-setup.md](wire-setup.md)).
2. Clear sticky `QUESTLINE_PERF_*` if you just dogfooded perf.
3. HUD Launch → Wire/editor profile + `examples/wire-smoke`.
4. Live → Runs → screenshots / hierarchy artifacts on the UI test.

### D. Game store (ElJuegaso)

```powershell
uv run questline hud --open --store D:\Projects\ElJuegaso\.questline\store.db
```

Browse historical automation runs; Launch still uses the HUD process’s
`questline.toml` / project root unless you start the HUD from the game repo with the
right `--config`.

### E. LAN viewer only

```powershell
uv run questline hud --host 0.0.0.0 --port 8741 --read-only
```

Others can browse Runs/Perf/Trends; mutators stay off.

---

## 6. What stays CLI-only (for now)

| Task | Command / note |
|------|----------------|
| Config doctor | `questline doctor` |
| Perf text/HTML file report | `questline perf report <run_id>` (HUD graphs are interactive equivalent) |
| Quarantine without HUD | `questline quarantine add\|remove\|audit` |
| One-off pytest outside launcher | `uv run pytest … --questline-profile …` |
| Arbitrary CLI / shell in browser | Deferred (BACKLOG) |
| AI actions on a failed run | Phase 12 |
| Poco / UTF C# results UI extras | Phase 14 (results still land in same store later) |

---

## 7. Safety checklist

- Mutating APIs: **localhost + CSRF** only.
- `--read-only` for remote viewing.
- Secrets: env names in Profiles UI; never paste tokens into toml or the JSON editor.
- Artifacts: only paths under the store `artifacts_dir` are served.
- Prefer **one** managed Launch at a time; device locks prevent double-booking a serial.

---

## 8. Quick verification checklist (HUD-first)

After starting `questline hud --open`:

- [ ] Launch mock run → Live events → Stop  
- [ ] Runs → run detail banner → test → steps / death-point / artifact  
- [ ] Perf → load series → compare two runs  
- [ ] Quarantine → add → limbo audit → remove  
- [ ] Profiles → validate bad wait → see CLI-equivalent error → discard or fix  
- [ ] Trends → flaky board / correlation populated after mixed results  

Record PR / session notes as: **Verified in HUD:** … vs **CLI-only:** ….

---

## 9. Related docs

| Doc | When you need it |
|-----|------------------|
| [hud.md](hud.md) | API tables, flags, HUD-first contract for AI sessions |
| [writing-tests.md](writing-tests.md) | Pages, steps, markers, quarantine authoring |
| [wire-setup.md](wire-setup.md) | Live Wire Editor / Android |
| [android.md](android.md) | adb, `android_local`, ports |
| [performance.md](performance.md) | Metrics, asserts, INC-0001 |
| [resilience.md](resilience.md) | Verdicts, recovery, exit codes |
| [reporting.md](reporting.md) | Reporter env secrets |
| [STATUS-DUAL.md](STATUS-DUAL.md) | What’s done / next across fw + game |
| [INCIDENTS.md](INCIDENTS.md) | Maintainer traps |
