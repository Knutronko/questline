"""In-memory logcat ring buffer with optional on-demand dump via adb."""

from __future__ import annotations

from collections import deque
from collections.abc import Callable

from questline.devices.adb.client import AdbClient


class LogcatBuffer:
    """Ring buffer of logcat lines; dump via ``adb logcat -d`` when refreshed."""

    def __init__(self, *, maxlen: int = 5000) -> None:
        self._lines: deque[str] = deque(maxlen=maxlen)

    def clear(self) -> None:
        self._lines.clear()

    def extend(self, text: str) -> None:
        for line in text.splitlines():
            self._lines.append(line)

    def text(self) -> str:
        return "\n".join(self._lines)

    def refresh_from_adb(
        self,
        adb: AdbClient,
        *,
        serial: str,
        clear_device: bool = False,
    ) -> str:
        if clear_device:
            adb.run(["logcat", "-c"], serial=serial, check=False)
            self.clear()
        result = adb.run(["logcat", "-d"], serial=serial, check=False)
        self.extend(result.stdout)
        return self.text()


def dump_logcat(
    adb: AdbClient,
    *,
    serial: str,
    buffer: LogcatBuffer | None = None,
    clear: bool = False,
) -> str:
    buf = buffer or LogcatBuffer()
    return buf.refresh_from_adb(adb, serial=serial, clear_device=clear)


# Type alias for injection in tests
LogcatDumper = Callable[[str], str]
