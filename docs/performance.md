# Performance sampling (PerfProbe, phase-09)

Opt-in background metrics during pytest runs. Samples land in the run store
(`perf_samples`) as a time series and can be asserted or summarized with
`questline perf report`.

## Enable

```toml
[profile.android_local]
# …
perf.enabled = true
perf.interval_s = 1.0
perf.scope = "test"          # or "run"
perf.source = "auto"         # auto | android | companion
# perf.metrics = ["fps", "memory_pss_mb"]   # empty = all known metrics
```

Env overrides (never put secrets in toml — N/A for perf flags):

| Env | Effect |
|-----|--------|
| `QUESTLINE_PERF_ENABLED` | `true`/`false` |
| `QUESTLINE_PERF_INTERVAL_S` | sampling period seconds |
| `QUESTLINE_PERF_SCOPE` | `test` / `run` |
| `QUESTLINE_PERF_SOURCE` | `auto` / `android` / `companion` |
| `QUESTLINE_PERF_METRICS` | comma-separated metric names |

Off by default so CI stays €0 and quiet unless a profile opts in.

## Metrics

| Metric | Source | Meaning |
|--------|--------|---------|
| `fps` | Android `dumpsys gfxinfo` (frame deltas or 50th-percentile ms) **or** companion | Frames per second |
| `jank_pct` | Android gfxinfo | Percent of janky frames in the gfxinfo window |
| `memory_pss_mb` | Android `dumpsys meminfo` | Total PSS (MB) |
| `cpu_pct` | `/proc/<pid>/stat` deltas | Approx. % of one core (100 Hz jiffies) |
| `battery_level` | `dumpsys battery` | Charge % |
| `battery_temp_c` | battery temperature (tenths °C → °C) | Device battery temp |
| `thermal_temp_c` | `dumpsys thermalservice` (when present) | Max reported thermal sensor °C |
| `allocated_mb` | Companion `GetPerfSample` | Unity allocated managed/native heap (MB) |
| `draw_calls` | Companion (placeholder; 0 unless game extends) | Reserved counter slot |

### Caveats

- **Emulator FPS ≠ device FPS.** Treat emulator series as relative/smoke only.
- **gfxinfo** reflects the process window Android tracks; first sample may use
  percentile→FPS until a frame-count delta exists.
- **cpu_pct** is approximate (assumes 100 Hz); multi-core loads can exceed 100.
- Parser failures log a warning and skip that metric for the tick — **they never
  fail the run**.
- Companion counters require `QuestlinePerfProvider` (bundled in
  `com.questline.companion`). Wire `EnsureStarted` registers it automatically;
  game **QL-3** is: refresh the UPM package / rebuild Dev APK so the provider is
  present on device builds.

## Overhead

Sampler runs on a **daemon thread**. Each tick publishes `PerfSample` events that
the store commits immediately (kill-safe). Target overhead on device is **&lt;2%**
wall time for a 1 s interval when only a few dumpsys calls run; spot-check by
comparing a short playtest with `perf.enabled=false` vs `true` (same build,
same scene). Heavy `dumpsys` on low-end phones is the main cost — raise
`interval_s` if needed.

## Assertions

```python
from questline import perf

perf.assert_avg("fps", ">=", 55, scope="test")
perf.assert_max("memory_pss_mb", "<=", 512, scope="test")
perf.assert_no_samples_below("fps", 20, tolerance=2, scope="test")
```

Failures raise `AssertionFailedError` (**verdict=`test`**) and attach a
`perf_series` JSON artifact with the offending slice.

## Report

```powershell
questline perf report <run_id>
questline perf report <run_id> --format html
questline perf report <run_id> --store .questline/store.db -o perf.html
```

## Out of scope (later)

HUD graphs (phase-10), Wire v2 find/tap (09b), anomaly detection, iOS.
