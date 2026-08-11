"""Android adb performance collectors and dumpsys /proc parsers."""

from __future__ import annotations

import logging
import re
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("questline.perf.android")

# --- parsers (pure; fixture-tested) -------------------------------------------------


@dataclass(frozen=True, slots=True)
class GfxInfoStats:
    """Parsed ``dumpsys gfxinfo`` summary."""

    total_frames: int | None = None
    janky_frames: int | None = None
    jank_pct: float | None = None
    percentile_50_ms: float | None = None
    package: str | None = None


_GFX_TOTAL = re.compile(r"Total frames rendered:\s*(\d+)", re.I)
_GFX_JANKY = re.compile(
    r"Janky frames:\s*(\d+)\s*\(([0-9.]+)\s*%\)",
    re.I,
)
_GFX_P50 = re.compile(r"50th percentile:\s*([0-9.]+)\s*ms", re.I)
_GFX_PKG = re.compile(r"Graphics info for pid\s+\d+\s*\[([^\]]+)\]", re.I)


def parse_gfxinfo(text: str) -> GfxInfoStats:
    """Parse ``dumpsys gfxinfo`` output. Missing fields stay None (never raises)."""
    if not text or not text.strip():
        logger.warning("gfxinfo parse: empty output — metric unavailable")
        return GfxInfoStats()
    total = _match_int(_GFX_TOTAL, text)
    janky = None
    jank_pct = None
    m = _GFX_JANKY.search(text)
    if m:
        try:
            janky = int(m.group(1))
            jank_pct = float(m.group(2))
        except ValueError:
            logger.warning("gfxinfo parse: bad janky line — metric unavailable")
    p50 = _match_float(_GFX_P50, text)
    pkg_m = _GFX_PKG.search(text)
    package = pkg_m.group(1).strip() if pkg_m else None
    if total is None and p50 is None and jank_pct is None:
        logger.warning("gfxinfo parse: no recognized fields — metric unavailable")
    return GfxInfoStats(
        total_frames=total,
        janky_frames=janky,
        jank_pct=jank_pct,
        percentile_50_ms=p50,
        package=package,
    )


@dataclass(frozen=True, slots=True)
class MemInfoStats:
    """Parsed ``dumpsys meminfo`` PSS."""

    total_pss_kb: float | None = None
    package: str | None = None

    @property
    def total_pss_mb(self) -> float | None:
        if self.total_pss_kb is None:
            return None
        return self.total_pss_kb / 1024.0


# App Summary TOTAL PSS (Android 8+) or classic TOTAL row.
_MEM_APP_TOTAL = re.compile(
    r"TOTAL\s+PSS:\s*([\d,]+)\s*(?:kB|KB)?",
    re.I,
)
_MEM_TOTAL_ROW = re.compile(
    r"^TOTAL\s+(\d+)",
    re.M,
)
_MEM_PKG = re.compile(r"MEMINFO in pid\s+\d+\s*\[([^\]]+)\]", re.I)


def parse_meminfo(text: str) -> MemInfoStats:
    """Parse ``dumpsys meminfo`` for TOTAL PSS (kB). Never raises."""
    if not text or not text.strip():
        logger.warning("meminfo parse: empty output — metric unavailable")
        return MemInfoStats()
    pss_kb: float | None = None
    m = _MEM_APP_TOTAL.search(text)
    if m:
        pss_kb = _parse_int_commas(m.group(1))
    if pss_kb is None:
        m2 = _MEM_TOTAL_ROW.search(text)
        if m2:
            pss_kb = _parse_int_commas(m2.group(1))
    if pss_kb is None:
        logger.warning("meminfo parse: TOTAL PSS not found — metric unavailable")
    pkg_m = _MEM_PKG.search(text)
    package = pkg_m.group(1).strip() if pkg_m else None
    return MemInfoStats(total_pss_kb=pss_kb, package=package)


@dataclass(frozen=True, slots=True)
class ProcStatSample:
    """Fields from ``/proc/<pid>/stat`` used for CPU%."""

    utime: int
    stime: int
    cutime: int
    cstime: int

    @property
    def total_jiffies(self) -> int:
        return self.utime + self.stime + self.cutime + self.cstime


def parse_proc_stat(text: str) -> ProcStatSample | None:
    """Parse one line of ``/proc/<pid>/stat``. Returns None on failure."""
    if not text or not text.strip():
        logger.warning("proc_stat parse: empty — metric unavailable")
        return None
    line = text.strip().splitlines()[0]
    # comm may contain spaces/parentheses: pid (comm) state ...
    try:
        close = line.rfind(")")
        if close < 0:
            raise ValueError("missing comm")
        rest = line[close + 1 :].split()
        # After state: ppid ... utime(11) stime(12) cutime(13) cstime(14) — 0-index in rest: 11-14?
        # rest[0]=state, rest[11]=utime, rest[12]=stime, rest[13]=cutime, rest[14]=cstime
        utime = int(rest[11])
        stime = int(rest[12])
        cutime = int(rest[13])
        cstime = int(rest[14])
    except (IndexError, ValueError) as exc:
        logger.warning("proc_stat parse failed: %s — metric unavailable", exc)
        return None
    return ProcStatSample(utime=utime, stime=stime, cutime=cutime, cstime=cstime)


@dataclass(frozen=True, slots=True)
class BatteryStats:
    level: float | None = None
    temperature_c: float | None = None


_BAT_LEVEL = re.compile(r"^\s*level:\s*(\d+)", re.M | re.I)
_BAT_TEMP = re.compile(r"^\s*temperature:\s*(-?\d+)", re.M | re.I)
# thermalservice / dumpsys thermalservice temperatures: ... or Temperature{...mValue=XX.X...}
_THERMAL_VALUE = re.compile(r"mValue\s*=\s*([0-9.]+)", re.I)
_THERMAL_TEMP_C = re.compile(
    r"(?:Current\s+)?temp(?:erature)?(?:\s*\(.*?\))?:\s*([0-9.]+)\s*(?:C|°C)?",
    re.I,
)


def parse_battery(text: str) -> BatteryStats:
    """Parse ``dumpsys battery``. Temperature is tenths of °C on Android."""
    if not text or not text.strip():
        logger.warning("battery parse: empty — metric unavailable")
        return BatteryStats()
    level = _match_float(_BAT_LEVEL, text)
    temp_raw = _match_float(_BAT_TEMP, text)
    temperature_c = None
    if temp_raw is not None:
        # Android reports temperature in tenths of a degree Celsius.
        temperature_c = temp_raw / 10.0
    return BatteryStats(level=level, temperature_c=temperature_c)


def parse_thermalservice(text: str) -> float | None:
    """Best-effort CPU/skin temperature (°C) from ``dumpsys thermalservice``."""
    if not text or not text.strip():
        return None
    values: list[float] = []
    for m in _THERMAL_VALUE.finditer(text):
        try:
            values.append(float(m.group(1)))
        except ValueError:
            continue
    if values:
        return max(values)
    m2 = _THERMAL_TEMP_C.search(text)
    if m2:
        try:
            return float(m2.group(1))
        except ValueError:
            return None
    return None


def _match_int(pattern: re.Pattern[str], text: str) -> int | None:
    m = pattern.search(text)
    if not m:
        return None
    try:
        return int(m.group(1).replace(",", ""))
    except ValueError:
        return None


def _match_float(pattern: re.Pattern[str], text: str) -> float | None:
    m = pattern.search(text)
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", ""))
    except ValueError:
        return None


def _parse_int_commas(raw: str) -> float | None:
    try:
        return float(raw.replace(",", ""))
    except ValueError:
        return None


# --- collectors ---------------------------------------------------------------------


ShellFn = Callable[[str], str]


@dataclass
class AndroidPerfCollector:
    """Collect FPS/jank, PSS, CPU%, battery from a device via shell commands.

    ``shell`` is typically ``provider.shell(device, cmd)`` bound for one device.
    """

    shell: ShellFn
    package: str
    clock: Callable[[], float] = field(default=time.monotonic)
    _prev_frames: int | None = field(default=None, init=False, repr=False)
    _prev_frames_t: float | None = field(default=None, init=False, repr=False)
    _prev_proc: ProcStatSample | None = field(default=None, init=False, repr=False)
    _prev_proc_t: float | None = field(default=None, init=False, repr=False)
    _pid: str | None = field(default=None, init=False, repr=False)

    def collect(self) -> Mapping[str, float]:
        out: dict[str, float] = {}
        out.update(self._collect_gfx())
        out.update(self._collect_mem())
        out.update(self._collect_cpu())
        out.update(self._collect_battery())
        return out

    def _collect_gfx(self) -> dict[str, float]:
        try:
            text = self.shell(f"dumpsys gfxinfo {self.package}")
        except Exception as exc:
            logger.warning("gfxinfo shell failed: %s — metric unavailable", exc)
            return {}
        stats = parse_gfxinfo(text)
        result: dict[str, float] = {}
        now = self.clock()
        if stats.jank_pct is not None:
            result["jank_pct"] = stats.jank_pct
        fps: float | None = None
        if stats.total_frames is not None:
            if self._prev_frames is not None and self._prev_frames_t is not None:
                dt = now - self._prev_frames_t
                dframes = stats.total_frames - self._prev_frames
                if dt > 0 and dframes >= 0:
                    fps = dframes / dt
            self._prev_frames = stats.total_frames
            self._prev_frames_t = now
        if fps is None and stats.percentile_50_ms is not None and stats.percentile_50_ms > 0:
            fps = 1000.0 / stats.percentile_50_ms
        if fps is not None:
            result["fps"] = fps
        return result

    def _collect_mem(self) -> dict[str, float]:
        try:
            text = self.shell(f"dumpsys meminfo {self.package}")
        except Exception as exc:
            logger.warning("meminfo shell failed: %s — metric unavailable", exc)
            return {}
        stats = parse_meminfo(text)
        if stats.total_pss_mb is None:
            return {}
        return {"memory_pss_mb": stats.total_pss_mb}

    def _resolve_pid(self) -> str | None:
        if self._pid:
            return self._pid
        for cmd in (
            f"pidof -s {self.package}",
            f"pidof {self.package}",
        ):
            try:
                raw = self.shell(cmd).strip()
            except Exception:
                continue
            if raw and raw.split()[0].isdigit():
                self._pid = raw.split()[0]
                return self._pid
        try:
            # Fallback: dumpsys activity processes | grep package (best-effort).
            text = self.shell(f"dumpsys activity processes {self.package}")
            m = re.search(r"pid[= ](\d+)", text, re.I)
            if m:
                self._pid = m.group(1)
                return self._pid
        except Exception:
            pass
        logger.warning("could not resolve pid for %s — cpu unavailable", self.package)
        return None

    def _collect_cpu(self) -> dict[str, float]:
        pid = self._resolve_pid()
        if not pid:
            return {}
        try:
            text = self.shell(f"cat /proc/{pid}/stat")
        except Exception as exc:
            logger.warning("proc stat shell failed: %s — metric unavailable", exc)
            return {}
        sample = parse_proc_stat(text)
        if sample is None:
            return {}
        now = self.clock()
        result: dict[str, float] = {}
        if self._prev_proc is not None and self._prev_proc_t is not None:
            dt = now - self._prev_proc_t
            dj = sample.total_jiffies - self._prev_proc.total_jiffies
            if dt > 0 and dj >= 0:
                # Approximate % of one core: jiffies are typically 100 Hz.
                hz = 100.0
                result["cpu_pct"] = max(0.0, (dj / hz) / dt * 100.0)
        self._prev_proc = sample
        self._prev_proc_t = now
        return result

    def _collect_battery(self) -> dict[str, float]:
        result: dict[str, float] = {}
        try:
            bat = parse_battery(self.shell("dumpsys battery"))
        except Exception as exc:
            logger.warning("battery shell failed: %s — metric unavailable", exc)
            bat = BatteryStats()
        if bat.level is not None:
            result["battery_level"] = bat.level
        if bat.temperature_c is not None:
            result["battery_temp_c"] = bat.temperature_c
        try:
            thermal = parse_thermalservice(self.shell("dumpsys thermalservice"))
        except Exception:
            thermal = None
        if thermal is not None and "battery_temp_c" not in result:
            result["battery_temp_c"] = thermal
        elif thermal is not None:
            result["thermal_temp_c"] = thermal
        return result


def bind_android_shell(provider: Any, device: Any) -> ShellFn:
    """Adapt ``DevicePort.shell(device, cmd)`` to ``ShellFn``."""

    def _shell(command: str) -> str:
        return provider.shell(device, command)

    return _shell
