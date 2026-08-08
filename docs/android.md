# Android via local adb (Phase 05)

Run Questline against an instrumented Unity APK on a USB phone or emulator using
`LocalAdbProvider` + **`QuestlineDriver` (Wire)** — happy path.

> **Live status:** `driver = "questline"` only. AltTester Desktop is **not** the €0 path
> (ADR-0005). Device plumbing (`adb reverse`, install, launch, lock) is unchanged.
> After QL-2b, rebuild the Dev APK so Wire is compiled in, then smoke with
> `examples/wire-smoke` + profile `android_local`.

## Prerequisites

- Android SDK **platform-tools** (`adb` on `PATH`, or set `QUESTLINE_ADB_PATH` /
  `ANDROID_HOME`)
- Optional: Android **emulator** + an AVD
- An **instrumented** Unity APK: `QUESTLINE_DEV` + companion **QuestlineWire** (never
  ship instrumentation in release)

Reference game: rebuild Questline Dev APK after QL-2b so `QuestlineWireServer` is in the
player. See [wire-setup.md](wire-setup.md) and [GAME-INTEGRATION.md](GAME-INTEGRATION.md).

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
`QUESTLINE_ADB_PATH`, `QUESTLINE_REVERSE_PORT`, `QUESTLINE_INSTALL_APK`.

Session wiring (pytest plugin):

1. Discover / optionally start emulator
2. **Acquire** device with exclusive lock
3. **`adb reverse tcp:<port> tcp:<port>`** + post-verify
4. Install APK (if configured) and launch package
5. Connect `QuestlineDriver` to `127.0.0.1:target_port`
6. On failure: screenshot attempt + logcat under `.questline/artifacts/`
7. Teardown: force-stop, clear reverse, release lock

## Run Wire smoke on device

```powershell
cd D:\dev\questline
$env:QUESTLINE_LIVE_TARGET = "1"
$env:QUESTLINE_APK_PATH = "D:\path\to\questline_dev.apk"
$env:QUESTLINE_APP_PACKAGE = "com.eljuegaso.p1"
uv run pytest examples/wire-smoke -q -o addopts= `
  --questline-profile android_local `
  --questline-config examples/wire-smoke/questline.toml
```

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `10061` / connection refused | Wire not in APK / Play not listening / reverse missing | Rebuild Dev APK with QL-2b; confirm log `[QuestlineWire] listening`; `adb reverse --list` |
| Port conflicts | Another process on 13000 | Stop AltTester host; one listener only |
| unauthorized / offline | USB debug | Re-accept prompt; replug; `adb kill-server` |
