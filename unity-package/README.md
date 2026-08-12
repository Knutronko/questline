# Questline Companion (`com.questline.companion`)

UPM package that exposes typed debug hooks to the Questline Python driver.

**Transports:**
- **QuestlineWire** (phase-05b / ADR-0005 + **Wire v2 UI** ADR-0008) — happy path, no Desktop:
  `QuestlineWireServer.EnsureStarted(13000)` under `#if UNITY_EDITOR || QUESTLINE_DEV`
  (`hierarchy` / `find` / `find_all` / `tap` / `screenshot`; `hello` advertises `features: hooks,ui`)
- Optional **AltTester** `CallStaticMethod` (legacy) — mutually exclusive on port 13000

See [docs/wire-setup.md](../docs/wire-setup.md), [docs/unity-setup.md](../docs/unity-setup.md),
[ADR-0004](../docs/adr/ADR-0004-companion-hooks.md), [ADR-0005](../docs/adr/ADR-0005-questline-wire.md),
and [ADR-0008](../docs/adr/ADR-0008-wire-v2-ui.md).

**GameLens (FP-G1):** Editor menu **Questline → Export Balance Snapshot**
(`QuestlineBalanceExport`) serializes ScriptableObjects listed in a game manifest
(QL-5). See [docs/gamelens.md](../docs/gamelens.md) and
[ADR-0009](../docs/adr/ADR-0009-gamelens-snapshot.md).

## Quick register (game code)

```csharp
using Questline.Companion;

void Awake()
{
    QuestlineHooks.RegisterAction("SkipTutorial", () => tutorial.Skip());
    QuestlineHooks.Register<int>("SetLevel", level => { progress.SetLevel(level); return null; },
        argName: "level", feature: "progression");
    QuestlineHooks.Register<string, int>("GrantSoftCurrency",
        (currency, amount) => { economy.Grant(currency, amount); return null; },
        causesSoftReload: false, feature: "economy",
        arg0Name: "currency", arg1Name: "amount");
    // Soft-reload example (Python auto re-handshakes after InvokeHook):
    QuestlineHooks.RegisterAction("ReloadActiveScene", () => { }, causesSoftReload: true);

#if UNITY_EDITOR || QUESTLINE_DEV
    QuestlineWireServer.EnsureStarted(13000);
    // Wire bootstrap also registers GetPerfSample (PerfProbe / QL-3).
    // Explicit call is safe if you start Wire later or use AltTester only:
    QuestlinePerfProvider.EnsureRegistered();
#endif
}
```

Python (`driver = "questline"`):

```python
from questline.drivers.locators import Locator, LocatorStrategy
from questline.drivers.port import GameHook

driver.hooks_manifest()  # serializable registry dump
driver.call_game_method(GameHook("SetLevel"), 3)
driver.call_game_method(GameHook("ReloadActiveScene", causes_soft_reload=True))
driver.call_game_method(GameHook("GetPerfSample"))  # fps / allocated_mb / draw_calls

# Wire v2 UI (after companion refresh / QL-2c)
el = driver.find(Locator(by=LocatorStrategy.NAME, value="OkButton"))
driver.tap(el)
png = driver.screenshot()
```
