# ADR-0004: Companion package hook contract (QuestlineHooks)

- **Status:** accepted (phase-04)
- **Context:** Game UI automation needs stable debug entry points (set level, grant
  currency, skip tutorial) without per-game reflection guessing. Soft scene reloads
  kill AltTester sessions silently unless the framework knows to re-handshake. A future
  feature-scan tool (FP-F1) must diff registered hooks across game versions.
- **Decision:**
  1. Ship UPM package `com.questline.companion` with `QuestlineHooks` — games register
     typed hooks (`Register` / `RegisterAction`) declaring `causesSoftReload` and an
     optional `feature` label.
  2. Python `AltTesterDriver.call_game_method` invokes
     `QuestlineHooks.InvokeHook(name, argsJson)` via AltTester `CallStaticMethod`.
  3. When `GameHook.causes_soft_reload` is true **or** the cached manifest marks the
     hook with `causesSoftReload`, the driver stops and reconnects before the next step
     (no silent session death).
  4. **Hooks manifest (addendum):** `QuestlineHooks.GetManifestJson()` returns one
     serializable dump `{hooks:[{name,args[{name,type}],causesSoftReload,feature?}]}`.
     Python retrieves it with a single call: `AltTesterDriver.hooks_manifest()` /
     (phase-05b) `QuestlineDriver.hooks_manifest()` over QuestlineWire (ADR-0005).
     Promote onto `DriverPort` when Wire lands so both adapters share the contract.
- **Consequences:** Games own hook handlers (including performing a soft reload when
  flagged). Feature-scan can diff manifests without reading game source. Soft-reload
  re-handshake delay is configurable on the driver; live validation is maintainer-checked
  (Editor). AltTester Desktop is **not** required once Wire is the transport; hooks stay
  the game API either way.
