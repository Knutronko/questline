# Android via local adb (Phase 05)

Run Questline against an instrumented Unity APK on a USB phone or emulator using
`LocalAdbProvider` + **`QuestlineDriver` (Wire)** — happy path.

> **Live status:** `driver = "questline"` only. AltTester Desktop is **not** the €0 path
> (ADR-0005). After QL-2b, rebuild the Dev APK so Wire is compiled in, then smoke with
> `examples/wire-smoke` + profile `android_local` (**green** on maintainer device
> 2026-08-09).

## Prerequisites

- Android SDK **platform-tools** (`adb` on `PATH`, or set `QUESTLINE_ADB_PATH` /
  `ANDROID_HOME`)
- Optional: Android **emulator** + an AVD
- An **instrumented** Unity APK: `QUESTLINE_DEV` + companion **QuestlineWire** (never
  ship instrumentation in release)

Reference game: Questline Dev APK with `QuestlineWireServer` in the player. See
[wire-setup.md](wire-setup.md) and [GAME-INTEGRATION.md](GAME-INTEGRATION.md).

## Phone setup (USB debugging)

1. Developer options → enable **USB debugging**.
2. Connect the phone; accept the RSA fingerprint prompt.
3. Verify: `adb devices -l`

## Profile: `android_local`

```toml
[profile.android_local]
driver = "questline"
device = "adb"
target_host = "127.0.0.1"
target_port = 13000
target_platform = "android"
install_apk = true
# apk_path / app_package / device_serial via toml or QUESTLINE_* env
```

Env overrides: `QUESTLINE_DEVICE_SERIAL`, `QUESTLINE_APK_PATH`,
`QUESTLINE_APP_PACKAGE`, `QUESTLINE_APP_ACTIVITY`, `QUESTLINE_EMULATOR_AVD`,
`QUESTLINE_ADB_PATH`, `QUESTLINE_REVERSE_PORT` (tunnel port; used for forward or
reverse), `QUESTLINE_INSTALL_APK`.

Session wiring (pytest plugin):

1. Discover / optionally start emulator
2. **Acquire** device with exclusive lock
3. **Port tunnel** (driver-dependent) + post-verify:
   - `driver = "questline"` → **`adb forward tcp:<port> tcp:<port>`** (host→device).
     Wire **listens on the device**; `adb reverse` steals device `:port` and Wire
     fails with `Address already in use`.
   - `driver = "alttester"` (legacy) → **`adb reverse`** (device→host hub)
4. Install APK (if configured), cold-start package, dismiss common system dialogs,
   wait until Wire `hello` succeeds
5. Connect `QuestlineDriver` to `127.0.0.1:target_port`
6. On failure: screenshot attempt + logcat under `.questline/artifacts/`
7. Teardown: force-stop, clear forward/reverse, release lock

## Run Wire smoke on device

```powershell
cd D:\dev\questline
$env:QUESTLINE_LIVE_TARGET = "1"
$env:QUESTLINE_ADB_PATH = "C:\Program Files\Unity\Hub\Editor\<VER>\Editor\Data\PlaybackEngines\AndroidPlayer\SDK\platform-tools\adb.exe"
$env:QUESTLINE_APK_PATH = "D:\path\to\questline_dev.apk"
$env:QUESTLINE_APP_PACKAGE = "com.eljuegaso.p1"
$env:QUESTLINE_APP_ACTIVITY = "com.unity3d.player.UnityPlayerGameActivity"
$env:QUESTLINE_DEVICE_SERIAL = "<serial from adb devices>"
uv run pytest examples/wire-smoke -q -o addopts= `
  --questline-profile android_local `
  --questline-config examples/wire-smoke/questline.toml
```

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `Address already in use` binding `:13000` | **`adb reverse`** still mounted (adbd owns device port) — not AltTester when `UseQuestlineWire` | `adb reverse --remove-all`; use **`adb forward`** for Wire; session does this for `driver=questline` |
| `10061` / connection refused / peer closed | Wire not up yet / no focus / forward missing | Confirm log `[QuestlineWire] listening`; `adb forward --list`; wait for dialog dismiss |
| System dialog: Android version / ABI not supported (`DeprecatedAbiDialog`) | Dev APK is **Mono + ARMv7** (Unity 6 Mono has no ARM64); common on Android 14+ 64-bit phones | Infra UI, not a game bug for smoke. Session auto-dismisses via keyevents/tap; if stuck, tap OK once. Optional future: IL2CPP+ARM64 Dev flavor (game-side; ask before redesign) |
| Port conflicts on host | Another process on 13000 | Stop leftover listeners; one tunnel only |
| unauthorized / offline | USB debug | Re-accept prompt; replug; `adb kill-server` |
