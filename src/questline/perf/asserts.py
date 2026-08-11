"""Threshold assertions over PerfProbe series (verdict=test)."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import UTC, datetime
from operator import ge, gt, le, lt
from typing import Any, Literal

from questline.core.errors import AssertionFailedError, AuthoringError

logger = logging.getLogger("questline.perf.asserts")

Scope = Literal["test", "run"]
Op = Literal[">=", ">", "<=", "<"]

_OPS: dict[str, Callable[[float, float], bool]] = {
    ">=": ge,
    ">": gt,
    "<=": le,
    "<": lt,
}


@dataclass(frozen=True, slots=True)
class PerfAssertContext:
    store: Any
    bus: Any
    run_id: str
    test_id: str | None = None


_CTX: ContextVar[PerfAssertContext | None] = ContextVar("questline_perf_assert_ctx", default=None)


def bind_perf_context(ctx: PerfAssertContext) -> None:
    """Bind store/run/test ids for subsequent ``assert_*`` calls (plugin sets this)."""
    _CTX.set(ctx)


def clear_perf_context() -> None:
    _CTX.set(None)


def assert_avg(
    metric: str,
    op: Op,
    threshold: float,
    *,
    scope: Scope = "test",
    store: Any | None = None,
    run_id: str | None = None,
    test_id: str | None = None,
    bus: Any | None = None,
) -> float:
    """Assert average of *metric* samples satisfies ``avg {op} threshold``."""
    samples = _load_samples(metric, scope=scope, store=store, run_id=run_id, test_id=test_id)
    if not samples:
        raise AssertionFailedError(f"perf.assert_avg({metric!r}): no samples in scope={scope!r}")
    avg = sum(s["value"] for s in samples) / len(samples)
    if not _compare(avg, op, threshold):
        _fail(
            f"perf.assert_avg({metric!r}): avg={avg:.4g} not {op} {threshold}",
            metric=metric,
            samples=samples,
            store=store,
            run_id=run_id,
            test_id=test_id,
            bus=bus,
            extra={"avg": avg, "op": op, "threshold": threshold},
        )
    return avg


def assert_max(
    metric: str,
    op: Op,
    threshold: float,
    *,
    scope: Scope = "test",
    store: Any | None = None,
    run_id: str | None = None,
    test_id: str | None = None,
    bus: Any | None = None,
) -> float:
    """Assert the maximum sample satisfies ``max {op} threshold`` (typically ``<=``)."""
    samples = _load_samples(metric, scope=scope, store=store, run_id=run_id, test_id=test_id)
    if not samples:
        raise AssertionFailedError(f"perf.assert_max({metric!r}): no samples in scope={scope!r}")
    peak = max(s["value"] for s in samples)
    if not _compare(peak, op, threshold):
        _fail(
            f"perf.assert_max({metric!r}): max={peak:.4g} not {op} {threshold}",
            metric=metric,
            samples=samples,
            store=store,
            run_id=run_id,
            test_id=test_id,
            bus=bus,
            extra={"max": peak, "op": op, "threshold": threshold},
        )
    return peak


def assert_no_samples_below(
    metric: str,
    floor: float,
    *,
    tolerance: int = 0,
    scope: Scope = "test",
    store: Any | None = None,
    run_id: str | None = None,
    test_id: str | None = None,
    bus: Any | None = None,
) -> int:
    """Fail if more than *tolerance* samples are strictly below *floor*."""
    if tolerance < 0:
        raise AuthoringError("tolerance must be >= 0")
    samples = _load_samples(metric, scope=scope, store=store, run_id=run_id, test_id=test_id)
    if not samples:
        raise AssertionFailedError(
            f"perf.assert_no_samples_below({metric!r}): no samples in scope={scope!r}"
        )
    offenders = [s for s in samples if s["value"] < floor]
    if len(offenders) > tolerance:
        _fail(
            f"perf.assert_no_samples_below({metric!r}): "
            f"{len(offenders)} sample(s) < {floor} (tolerance={tolerance})",
            metric=metric,
            samples=samples,
            store=store,
            run_id=run_id,
            test_id=test_id,
            bus=bus,
            extra={
                "floor": floor,
                "tolerance": tolerance,
                "offender_count": len(offenders),
            },
        )
    return len(offenders)


def _compare(actual: float, op: Op, threshold: float) -> bool:
    fn = _OPS.get(op)
    if fn is None:
        raise AuthoringError(f"unsupported comparator {op!r}; use one of {sorted(_OPS)}")
    return fn(actual, threshold)


def _resolve_ctx(
    *,
    store: Any | None,
    run_id: str | None,
    test_id: str | None,
    bus: Any | None,
) -> tuple[Any, str, str | None, Any | None]:
    bound = _CTX.get()
    resolved_store = store if store is not None else (bound.store if bound else None)
    resolved_run = run_id if run_id is not None else (bound.run_id if bound else None)
    resolved_test = test_id if test_id is not None else (bound.test_id if bound else None)
    resolved_bus = bus if bus is not None else (bound.bus if bound else None)
    if resolved_store is None or not resolved_run:
        raise AuthoringError(
            "perf assertions require an active questline run (questline_store / bind_perf_context) "
            "or explicit store= and run_id= arguments"
        )
    return resolved_store, resolved_run, resolved_test, resolved_bus


def _load_samples(
    metric: str,
    *,
    scope: Scope,
    store: Any | None,
    run_id: str | None,
    test_id: str | None,
) -> list[dict[str, Any]]:
    resolved_store, resolved_run, resolved_test, _ = _resolve_ctx(
        store=store, run_id=run_id, test_id=test_id, bus=None
    )
    if scope == "test":
        if not resolved_test:
            raise AuthoringError(
                "perf assertion scope='test' requires a test_id "
                "(run inside a questline test or pass test_id=)"
            )
        return resolved_store.list_perf_samples(
            run_id=resolved_run, test_id=resolved_test, metric=metric
        )
    if scope == "run":
        return resolved_store.list_perf_samples(run_id=resolved_run, metric=metric)
    raise AuthoringError(f"unknown perf assertion scope {scope!r}; use 'test' or 'run'")


def _fail(
    message: str,
    *,
    metric: str,
    samples: list[dict[str, Any]],
    store: Any | None,
    run_id: str | None,
    test_id: str | None,
    bus: Any | None,
    extra: dict[str, Any],
) -> None:
    resolved_store, resolved_run, resolved_test, resolved_bus = _resolve_ctx(
        store=store, run_id=run_id, test_id=test_id, bus=bus
    )
    artifact_path: str | None = None
    try:
        payload = {
            "metric": metric,
            "message": message,
            "generated_at": datetime.now(UTC).isoformat(),
            "samples": samples,
            **extra,
        }
        path = resolved_store.save_artifact(
            (json.dumps(payload, indent=2) + "\n").encode("utf-8"),
            run_id=resolved_run,
            name=f"perf-series-{metric}.json",
            kind="perf_series",
            test_id=resolved_test,
            bus=resolved_bus,
        )
        artifact_path = str(path)
    except Exception as exc:  # pragma: no cover - artifact is best-effort beside the fail
        logger.warning("could not attach perf series artifact: %s", exc)
    suffix = f" [series={artifact_path}]" if artifact_path else ""
    raise AssertionFailedError(message + suffix)
