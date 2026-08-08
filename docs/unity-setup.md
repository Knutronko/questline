# Unity setup — legacy AltTester (optional)

> **Happy-path live is QuestlineWire** — see [wire-setup.md](wire-setup.md) first.
> This document is for the **legacy remoto** AltTester path only (needs Desktop hub;
> not €0). Prefer **Poco** (phase-14) when you need UI hierarchy instead of AltTester.

Step-by-step for adding **legacy** AltTester UI automation to a Unity game (Editor play
mode and Windows standalone).

**Reference game note:** QL-1 installed AltTester; **QL-2b** switched live to Wire.
Do **not** treat Desktop reconnect as DoD.

## Prerequisites

- Unity 2021.3+ (or whatever your game already uses)
- Python 3.11+ with [uv](https://github.com/astral-sh/uv)
- This repo checked out; optional extra: `questline[alttester]`

```bash
uv venv
uv pip install -e ".[dev,alttester]"
```

## 1. Install AltTester Unity SDK

1. Open your game project in the Unity Editor.
2. Install the **AltTester Unity SDK** via the method AltTester documents for your version
   (UPM git URL or `.unitypackage` from https://alttester.com/docs/sdk/latest/).
3. Add the **AltTester Prefab** to your bootstrap / first-loaded scene (required for the
   instrumentation server to start in play mode and in instrumented builds).
4. Keep the default driver port **13000** unless you change it everywhere (Python
   `ConnectionTarget.port` / `target_port` in `questline.toml`).

## 2. Install `com.questline.companion`

From this repo, the UPM package lives at `unity-package/` (`package.json` name
`com.questline.companion`).

**Option A — local path (recommended while developing questline):**

1. Unity → Window → Package Manager → **+** → **Add package from disk…**
2. Select `unity-package/package.json` from your questline checkout.

**Option B — git URL** (when the package is referenced from a published commit):

```
https://github.com/Knutronko/questline.git?path=unity-package#<commit>
```

Confirm the assembly `Questline.Companion` compiles with no errors.

## 3. Register first hooks

In a game bootstrap `MonoBehaviour` (debug/dev builds only if you prefer):

```csharp
using Questline.Companion;
using UnityEngine;
using UnityEngine.SceneManagement;

public class QuestlineHookBootstrap : MonoBehaviour
{
    void Awake()
    {
        QuestlineHooks.Register("Ping", () => "pong", feature: "smoke");
        QuestlineHooks.RegisterAction("SkipTutorial", () => { /* your cheat */ });
        QuestlineHooks.Register<int>("SetLevel", level =>
        {
            /* your cheat */ return null;
        }, argName: "level", feature: "progression");

        // Soft reload: handler performs the reload; Python re-handshakes automatically.
        QuestlineHooks.RegisterAction("ReloadActiveScene", () =>
        {
            var scene = SceneManager.GetActiveScene();
            SceneManager.LoadScene(scene.name);
        }, causesSoftReload: true);
    }
}
```

Contract details: [ADR-0004](adr/ADR-0004-companion-hooks.md).

## 4. Smoke scene objects (optional but required for `examples/unity-smoke`)

Add empty GameObjects (stable names):

| Name | Role |
|------|------|
| `QuestlineSmokeRoot` | Hierarchy root marker |
| `QuestlineSmokeButton` | UI Button the smoke suite taps |

Any game with AltTester + companion + these names can run the generic smoke suite.

## 5. Editor play mode — first green

1. Enter **Play** in the Editor (AltTester server listening).
2. From the questline repo:

```bash
# Windows PowerShell
$env:QUESTLINE_LIVE_TARGET = "1"
uv run pytest examples/unity-smoke -q -o addopts= `
  --questline-profile editor `
  --questline-config examples/unity-smoke/questline.toml
```

3. Conformance (live half):

```bash
$env:QUESTLINE_LIVE_TARGET = "1"
uv run pytest tests/test_alttester_conformance_live.py -q -o addopts=
```

Without `QUESTLINE_LIVE_TARGET=1`, those tests are skipped (CI stays green on mocks).

## 6. Windows standalone build

1. Build a **Development** Windows standalone with AltTester included (same as AltTester's
   instrumented-build docs for your SDK version).
2. Launch the `.exe`; confirm port 13000 is reachable on localhost.
3. Run smoke with the `standalone` profile:

```bash
$env:QUESTLINE_LIVE_TARGET = "1"
uv run pytest examples/unity-smoke -q -o addopts= `
  --questline-profile standalone `
  --questline-config examples/unity-smoke/questline.toml
```

## 7. Soft-reload handshake check

1. Ensure `ReloadActiveScene` (or any hook with `causesSoftReload: true`) is registered.
2. Call it from Python:

```python
from questline.drivers.port import GameHook

driver.call_game_method(GameHook("ReloadActiveScene", causes_soft_reload=True))
# next find/tap must succeed — AltTesterDriver reconnected automatically
```

3. Maintainer acceptance: following step succeeds after the hook (no manual reconnect).

## 8. Profiles cheat sheet

| Profile field | Meaning |
|---------------|---------|
| `driver = "alttester"` | Use `AltTesterDriver` |
| `target_platform` | `editor` \| `standalone_exe` \| `android` |
| `target_host` / `target_port` | AltTester server |
| `target_app_name` | AltTester `app_name` / tag (`__default__` usual) |

Env overrides: `QUESTLINE_ALT_HOST`, `QUESTLINE_ALT_PORT`, `QUESTLINE_TARGET_PLATFORM`, …

For **Android** (`android_local` profile, adb reverse, APK install/launch), see
[android.md](android.md).

## Troubleshooting

| Symptom | Likely cause |
|---------|----------------|
| InfraError / NoAppConnected (close 4001) | Play mode not running, or wrong `app_name` tag |
| SessionLostError / AppDisconnected (4002) | Soft reload without re-handshake, or app quit |
| `AltTester-Driver is not installed` | `uv pip install -e ".[alttester]"` |
| unknown questline hook | Hook not registered before Play, or typo in name |
| smoke WaitFor timeout | Missing `QuestlineSmokeRoot` / `QuestlineSmokeButton` names |

## Maintainer acceptance checklist (phase-04)

- [x] CI: unit + fake-transport conformance green (no live Unity)
- [x] Conformance green in Editor play mode (**game QL-1**)
- [x] Smoke green in Editor (+ Windows standalone as available) (**game QL-1**)
- [x] `causesSoftReload` hook → auto re-handshake → next step OK (**game QL-1**)
- [x] This doc followed once end-to-end on a real project (QL-1)
