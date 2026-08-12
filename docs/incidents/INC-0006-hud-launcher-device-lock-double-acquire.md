# INC-0006: HUD Launch held adb device lock so pytest could not acquire it

- **Date:** 2026-08-12
- **Phases / triggers:** 10 (HUD Launch → Wire Android)
- **Status:** fixed
- **Symptom:** Launch finishes in &lt;1s; Live shows `RunStarted` → `RunFinished failed`;
  Run detail has **No tests** (0/0). Status `log_tail` shows
  `DeviceError: device '…' is locked by another questline run (owner=hud-launcher:…)`.
- **Root cause:** `RunLauncher` acquired the exclusive adb lock for the selected serial
  and kept it for the whole subprocess. The plugin’s `setup_android_session` then tried
  to acquire the same lock → setup ERROR on every test → no `TestStarted` events.
- **Fix:** Launcher only calls `DeviceLock.ensure_available` (refuse if another **live**
  run holds the lock; clear stale PID locks). Pytest owns the lock as before.
- **Prevention:** Never hold the device lock in a parent that spawns questline pytest.
  HUD one-at-a-time is already enforced by launcher job state.
- **See also:** INC-0005, [`hud-operator-guide.md`](../hud-operator-guide.md)
