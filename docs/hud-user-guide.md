# Questline HUD — human guide

This is the **button-by-button** guide for someone who has not used Questline
before. It describes what you see in the browser, what each control does, and
what a **live Ask** should look like.

Technical APIs and flags: [`hud.md`](hud.md).  
Capability → HUD recipes (operators who already know the stack):
[`hud-operator-guide.md`](hud-operator-guide.md).  
AI keys / profiles: [`ai-setup.md`](ai-setup.md).

---

## 1. What this app is

Questline is a **local** automation console for a Unity game (and a mock driver
for demos). Tests write results into a SQLite **store**. The HUD is a web UI
over that store.

You use it to:

| Goal | Page |
|------|------|
| See past test runs and why they failed | **Runs** |
| Start / stop a test session | **Launch** |
| Park a flaky test so the suite skips it | **Quarantine** |
| Edit `questline.toml` profiles (no secrets) | **Profiles** |
| Compare FPS / memory across two runs | **Perf** |
| Browse balance snapshots and ask “what should we retune?” | **GameLens** |
| Write steps → AI pytest + gate | **Generate** |
| See agent eval scores (diagnosis / false-green) | **Eval** |
| See pass-rate and flaky tests over time | **Trends** |
| Watch events while a run is in progress | **Live** |

It does **not** replace Unity, does not write game ScriptableObjects, and does
not decide ship / no-ship. AI text is labeled **model reasoning**. Numbers come
from the store (**measured**).

Default URL: `http://127.0.0.1:8741/`.

---

## 2. Which HUD did I open?

Look at the **top bar**. Three badges can appear:

| Badge / banner | Meaning | What to do |
|----------------|---------|------------|
| **SMOKE** + yellow “SMOKE FIXTURE SERVER” | Demo server. Seeded fake runs. **Launch is fake.** **Ask is a scripted fake LLM** (no API key). | Fine for learning the UI. For real tests or live Groq/Ollama: **Ctrl+C** that process, then `uv run questline hud --open`. |
| **RO** | Started with `--read-only`. Browse only. | Launch / Quarantine / Profiles / Ask are hidden or disabled. |
| **STALE HUD PROCESS** | Browser JS is newer than the Python process (old `questline hud` still running). | Stop the old process, start again from `D:\dev\questline`, hard-refresh the tab. |

**Two common start commands** (do not run both on the same port):

```powershell
cd D:\dev\questline

# A — learn the UI (fake data, fake Ask)
uv run python scripts/serve_hud_smoke.py --port 8741
# then open http://127.0.0.1:8741/  (this script does not open a browser)

# B — real store + live Ask (same PowerShell window as your API key)
$env:GROQ_API_KEY = "paste-real-key"   # skip this line for Ollama-only
uv run questline hud --open
# optional game store:
# uv run questline hud --open --store D:\Projects\ElJuegaso\.questline\store.db
```

If start B fails with “port already in use”, the smoke process is still up —
Ctrl+C it first. If smoke fails with *file in use* on `store.db`, another
Python still holds `.questline-hud-smoke\store.db` (often an old smoke on
port **8743**).

Confirm real HUD: `http://127.0.0.1:8741/api/meta` should show `"smoke": false`.

---

## 3. Top navigation

| Link | What it is |
|------|------------|
| **Questline HUD** (logo) | Back to the Runs list. |
| **Runs** | History of pytest sessions stored in this SQLite file. |
| **Launch** | Compose and start one managed test process. Hidden in read-only. |
| **Quarantine** | Skip-list (`quarantine.yaml`) for flaky tests. Hidden in read-only. |
| **Profiles** | Edit named configs (`mock`, `editor`, `ai_groq`, …). Hidden in read-only. |
| **Perf** | Time-series graphs from PerfProbe samples. |
| **GameLens** | Balance snapshots, typed diff, telemetry sessions, balance **Ask**. |
| **Generate** | Write test steps; AI writes pytest; the gate runs it. |
| **Eval** | Golden harness scores (diagnosis / false-green). |
| **Trends** | Pass-rate / duration / flakiness across recent runs. |
| **Live** | Live event stream (useful right after Launch). |

There is **no** separate Wire / Unity panel. Live game work is: pick a Wire
profile on Launch → watch Live → inspect screenshots on the test page.

---

## 4. Runs

**What for:** “What ran, did it pass, was the failure the game or the lab?”

### List (`#/`)

| Control | What it does |
|---------|----------------|
| **profile** | Filter by profile name (`mock`, `editor`, …). Empty = all. |
| **status** | `any` / `passed` / `failed` / `running` / `error`. |
| **Filter** | Applies the two fields (updates the URL hash). |
| **Launch run** | Shortcut to Launch. |
| Row **Run** link | Opens that session. The id is shortened (`a4c2cbe7…`). |

Columns:

- **Driver** — `mock` (no game), `questline` (Wire / live Unity), `alttester` (legacy).
- **Device** — adb serial, or empty for Editor.
- **Pass** — passed / total tests.
- **Infra** — lab failures (device, Wire, session setup). Amber in the detail banner.
- **Test** — assertion / gameplay failures. Red in the detail banner.

Empty store: use **Launch** once, or point `--store` at a game DB that already
has runs.

### Run detail (`#/runs/{id}`)

Banner counts:

| Tile | Meaning |
|------|---------|
| **passed** | Tests that passed. |
| **failed** | Tests that failed (any reason). |
| **infra** | Failed because the *harness* died (no device, Wire down, empty session). |
| **test** | Failed because the *game/assertion* failed. |
| **authoring** | Failed because the test was written against the wrong API. |

**AI calls** table (phase 11): each LLM ping for this run — provider, model,
tokens in/out, **estimated** USD (not an invoice), outcome, purpose. No API
keys. Empty until something actually called an LLM in that run.

**Tests** table: click a **nodeid** (pytest path) to drill in. **Death step** is
the last step that started before the failure.

If the run failed, **Triage this run** clusters failures (read-only). Results
attach to the run (`verdict` / `cause` / clusters). The model does **not** own
green/red.

If the run failed with **no tests**, session setup died before pytest collected
anything (typical: Editor still owning port 13000 while you wanted Android, or
adb lock). Check Launch → **Status** `error` / `log_tail`.

### Test detail

| Block | What it is |
|-------|------------|
| **Death point** | Last started step + error + driver health. The place to start debugging. |
| **History** | Sparkline of the *same* nodeid across previous runs (pass/fail height). |
| **Step timeline** | Ordered steps with status and error text. |
| **Artifacts** | Screenshots / logs written under the store jail. Click to open. |

Failed tests also show **Diagnose this test** (default, read-only) and **Fix this
test** (opt-in confirm; the gate re-runs pytest). **Suggest locator** appears on
`ElementNotFoundError` and never writes `locators.yaml`.

**Verdict words you will see**

| Verdict | Human meaning |
|---------|----------------|
| `test` | The check failed; the lab was healthy. |
| `infra` | The lab failed (connection, device, empty hierarchy). Not “the game lost”. |
| `authoring` | The test called something Questline does not support that way. |

---

## 5. Launch

**What for:** start the same kind of pytest session you would run in a
terminal, without leaving the browser.

**Smoke HUD:** Launch starts a **fake** process. Use it only to see Live
events. It does not write new real runs into the fixture store.

| Control | What it does |
|---------|----------------|
| Preset **Mock demo** | No Unity. Profile `mock`, tests `examples/demo-tests`. First dogfood. |
| Preset **Wire Editor** | Unity Play + companion Wire on `127.0.0.1:13000`. Device stays empty (normal). Checks **QUESTLINE_LIVE_TARGET**. |
| Preset **Wire Android** | Dev APK + adb. Pick a **serial** if more than one phone/emulator. |
| **config** | Which `questline.toml` to read. Changing it reloads **profile**. |
| **profile** | Named settings block (`mock`, `editor`, `android_local`, …). Comes from the toml, **not** from “is Unity open?”. |
| **device** | adb serial only. `(no adb pin — OK for Editor)` is correct for Wire Editor. |
| **Refresh devices** | Re-run `adb devices`. |
| **markers** | Optional pytest `-m` expression. Leave empty unless you know markers. |
| **tests** | One path or nodeid per line. |
| Reporter checkboxes | `console` / `html` / `slack` / `github_issues`. Slack/GitHub need env tokens in the **shell that started the HUD**. |
| **include quarantined** | Run tests that are on the skip-list too. Off by default. |
| **QUESTLINE_LIVE_TARGET=1** | Required for `examples/wire-smoke` (those tests skip without it). |
| **Launch** | Starts **one** managed subprocess and jumps to **Live**. Disabled if a run is already going. |
| **Stop** | Cancels the managed run. |
| **Open Live** | Appears while a run is busy. |
| **Status** | JSON of the launcher (`idle` / `starting` / `running` / `stopping` / `error`, plus `log_tail`). |
| **Unity Editor** chip | CLI present or missing, Editor running, Play on/off, Pipeline yes/no/unknown. Project name only (no home path). |
| **Ensure Editor** | Same as `questline unity ensure-editor`: open the profile project, enter Play, wait for Wire on `:13000`. Disabled in read-only. If the CLI is missing, it tells you to press Play yourself. |

Rules of thumb:

- Only **one** HUD-launched run at a time. 409 “already running” → Open Live or Stop.
- For a **game suite**, start the HUD with `--project-root` at `automation/` so presets use that `questline.toml` (`editor` / `android_local`) instead of `examples/wire-smoke`.
- For Android: **stop Unity Play** first. Editor and the phone both want host port `:13000`.
- Profiles are not “Unity projects”. They are rows in `questline.toml`.

---

## 6. Live

**What for:** watch the run *while* it is happening.

| Control | What it does |
|---------|----------------|
| Badge `connecting…` / `live` / `closed` / `error` | WebSocket health. You want **live**. |
| **Clear** | Empties the log on screen. Does not stop the run. |

Lines look like `RunStarted`, `TestStarted`, `Step*`, `TestFinished`,
`PerfSample`. Newest at the top.

Events appear here when the run was started **from this HUD** (it forwards
automatically). A pytest you started in another terminal will **not** show up
unless that process was told to forward to this HUD.

---

## 7. Quarantine

**What for:** park a flaky test so the default suite skips it, with an owner
and an exit condition. Same file the CLI uses (`quarantine.yaml`).

Quarantined tests stay skipped unless Launch has **include quarantined**
checked.

| Control | What it does |
|---------|----------------|
| **test_id** | Full pytest nodeid (`path::test_name`). |
| **owner** | Who owns the flake. |
| **reason** | Why it is parked. |
| **exit** | What must be true before you remove it. |
| **issue** | Optional ticket id. |
| **Add to ledger** | Writes the row. Also keep `@quest.quarantined` in code in sync. |
| **Limbo audit** | Reports ledger-only vs marker-only mismatches (summary in the log box). |
| **Remove** (per row) | Deletes that ledger entry. Also remove the marker in code. |

---

## 8. Profiles

**What for:** inspect and edit `[profile.<name>]` in `questline.toml` without
hand-editing TOML. Used by Launch and by GameLens **Ask**.

| Control | What it does |
|---------|----------------|
| **profile** dropdown | Which named block to edit (`mock`, `ai_groq`, …). |
| **Load** | Fills the JSON box from disk. |
| **Validate** | Same checks as the CLI. Does **not** write. A bad wait value should error. |
| **Diff preview** | Shows what would change. Does **not** write. |
| **Save** | Writes the toml. Confirm the diff first. |
| JSON textarea | Public fields only. |
| **Secret env slots** | Names such as `GROQ_API_KEY` — **never** the values. Put keys in the environment of the HUD process, not here. |

Do not paste tokens into the JSON. Do not add keys named `*_token` / `*_key`.

After Save, use that profile name on **Launch** or in GameLens **Ask**.

---

## 9. Perf

**What for:** “Did this build hitch more than last week?” Same samples as
`questline perf report`, graphed.

Runs only have series if the profile had `perf.enabled = true` when they ran.

| Control | What it does |
|---------|----------------|
| **run** + **Load series** | Sparklines per metric (`fps`, `memory_pss_mb`, …) with avg and sample count. |
| **A (baseline)** / **B** + **Compare** | Table of Δ average + overlay of the two series. |

If the page is empty, the selected run has no samples — enable perf on a
profile and Launch again (or use the smoke fixture, which seeds two runs).

---

## 10. Trends

**What for:** stability over the last ~50 runs. No buttons — it is a dashboard.

| Block | What you are looking at |
|-------|-------------------------|
| **Pass rate** | One bar per run. Hover text: id, %, duration. Red-tinted if that run had failures. |
| **Duration** | How long each run took. |
| **Flakiness board** | Nodeids that both passed and failed. **Flake** is that mix, not “the game lost”. |
| **Duration vs pass** | Green dot = pass, red = fail, for the same flaky nodeids. |

---

## 11. GameLens

**What for:** balance **config truth** (snapshots) next to **measured play**
(telemetry) and an agent that proposes **what a human should look at** — not
what number to write into a ScriptableObject.

Sub-nav inside GameLens: **Snapshots** · **Diff** · **Sessions** · **Agent**.

### Snapshots

Table of imported balance snapshots (`id`, game version, feature, created).

| Control | What it does |
|---------|----------------|
| **A** / **B** | Which two snapshots to compare. |
| **Open typed diff** | Goes to Diff for that pair. |

No snapshots = empty store (wrong `--store`, or you are on a HUD that never
imported a GameLens pack). Smoke seeds `1.0.0` and `1.1.0`.

### Diff

Typed entries grouped by **system** (added / removed / changed fields). This is
config delta, **not** a pass/fail.

**Implications** (if a batch report was persisted earlier):

| Block | Trust |
|-------|--------|
| **Gaps** | Missing joins / KPIs. Stay listed. Never filled in. |
| **Model reasoning** | Narrative from a previous `lens diff --ai`. Opinion. |
| **Measured** | JSON from `telemetry_sessions.summary`. Facts. |

### Ask balance agent (on the Diff page)

This is the interactive copilot. It only **reads** the store.

| Control | What it does |
|---------|----------------|
| **profile** | Which AI profile to use. Prefer **`ai_groq`**. Use **`ai_ollama`** for local / zero cost. Do **not** pick `ai_mistral` until a La Plateforme key exists. |
| **question** | What you want prioritized. Default: *What should a human look at for a retune?* |
| **Ask** | Runs the agent (CSRF mutator). Disabled in `--read-only`. Status line shows `running…` then `status=ok` (or `error` / `skipped`). |

**Smoke Ask** answers from a scripted fake. Good for seeing the layout.
**Live Ask** needs the real HUD (`smoke: false`), a key or a running Ollama,
and the env var set in the **same** PowerShell that launched `questline hud`.

### What a live Ask must show

After **Ask**, a panel appears under the form (same shape as **Agent →** a
turn):

```
status=ok · framing=model reasoning · cost_usd=<number>
```

| Section | What you should see | What you must not see |
|---------|---------------------|------------------------|
| **Priorities (model reasoning)** | Short **English** bullets: “look at X because measured Y changed”. Opinion. | Green/red, pass/fail, ship/no-ship, “write this SO field to 12”. |
| **Gaps** | Explicit holes, e.g. `snap-unset`, `combat.damage`, unjoined sessions. | Invented KPI values “to fill the gap”. |
| **Measured citations** | JSON copied from the store (session summaries the tools actually read). | Numbers that appear only in the prose and not in this JSON. |
| **cost_usd** | Groq: a small **estimate** (not a bill). Ollama: **0**. | A secret or a raw home path. |

Also:

- `outcome=lose` on a bot session is **measured play** (the run finished and
  lost). It is **not** “the bot/framework failed”.
- `config_snapshot_id=snap-unset` means those sessions **cannot** be joined to
  a snapshot. The agent should say that, not pretend they belong to version
  1.1.0.
- `framing=model reasoning` is the label that this text is not measured.

Then open **Agent**: a new row with your question. Click the id to reopen the
same panel.

If Ask errors: `questline doctor -p ai_groq` (or `ai_ollama`) in **that**
shell; confirm no SMOKE banner; confirm you are not `--read-only`; confirm the
store has at least two snapshots.

Ollama `llama3.2` often completes the path but is weak at keeping gaps
separate from missing KPIs. Prefer Groq for a readable retune list.

### Sessions

List of telemetry playthroughs.

| Column | How to read it |
|--------|----------------|
| **Outcome** | `lose` / `win` / … from play. `lose` ≠ infra fail. |
| **Snapshot** | GameLens snapshot id used when the bot ran. `snap-unset` = join gap. |
| **Policy** / **Seed** | Which bot policy and RNG seed. |
| **Notes** | Operator notes from the session. |

Click an id → **Summary (measured)** JSON (the facts the agent is allowed to
cite).

### Agent

History of Ask turns. Empty until you Ask from a Diff. Click a row to see
priorities / gaps / citations again.

---

## 12. Generate tests

**What for:** “I write the steps, Questline writes a pytest using this HUD’s pages/locators.”

Page: `#/generate`. Point the HUD at the **game suite** (not the questline repo cwd):

```powershell
uv run questline hud --open `
  --config D:\Projects\ElJuegaso\automation\questline.toml `
  --project-root D:\Projects\ElJuegaso\automation
```

Confirm **no** SMOKE banner. The model reads `pages/`, `locators.yaml`, and existing suites — **not** Unity C#.

| Control | What it does |
|---------|----------------|
| **Steps / spec** | Plain text or Markdown. Chips **Ping**, **Combat + amount**, and **Blank** replace the box. With `pages/` present, the box starts as the filled combat example (ping, then level 1 / amber 50). Per-step `expect:` lines are for you; the gate reads the final `expect: green` or `expect: red`. Live steps should match **hooks/pages that exist**. UI find/tap is deferred until Poco — Generate must still call Page hooks for the outcome (`ensure_in_combat`, `get_amber`), not `pytest.skip` (INC-0015). Never `from questline_ctx import` (INC-0014). “Tap Play / coins 100” is the mock demo, not the reference game. |
| **dest** | Folder under the HUD project root (`suites` when that folder exists, else `generated-tests`). Each Generate writes a **new** `test_gen_<id>.py`. Live models must `write_file` (markdown pytest dumps are salvaged). Collect of an existing suite file is not success. |
| **Demo (canned MockDriver)** | Smoke: checked. Real HUD: off. Writes a known-good Play→HUD MockDriver test — **no API key**, **Unity will not move**. Launch Editor/Android stay hidden. When `pages/` exist, Demo writes to `generated-tests/`, not `suites/`. |
| **Generate** | Writes the file. **Demo** then **executes** pytest. Live then **collects** only (Unity not required yet). Live without `GROQ_API_KEY` (or Ollama) returns 400 — it does **not** silently write MockDriver (INC-0011). |
| **Launch Editor** | After a **non-MockDriver** collect: Wire profile `editor`, `QUESTLINE_LIVE_TARGET=1`. Unity Play + Wire on `:13000` must already be up. Hidden on smoke and on Demo files. |
| **Launch Android** | Same file, profile `android_local`, optional adb serial. Dev APK must already be on the device. Hidden on smoke and on Demo files. |

Game `questline.toml` usually has no `[profile.ai_groq]`. Set `GROQ_API_KEY` in the
**same** PowerShell that starts `questline hud`, then restart the HUD. Collect
**accepted** is not a live green. Launch is the live run. The HUD does **not** start Unity (that is a later sidecar).

HTTP **429** from Groq is a rate limit (INC-0013), not a missing test file. Wait
about 20 seconds and Generate again. Optional: run Ollama (`llama3.2`) — the HUD
appends it as fallback after env Groq.

CLI extra: `uv run questline ai generate --spec examples/specs/buy_pack.md --demo`.

## 13. Words that confuse newcomers

| You see | It means | It does **not** mean |
|---------|----------|----------------------|
| **infra** | The lab broke. | The game balance is wrong. |
| **test** (verdict) | An assertion failed. | “AI says don’t ship.” |
| **outcome=lose** | The playthrough lost (measured). | The automation is broken. |
| **snap-unset** | No snapshot id on that session. | “Treat it as the latest version.” |
| **model reasoning** | LLM opinion, labeled. | A measured KPI. |
| **gaps** | Data we do not have. | “Impute 0” or invent combat.damage. |
| **SMOKE** | Fixture server. | Your ElJuegaso store. |
| **cost_usd** | Internal estimate for budgets. | Your Groq invoice. |

---

## 14. First 20 minutes (recommended)

1. Start **smoke** (`serve_hud_smoke.py`). Learn every page; Ask once (fake).
2. Ctrl+C. Set `GROQ_API_KEY` (or start Ollama). `uv run questline doctor -p ai_groq`.
3. `uv run questline hud --open --config D:\Projects\ElJuegaso\automation\questline.toml --project-root D:\Projects\ElJuegaso\automation`
4. Confirm **no** SMOKE banner.
5. GameLens → two snapshots → Open typed diff → profile `ai_groq` → **Ask**.
6. **Generate** → uncheck Demo → steps that match existing pages/hooks → **Generate** (collect) → **Launch Editor** (Unity Play already up).
7. Check: English priorities, gaps still listed, citations JSON, `cost_usd` set,
   turn appears under **Agent**.

---

## 15. What stays outside the HUD

| Task | Where |
|------|--------|
| `questline doctor` (ping providers) | CLI |
| Import a balance snapshot | CLI `questline lens` — see [`gamelens.md`](gamelens.md) |
| Drain telemetry files | CLI `questline telemetry` — see [`telemetry.md`](telemetry.md) |
| AI triage / diagnose / heal a failed test | HUD run/test detail (phase-12). CLI extra: `questline ai triage|diagnose|heal` — [`ai-agents.md`](ai-agents.md) |
| Eval goldens | HUD **Eval**. CLI extra: `questline ai eval` — [`ai-eval.md`](ai-eval.md) |
| Spec→test | HUD **Generate** (demo checkbox or live LLM). CLI: `questline ai generate --demo` |
| Poco / second UI backend | Not built (phase-14) |
| Command palette / arbitrary shell | Not in the HUD |

---

## 16. Safety (short)

- Mutating actions (Launch, Quarantine, Profiles, Ask) only from **localhost**
  plus a CSRF cookie. Do not expose a writable HUD on the LAN; use
  `--read-only` if others only need to browse.
- Secrets live in the environment of the HUD process. The UI shows **names**.
- Artifacts are only served from the store’s artifacts directory.
