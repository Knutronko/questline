"""Android dumpsys /proc parsers against recorded fixtures."""

from __future__ import annotations

from pathlib import Path

from questline.perf.android import (
    AndroidPerfCollector,
    parse_battery,
    parse_gfxinfo,
    parse_meminfo,
    parse_proc_stat,
    parse_thermalservice,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "perf"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_parse_gfxinfo_android10() -> None:
    stats = parse_gfxinfo(_read("gfxinfo_android10.txt"))
    assert stats.total_frames == 1800
    assert stats.janky_frames == 90
    assert stats.jank_pct == 5.0
    assert stats.percentile_50_ms == 16.5
    assert stats.package == "com.example.game"


def test_parse_gfxinfo_android13() -> None:
    stats = parse_gfxinfo(_read("gfxinfo_android13.txt"))
    assert stats.total_frames == 2400
    assert stats.jank_pct == 2.0
    assert stats.percentile_50_ms == 8.2


def test_parse_gfxinfo_empty_degrades() -> None:
    stats = parse_gfxinfo("")
    assert stats.total_frames is None
    assert stats.jank_pct is None


def test_parse_meminfo_android10_and_13() -> None:
    a10 = parse_meminfo(_read("meminfo_android10.txt"))
    assert a10.total_pss_kb == 90000
    assert a10.total_pss_mb == 90000 / 1024.0
    a13 = parse_meminfo(_read("meminfo_android13.txt"))
    assert a13.total_pss_kb == 130024


def test_parse_battery_temp_tenths() -> None:
    bat = parse_battery(_read("battery_android10.txt"))
    assert bat.level == 84
    assert bat.temperature_c == 31.2
    bat13 = parse_battery(_read("battery_android13.txt"))
    assert bat13.level == 97
    assert bat13.temperature_c == 28.5


def test_parse_thermalservice() -> None:
    assert parse_thermalservice(_read("thermalservice_android13.txt")) == 36.5


def test_parse_proc_stat() -> None:
    sample = parse_proc_stat(_read("proc_stat_sample.txt"))
    assert sample is not None
    assert sample.utime == 500
    assert sample.stime == 200
    assert sample.cutime == 10
    assert sample.cstime == 5
    assert sample.total_jiffies == 715


def test_android_collector_delta_fps_and_cpu() -> None:
    clock = {"t": 0.0}

    def now() -> float:
        return clock["t"]

    responses = {
        "dumpsys gfxinfo com.example.game": _read("gfxinfo_android10.txt"),
        "dumpsys meminfo com.example.game": _read("meminfo_android10.txt"),
        "dumpsys battery": _read("battery_android10.txt"),
        "dumpsys thermalservice": _read("thermalservice_android13.txt"),
        "pidof -s com.example.game": "4321\n",
        "cat /proc/4321/stat": _read("proc_stat_sample.txt"),
    }

    def shell(cmd: str) -> str:
        if cmd in responses:
            return responses[cmd]
        raise AssertionError(f"unexpected shell: {cmd}")

    collector = AndroidPerfCollector(shell=shell, package="com.example.game", clock=now)
    first = dict(collector.collect())
    assert first["jank_pct"] == 5.0
    assert first["memory_pss_mb"] == 90000 / 1024.0
    assert first["battery_level"] == 84
    assert "fps" in first  # from p50 on first tick
    assert "cpu_pct" not in first  # needs a prior sample

    # Advance frames + jiffies for deltas.
    responses["dumpsys gfxinfo com.example.game"] = _read("gfxinfo_android10.txt").replace(
        "Total frames rendered: 1800", "Total frames rendered: 1860"
    )
    responses["cat /proc/4321/stat"] = _read("proc_stat_sample.txt").replace(
        "500 200 10 5", "600 250 10 5"
    )
    clock["t"] = 1.0
    second = dict(collector.collect())
    assert second["fps"] == 60.0  # 60 frames / 1s
    assert second["cpu_pct"] == 150.0  # 150 jiffies @ 100Hz over 1s → 150%
