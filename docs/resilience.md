# Resilience — health, recovery, watchdog, verdicts

Session losses and silent hangs must not look like “the test is red.”
Questline classifies infra failures, recovers when possible, and aborts with
distinct exit codes when progress stops or losses chain.

See architecture [`01-ARCHITECTURE.md`](01-ARCHITECTURE.md) §2.6 and
[`ADR-0006`](adr/ADR-0006-recovery-ladder.md).

## Components

| Piece | Module | Role |
|-------|--------|------|
| **HealthMonitor** | `core/health.py` | Cheap checks: `is_alive`, hierarchy non-empty (skipped if N/A), device online |
| **normalize / classify** | `core/errors.py` | Transport signatures → `SessionLostError` / `verdict=infra`; bare `AssertionError` → `test` |
| **RecoveryPolicy** | `core/recovery.py` | Ladder `reconnect_driver` → `restart_app` → `restart_session` + circuit breaker |
| **Watchdog** | `core/watchdog.py` | No-progress daemon; every long op (incl. recovery) must `mark_progress()` |

## Exit codes

| Code | Constant | Meaning |
|------|----------|---------|
| 140 | `EXIT_WATCHDOG` | No progress within `resilience.watchdog_timeout_s` |
| 141 | `EXIT_CIRCUIT_BREAKER` | N consecutive session losses without an intervening pass |

Reporters (phase 07) still consume the event bus / sealed store after abort.

## Config (`questline.toml` / env)

```toml
[profile.ci.resilience]
watchdog_timeout_s = 120
circuit_breaker_losses = 3
recovery_enabled = true
```

| Env | Field |
|-----|-------|
| `QUESTLINE_WATCHDOG_TIMEOUT_S` | `resilience.watchdog_timeout_s` |
| `QUESTLINE_CIRCUIT_BREAKER_LOSSES` | `resilience.circuit_breaker_losses` |
| `QUESTLINE_RECOVERY_ENABLED` | `resilience.recovery_enabled` |

## Failure modes

| Signature / symptom | Classification | Recovery | What the report / store shows |
|---------------------|----------------|----------|-------------------------------|
| `ConnectionResetError` / “connection closed” / wire disconnect | `SessionLostError(kind=disconnect)` → **infra** | Ladder from reconnect | Pytest **failed**; `tests.verdict=infra`; `SessionLost` + `RecoveryAttempted` events |
| “no app connected” | `SessionLostError(kind=no_app)` → **infra** | Ladder (often restart_app/session on device) | Same; not a test assertion failure |
| Empty hierarchy at teardown | `SessionLostError(kind=empty_hierarchy)` → **infra** | Ladder | Infra verdict; health tags may include `hierarchy_ok=false` |
| Driver `is_alive()==false` mid-run | Health → session loss | Ladder if recovery enabled | Death-point tags: `driver_alive=false` |
| Bare `assert` / `AssertionError` | **test** | None | Pytest failed; `verdict=test` |
| `ElementNotFoundError` / `AssertionFailedError` | **test** | None | Pytest failed; `verdict=test` |
| N consecutive session losses | Circuit breaker | Abort run | `CircuitBreakerTripped`; run `status=aborted`; exit **141** |
| Silent hang / hung recovery | Watchdog | Abort run | `WatchdogFired`; prior events retained; exit **140** |

## Design rules (outcomes vs verdicts)

- Pytest **outcome** for the affected test stays **failed** (no silent skip / xfail).
- Store **verdict** is what reporters and triage read (`infra` vs `test`).
- Drivers are never frozen across reset — always `DriverHandle` + provider.
- Progress marks fire during recovery (regression-tested); a hung recovery still trips the watchdog.

## Fault-injection CI

```powershell
.\.venv\Scripts\python.exe -m pytest tests\resilience tests\test_errors.py -q
```

No device or AltTester Desktop required. Optional live check: pull USB mid Wire/Android run and confirm infra classification + recovery attempt.
