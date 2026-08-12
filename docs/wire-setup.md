# QuestlineWire — Unity setup (happy-path live)

First-party live driver: TCP + NDJSON on **127.0.0.1:13000** (ADR-0005 / ADR-0008).
**No AltTester Desktop.** Dev/Editor only (`UNITY_EDITOR || QUESTLINE_DEV`).

This is the **default** live path. For legacy AltTester (Desktop hub), see
[unity-setup.md](unity-setup.md) — remote option only, not €0 happy path.

## Driver priority

| Priority | Profile `driver` | Use for |
|----------|------------------|---------|
| 1 | `"questline"` | Live Editor / Android — hooks + **Wire v2 UI** (find/hierarchy/tap/screenshot) |
| 2 | `"poco"` (phase-14) | Second UI backend / richer stacks |
| 3 | `"alttester"` | Legacy only — needs Desktop |
| — | `"mock"` | CI / unit |

## Game bootstrap (any Unity project)

1. Install / refresh `com.questline.companion` (git UPM or embedded copy).
2. Register hooks as today (`QuestlineHooks.Register…`).
3. Start Wire (**do not** also bind AltTester on the same port):

```csharp
#if UNITY_EDITOR || QUESTLINE_DEV
using Questline.Companion;

void Awake()
{
    QuestlineHooks.Clear();
    QuestlineHooks.Register("Ping", () => "pong", feature: "smoke");
    // … game hooks …
    QuestlineWireServer.EnsureStarted(13000);
}
#endif
```

4. Console should log: `[QuestlineWire] listening on 127.0.0.1:13000 (v2)`.
5. `hello` advertises `"protocol_version": 2` and `"features": ["hooks","ui"]`.
   Older companions (v1 / no `ui`) → clear `AuthoringError` on UI ops; hooks still work.

## Find / tap (Wire v2)

```python
from questline.drivers.locators import Locator, LocatorStrategy
from questline.core.waits import WaitPolicy

# Immediate
el = driver.find(Locator(by=LocatorStrategy.NAME, value="OkButton"))
driver.tap(el)

# Wait budget
el = driver.find(
    Locator(by=LocatorStrategy.ID, value="btn_ok"),
    WaitPolicy(probe=0.5, deadline=5.0, interval=0.2),
    budget="deadline",
)

# Hierarchy snapshot (capped depth/nodes on companion)
snap = driver.hierarchy()
png = driver.screenshot()  # non-empty PNG bytes
```

Locator strategies: `id` (Unity instance id), `name`, `path`, `text` (UGUI/TMP),
`component` (type name) + optional `scope` (path substring).
`press` / `swipe` / `text_input` stay explicit `AuthoringError` (deferred / hooks).

## Python smoke (Editor)

```powershell
cd D:\dev\questline   # repo root — not $HOME
$env:QUESTLINE_LIVE_TARGET = "1"
uv pip install -e ".[dev]"
uv run pytest examples/wire-smoke -q -o addopts= `
  --questline-profile editor `
  --questline-config examples/wire-smoke/questline.toml
```

Includes hooks + **UI** (`test_wire_v2_hierarchy_find_tap`). No `[alttester]` extra.
Profile key: `driver = "questline"`.

### PowerShell env footgun (INC-0001)

`QUESTLINE_PERF_*` from a prior PerfProbe dogfood **survives for the life of that
PowerShell window** and overrides toml. PerfProbe then shares the Wire socket with
tests → stolen NDJSON replies (hooks/UI see `GetPerfSample` / `fps` payloads).

Before Wire-only smoke:

```powershell
Remove-Item Env:QUESTLINE_PERF_ENABLED, Env:QUESTLINE_PERF_SOURCE, Env:QUESTLINE_PERF_INTERVAL_S -ErrorAction SilentlyContinue
Get-ChildItem Env:QUESTLINE*   # sanity
```

See [`INCIDENTS.md`](INCIDENTS.md) · [INC-0001](incidents/INC-0001-wire-perf-socket-race.md).
Transport locks requests after the 09b fix; still clear env when isolating UI.

## Android

`LocalAdbProvider` + **`adb forward tcp:13000 tcp:13000`** (host→device). Wire listens
**on the device**; do **not** use `adb reverse` for `driver = "questline"` (reverse
steals device `:13000` → `Address already in use`).
APK must be built with `QUESTLINE_DEV` so `QuestlineWireServer` (+ Wire UI) is compiled in.
See [android.md](android.md) and [examples/wire-smoke/questline.toml](../examples/wire-smoke/questline.toml).

```powershell
$env:QUESTLINE_LIVE_TARGET = "1"
$env:QUESTLINE_ADB_PATH = "path\to\platform-tools\adb.exe"   # if adb not on PATH
$env:QUESTLINE_APK_PATH = "path\to\dev.apk"
$env:QUESTLINE_APP_PACKAGE = "com.example.game"
$env:QUESTLINE_APP_ACTIVITY = "com.unity3d.player.UnityPlayerGameActivity"
uv run pytest examples/wire-smoke -q -o addopts= `
  --questline-profile android_local `
  --questline-config examples/wire-smoke/questline.toml
```

Mono + ARMv7 Dev APKs may show a one-shot Android **DeprecatedAbi** / “version not
supported” system dialog on 64-bit phones — session auto-dismisses; see
[android.md](android.md) troubleshooting.

**Android Wire v2 UI** smoke is optional until game **QL-2c** (companion refresh + Dev APK).

## Wire roadmap (formal)

| Stage | Scope | Status |
|-------|--------|--------|
| **MVP (05b)** | connect / alive / app_state / hooks_manifest / call_hook / soft-reload | ✅ |
| **Editor live** | `examples/wire-smoke` + reference game QL-2b | ✅ |
| **Android live** | Rebuild Dev APK with Wire; `android_local` smoke | ✅ |
| **Wire v2 UI (09b)** | find / hierarchy / tap / screenshot — [ADR-0008](adr/ADR-0008-wire-v2-ui.md) | ✅ |
| **Play gestures (09c)** | swipe / drag / long-press — only if FP-G3 gate fails | ⬜ parked |

Wire is the **happy-path** Unity transport (hooks + UI). **Poco** (14) is the
**second** UI adapter. Bots/GameLens: prefer hooks + Tap; see
[BALANCE-AUTOMATION.md](BALANCE-AUTOMATION.md) §5 and
[phase-09c](phases/phase-09c-wire-play-gestures.md).

## Reference game (ElJuegaso) — QL-2b ✅ → **QL-2c** next

Bootstrap already calls `QuestlineWireServer.EnsureStarted(13000)` and skips AltTester
host when `UseQuestlineWire = true`. Companion embed includes `QuestlineWireServer.cs`.

| Path in questline | Action in game |
|---|---|
| `unity-package/Runtime/QuestlineHooks.cs` | Keep in sync on API changes |
| `unity-package/Runtime/QuestlineWireServer.cs` | Embedded (QL-2b); refresh for v2 |
| `unity-package/Runtime/QuestlineWireUi.cs` | **New (09b)** — sync in **QL-2c** |
| `unity-package/Runtime/Questline.Companion.asmdef` | `UNITY_EDITOR \|\| QUESTLINE_DEV` |
| `unity-package/package.json` | Sync version notes |

**QL-2c:** copy/refresh companion (include `QuestlineWireUi.cs`), Editor verify find/tap,
rebuild `QUESTLINE_DEV` APK for Android. Framework `examples/wire-smoke` UI case is green
in Editor once the companion is refreshed.
