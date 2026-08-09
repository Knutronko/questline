# QuestlineWire — Unity setup (happy-path live)

First-party live driver: TCP + NDJSON on **127.0.0.1:13000** (ADR-0005).
**No AltTester Desktop.** Dev/Editor only (`UNITY_EDITOR || QUESTLINE_DEV`).

This is the **default** live path. For legacy AltTester (Desktop hub), see
[unity-setup.md](unity-setup.md) — remote option only, not €0 happy path.

## Driver priority

| Priority | Profile `driver` | Use for |
|----------|------------------|---------|
| 1 | `"questline"` | Live Editor / Android smoke, hooks, soft-reload |
| 2 | `"poco"` (phase-14) | UI hierarchy / find / tap (preferred over AltTester) |
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

4. Console should log: `[QuestlineWire] listening on 127.0.0.1:13000 (v1)`.

## Python smoke (Editor)

```powershell
cd D:\dev\questline   # repo root — not $HOME
$env:QUESTLINE_LIVE_TARGET = "1"
uv pip install -e ".[dev]"
uv run pytest examples/wire-smoke -q -o addopts= `
  --questline-profile editor `
  --questline-config examples/wire-smoke/questline.toml
```

No `[alttester]` extra. Profile key: `driver = "questline"`.

## Android

Same `LocalAdbProvider` + `adb reverse tcp:13000 tcp:13000` as phase-05.
APK must be built with `QUESTLINE_DEV` so `QuestlineWireServer` is compiled in.
See [android.md](android.md) and [examples/wire-smoke/questline.toml](../examples/wire-smoke/questline.toml).

```powershell
$env:QUESTLINE_LIVE_TARGET = "1"
$env:QUESTLINE_APK_PATH = "path\to\dev.apk"
$env:QUESTLINE_APP_PACKAGE = "com.example.game"
uv run pytest examples/wire-smoke -q -o addopts= `
  --questline-profile android_local `
  --questline-config examples/wire-smoke/questline.toml
```

## Wire roadmap (formal)

| Stage | Scope | Status |
|-------|--------|--------|
| **MVP (05b)** | connect / alive / app_state / hooks_manifest / call_hook / soft-reload | ✅ |
| **Editor live** | `examples/wire-smoke` + reference game QL-2b | ✅ |
| **Android live** | Rebuild Dev APK with Wire; `android_local` smoke | ⬜ follow-up |
| **Wire v2 UI** | find / hierarchy / tap / screenshot | ❌ **Deferred** — implement via **Poco** (phase-14), not Wire |

Wire stays the **hooks / session** transport. Poco (not AltTester) is the planned
**UI hierarchy** adapter.

## Reference game (ElJuegaso) — QL-2b ✅

Bootstrap already calls `QuestlineWireServer.EnsureStarted(13000)` and skips AltTester
host when `UseQuestlineWire = true`. Companion embed includes `QuestlineWireServer.cs`.

| Path in questline | Action in game |
|---|---|
| `unity-package/Runtime/QuestlineHooks.cs` | Keep in sync on API changes |
| `unity-package/Runtime/QuestlineWireServer.cs` | Embedded (QL-2b) |
| `unity-package/Runtime/Questline.Companion.asmdef` | `UNITY_EDITOR \|\| QUESTLINE_DEV` |
| `unity-package/package.json` | Sync version notes |

**Editor Wire is green;** game exit task `automation/` coverage-demo is **scaffolded**
(GAME-INTEGRATION §3). Android Wire live still needs Dev APK rebuild.
AltTester UPM may remain installed dormant; do not treat it as primary live.
