"""PerfProbe: background sampling, collectors, and threshold assertions."""

from __future__ import annotations

from questline.perf.asserts import (
    assert_avg,
    assert_max,
    assert_no_samples_below,
    bind_perf_context,
    clear_perf_context,
)
from questline.perf.probe import PerfProbe

__all__ = [
    "PerfProbe",
    "assert_avg",
    "assert_max",
    "assert_no_samples_below",
    "bind_perf_context",
    "clear_perf_context",
]
