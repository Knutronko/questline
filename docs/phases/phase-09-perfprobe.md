# Phase 09 — PerfProbe: performance metrics on device and in Editor

> Session preamble: see `phase-00-bootstrap.md`. Read `docs/01-ARCHITECTURE.md §7`.

## Context
Phases 00–08 merged. Runs on Android work; store has a `perf_samples` table (empty so far).

## Objective
Opt-in performance sampling during runs, stored as time series, with optional threshold
assertions. Device metrics via adb; Editor/standalone metrics via the companion package.

## In scope
1. **Sampler core** (`perf/probe.py`): background thread started per test (or per run,
   config), sampling interval configurable; emits `PerfSample(metric, value, ts, test_id)`
   events → store; zero samples lost on crash (incremental writes); overhead measured and
   documented (<2% target on the device).
2. **Android collectors** (`perf/android.py`): FPS + jank (`dumpsys gfxinfo` parse),
   memory PSS (`dumpsys meminfo`), CPU (`/proc/<pid>/stat` deltas), battery + temperature
   (`dumpsys battery`/`thermalservice` where available). Robust parsers with recorded
   fixtures from at least 2 Android versions; a parser failure degrades to "metric
   unavailable" (logged), never a run failure.
3. **Companion collectors**: extend `com.questline.companion` with a perf provider (FPS,
   allocated memory, draw calls) queryable through the driver; used for Editor/standalone
   profiles.
4. **Threshold assertions** (`perf/asserts.py`):
   `perf.assert_avg("fps", ">=", 55, window="test")`, `assert_max("memory_pss", "<=", X)`,
   `assert_no_samples_below("fps", 20, tolerance=…)`. Failures carry verdict `test` with
   the offending series slice attached as artifact.
5. CLI: `questline perf report <run_id>` — text/HTML summary per metric.
6. Docs: `docs/performance.md` (what each metric means, caveats: emulator FPS ≠ device FPS).

## Out of scope
HUD graphs (Phase 10 renders this data), anomaly detection (backlog), iOS metrics.
Wire v2 UI (`find`/`tap`) is **phase-09b** (after this phase) — do not implement here.

## Acceptance criteria
- [ ] CI: parsers green on recorded fixtures; sampler lifecycle unit tests (start/stop/kill).
- [ ] Maintainer-checked: run on real phone produces plausible FPS/memory series for
      their game; overhead spot-check documented.
- [ ] Threshold assertion demo: seeded low-FPS fixture fails with the series attached.
- [ ] Editor profile produces companion-sourced samples.

## PR checklist
Title `phase-09: perfprobe`. Next planned fw bridge: [phase-09b](phase-09b-wire-v2.md).
