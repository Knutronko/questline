# Questline Companion (`com.questline.companion`)

UPM package that exposes typed debug hooks to the Questline Python driver.

**Transports:** QuestlineWire (phase-05b / ADR-0005 — happy path, no Desktop) or optional
AltTester `CallStaticMethod` (legacy).

See [docs/unity-setup.md](../docs/unity-setup.md), [ADR-0004](../docs/adr/ADR-0004-companion-hooks.md),
and [ADR-0005](../docs/adr/ADR-0005-questline-wire.md).

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
}
```

Python:

```python
driver.hooks_manifest()  # serializable registry dump
driver.call_game_method(GameHook("SetLevel"), 3)
driver.call_game_method(GameHook("ReloadActiveScene", causes_soft_reload=True))
```
