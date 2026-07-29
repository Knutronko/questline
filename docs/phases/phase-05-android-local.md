# Phase 05 — Android via local adb

> Session preamble: see `phase-00-bootstrap.md`. Read `docs/01-ARCHITECTURE.md §3.2`.

## Context
Phases 00–04 merged. AltTesterDriver works against Editor/standalone. No device layer yet.

## Objective
`DeviceProviderPort` + a real `LocalAdbProvider`; the Unity smoke suite green on a physical
Android phone and on an emulator, launched through the framework.

## In scope
1. **DevicePort** (`devices/port.py`): `DeviceProviderPort` per architecture §3.2;
   `DeviceSpec` (platform, id?, api_level?, caps) and `Device` model.
2. **LocalAdbProvider** (`devices/adb/`): device discovery (`adb devices -l` parsed),
   acquire/release with lock file (two runs can't grab the same device), APK install
   (+ version check), app launch/stop, **port forward AND reverse with post-verification**
   (`adb reverse --list` asserted after mount — a silent failure here is a design-rule
   violation), logcat capture to artifacts (ring buffer, saved on failure).
3. **Profile plumbing**: `android_local` profile = LocalAdbProvider + AltTesterDriver
   `ConnectionTarget(android)`; device serial pinning via config; clear errors when no
   device/emulator found.
4. **Emulator helper** (best-effort, Windows-friendly): start a named AVD if configured
   (`emulator -avd X`), wait for boot completed; documented as optional.
5. Docs: `docs/android.md` — phone setup (USB debugging), emulator setup, troubleshooting
   table (offline device, unauthorized, port conflicts).

## Out of scope
Cloud farms (stubs in Phase 15), Appium device-level driver, PerfProbe (Phase 09).

## Acceptance criteria
- [ ] CI: provider unit tests green with a **fake adb** (recorded outputs); interface
      conformance tests for DevicePort.
- [ ] Maintainer-checked: smoke suite green on a real phone via
      `pytest examples/unity-smoke --questline-profile android_local`.
- [ ] Maintainer-checked: same on an emulator; device lock prevents a second concurrent run.
- [ ] Failure artifacts: on a forced failure, logcat + screenshot land in the run store.
- [ ] `adb reverse` post-verification test exists (fake adb returns empty list → raises).

## PR checklist
Title `phase-05: android local device provider`.
