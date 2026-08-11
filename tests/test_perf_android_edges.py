"""Extra android parser / collector edge cases for coverage."""

from __future__ import annotations

from questline.perf.android import (
    AndroidPerfCollector,
    parse_battery,
    parse_gfxinfo,
    parse_meminfo,
    parse_proc_stat,
    parse_thermalservice,
)


def test_parse_garbage_degrades() -> None:
    assert parse_gfxinfo("no useful data").total_frames is None
    assert parse_meminfo("TOTAL something else").total_pss_kb is None
    assert parse_proc_stat("not a stat line") is None
    assert parse_battery("").level is None
    assert parse_thermalservice("") is None
    assert parse_thermalservice("Current temperature: 41.5 C") == 41.5


def test_collector_shell_failures_skip_metrics() -> None:
    def shell(cmd: str) -> str:
        raise OSError(f"adb fail: {cmd}")

    c = AndroidPerfCollector(shell=shell, package="com.x")
    assert dict(c.collect()) == {}


def test_meminfo_total_row_fallback() -> None:
    text = """
** MEMINFO in pid 1 [com.x] **
TOTAL    12345    10000
"""
    stats = parse_meminfo(text)
    assert stats.total_pss_kb == 12345
