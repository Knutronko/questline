# Android via local adb (Phase 05)

Run Questline against an instrumented Unity APK on a USB phone or emulator using
`LocalAdbProvider` + a game driver (`QuestlineDriver` / Wire preferred — phase-05b;
`AltTesterDriver` optional/legacy) with `ConnectionTarget(platform="android")`.

> **Live status:** AltTester Desktop is **not** the €0 happy path (ADR-0005). Prefer
> `driver = "questline"` once phase-05b Gate B lands. Device plumbing (`adb reverse`,
> install, launch, lock) is unchanged.

## Prerequisites

- Android SDK **platform-tools** (`adb` on `PATH`, or set `QUESTLINE_ADB_PATH` /
  `ANDROID_HOME`)
- Optional: Android **emulator** + an AVD (`emulator` on `PATH` or under
  `$ANDROID_HOME/emulator`)
- An **instrumented** Unity APK (AltTester SDK + `com.questline.companion` compiled
  into a **dev** flavor only — never ship instrumentation in release)

Reference game: game session **QL-2** builds the `QUESTLINE_DEV` Android flavor.
Until QL-2 lands, use a minimal sample-project APK (same companion + smoke GOs) and
re-validate against ElJuegaso after QL-2. See [GAME-INTEGRATION.md](GAME-INTEGRATION.md) §4.

## Phone setup (USB debugging)

1. Developer options → enable **USB debugging**.
2. Connect the phone; accept the RSA fingerprint prompt ("Allow USB debugging?").
3. Verify:

```bash
adb devices -l
# <serial>  device  ...
```

4. If the state is `unauthorized`, unlock the phone and re-accept the prompt.
   If `offline`, replug USB / change cable / `adb kill-server && adb start-server`.

## Emulator setup (optional)

1. Create an AVD in Android Studio (or `avdmanager`).
2. Either start it yourself (`emulator -avd Pixel_6_API_34`) **or** set
   `emulator_avd = "Pixel_6_API_34"` in the `android_local` profile — Questline will
   start it when no device is online and wait for `sys.boot_completed=1`.
3. Emulator helper is **best-effort** and Windows-friendly; if boot hangs, start the
   AVD manually and re-run.

## Profile: `android_local`

```toml
[profile.android_local]
driver = "alttester"
device = "adb"
target_host = "127.0.0.1"
target_port = 13000
target_platform = "android"
target_app_name = "__default__"
# device_serial = "emulator-5554"
# apk_path = "path/to/dev.apk"
# app_package = "com.example.game"
# app_activity = "com.unity3d.player.UnityPlayerActivity"
# emulator_avd = "Pixel_6_API_34"
install_apk = true
```

Env overrides: `QUESTLINE_DEVICE_SERIAL`, `QUESTLINE_APK_PATH`,
`QUESTLINE_APP_PACKAGE`, `QUESTLINE_APP_ACTIVITY`, `QUESTLINE_EMULATOR_AVD`,
`QUESTLINE_ADB_PATH`, `QUESTLINE_REVERSE_PORT`, `QUESTLINE_INSTALL_APK`.

Session wiring (pytest plugin):

1. Discover / optionally start emulator
2. **Acquire** device with exclusive lock (`.questline/device-locks/<serial>.lock`)
3. **`adb reverse tcp:<port> tcp:<port>`** + post-verify `adb reverse --list`
   (empty list → `DeviceError` — no silent failures)
4. Install APK (if configured) and launch package
5. Connect `AltTesterDriver` to `127.0.0.1:target_port`
6. On test failure: screenshot + logcat saved under `.questline/artifacts/`
7. Teardown: force-stop, clear reverse/forward, release lock

## Run the Unity smoke suite

```powershell
$env:QUESTLINE_LIVE_TARGET = "1"
$env:QUESTLINE_APK_PATH = "D:\path\to\dev.apk"
$env:QUESTLINE_APP_PACKAGE = "com.example.game"
uv run pytest examples/unity-smoke -q -o addopts= `
  --questline-profile android_local `
  --questline-config examples/unity-smoke/questline.toml
```

Device lock: a second concurrent run against the same serial fails with
`DeviceError: … is locked by another questline run`.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|----------------|-----|
| `No online Android device` | USB off / no emulator | Enable debugging; start AVD; check `adb devices` |
| `unauthorized` | RSA prompt not accepted | Unlock phone, re-plug, accept prompt |
| `offline` | flaky USB / adb server | New cable; `adb kill-server`; reboot phone |
| `device_serial=… is not online` | Wrong pin / multiple devices | `adb devices -l`; fix or clear `device_serial` |
| `adb reverse post-verification failed` | reverse silently no-op / old adb | Update platform-tools; re-authorize USB |
| Port conflicts / AltTester connect timeout | reverse missing or wrong port | Confirm `adb reverse --list`; match `target_port` |
| `device … is locked` | Prior run crashed holding lock | Wait for other run; or delete `.questline/device-locks/*.lock` if PID is dead |
| Install / launch fails | wrong package / unsigned APK | Use the **dev** instrumented APK; check `app_package` |
| Smoke WaitFor timeout | Missing smoke GOs / no companion | Same as Editor: `QuestlineSmokeRoot` / `Button` + hooks |

## Maintainer acceptance checklist (phase-05)

- [x] CI: provider unit tests with fake adb; DevicePort conformance; reverse empty-list raises
- [ ] **Maintainer-checked:** smoke green on a real phone via `--questline-profile android_local`
- [ ] **Maintainer-checked:** same on an emulator; lock blocks a second concurrent run
- [ ] **Maintainer-checked:** forced failure → logcat + screenshot in the run store
- [ ] **pending game QL-2:** instrumented ElJuegaso Android/dev APK — until then, validate
      with a minimal sample-project APK and re-validate after QL-2
