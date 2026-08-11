# INC-0001: Wire NDJSON response steal when PerfProbe env left on

- **Date:** 2026-08-11
- **Phases / triggers:** phase-09 (PerfProbe), phase-09b (Wire v2 live), QL-3 maintainer C
- **Status:** fixed
- **PRs:** questline [#22](https://github.com/Knutronko/questline/pull/22) (lock + id check)

## Symptom

`examples/wire-smoke` (Editor) failed intermittently after QL-3 live perf checks:

- `hooks_manifest` → `AuthoringError: hooks manifest JSON must contain a 'hooks' array`
  with raw result `{'value': '{"fps":…,"allocated_mb":…,"draw_calls":0}'}`
- `hierarchy` → `wire hierarchy.roots must be an array` with the **same** `value`/fps
  payload

Shape is exactly `call_hook` / `GetPerfSample`, not the requested op.

## Root cause

PowerShell session still had leftover env from QL-3 maintainer steps:

```powershell
$env:QUESTLINE_PERF_ENABLED = "true"
$env:QUESTLINE_PERF_SOURCE = "companion"
$env:QUESTLINE_PERF_INTERVAL_S = "1"
```

Env **overrides** `questline.toml`. PerfProbe’s background thread called
`GetPerfSample` on the **same** TCP NDJSON connection as the test thread.
`TcpWireTransport.request` was not serialized → response lines were stolen
(hooks/UI read a perf reply).

## Fix

1. Serialize `TcpWireTransport.request` (and FakeWire) with a lock.
2. Validate response `id` matches request `id` (fail loud on mismatch).
3. Concurrent unit test in `tests/test_wire_unit.py`.
4. `examples/wire-smoke/questline.toml` sets `perf.enabled = false` (reminder only —
   env still wins).

## Prevention

- Before Wire-only smoke, clear perf env in **that** PowerShell window:

  ```powershell
  Remove-Item Env:QUESTLINE_PERF_ENABLED, Env:QUESTLINE_PERF_SOURCE, Env:QUESTLINE_PERF_INTERVAL_S -ErrorAction SilentlyContinue
  ```

- Or open a **new** PowerShell if unsure what is set (`Get-ChildItem Env:QUESTLINE*`).
- Remember: `QUESTLINE_PERF_*` survives for the life of the window after QL-3 / perf
  dogfood; it is not reset by `cd` or changing repos.
- Live Wire + PerfProbe together is supported **after** the lock fix; still prefer
  clearing perf env when debugging Wire UI alone.
- Operator guides: [`docs/wire-setup.md`](../wire-setup.md),
  [`docs/performance.md`](../performance.md).

## See also

- INC-0002 (companion sync) — often appeared in the same maintainer session
- ADR-0005 transport; ADR-0008 Wire v2 UI
