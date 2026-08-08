# QuestlineWire — Unity setup (phase-05b)

First-party live driver: TCP + NDJSON on **127.0.0.1:13000** (ADR-0005).
No AltTester Desktop. Dev/Editor only (`UNITY_EDITOR || QUESTLINE_DEV`).

## Game bootstrap (any Unity project)

1. Install / refresh `com.questline.companion` (git UPM or embedded copy).
2. Register hooks as today (`QuestlineHooks.Register…`).
3. Start Wire **instead of** (or without) AltTester Prefab on port 13000:

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

4. Do **not** run AltTester Prefab on the same port while Wire is listening.

## Python smoke

```powershell
$env:QUESTLINE_LIVE_TARGET = "1"
uv pip install -e ".[dev]"
uv run pytest examples/wire-smoke -q -o addopts= `
  --questline-profile editor `
  --questline-config examples/wire-smoke/questline.toml
```

Profile key: `driver = "questline"` (no `[alttester]` extra).

## Android

Same `LocalAdbProvider` + `adb reverse tcp:13000 tcp:13000` as phase-05.
APK must be built with `QUESTLINE_DEV` so `QuestlineWireServer` is compiled in.
See [android.md](android.md) and [examples/wire-smoke/questline.toml](../examples/wire-smoke/questline.toml).

## Reference game (ElJuegaso) — QL-2b later

Exact companion files to refresh after this phase merges:

| Path in questline | Action in game |
|---|---|
| `unity-package/Runtime/QuestlineHooks.cs` | Refresh embed if changed |
| `unity-package/Runtime/QuestlineWireServer.cs` | **Add** (new) |
| `unity-package/Runtime/Questline.Companion.asmdef` | Refresh if needed |
| `unity-package/package.json` | Bump / sync version note |

Game-side bootstrap: call `QuestlineWireServer.EnsureStarted()` from existing
`P1QuestlineBootstrap` (or equivalent) under the same define gate; disable AltTester
Prefab when using Wire profiles. **Do not** delete AltTester UPM until Wire is green
on device. Do **not** scaffold `automation/` until first live smoke is green.
