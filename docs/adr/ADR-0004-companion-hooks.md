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
  2. Python invokes hooks via **QuestlineWire** (`call_hook`) or legacy AltTester
     `CallStaticMethod` — same `QuestlineHooks.InvokeHook(name, argsJson)`.
  3. When `GameHook.causes_soft_reload` is true **or** the cached manifest marks the
     hook with `causesSoftReload`, the driver stops and reconnects before the next step
     (no silent session death).
  4. **Hooks manifest:** `QuestlineHooks.GetManifestJson()` → Python
     `hooks_manifest()` on `DriverPort` (Wire + AltTester adapters).
- **Consequences:** Games own hook handlers. Soft-reload re-handshake is driver-side.
  Happy-path transport is Wire (ADR-0005). AltTester Desktop is not required.
