"""adb client protocol, real subprocess runner, and fake for unit tests."""

from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from questline.core.errors import DeviceError


@dataclass(frozen=True, slots=True)
class AdbResult:
    args: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0


@runtime_checkable
class AdbClient(Protocol):
    """Minimal adb command runner (serial optional via -s)."""

    def run(
        self,
        args: Sequence[str],
        *,
        serial: str | None = None,
        check: bool = True,
        timeout: float | None = 60.0,
    ) -> AdbResult: ...


class RealAdb:
    """Invoke the system ``adb`` binary (or an explicit path)."""

    def __init__(self, adb_path: str | None = None) -> None:
        self.adb_path = adb_path or os.environ.get("ANDROID_HOME") and _adb_from_sdk(
            os.environ["ANDROID_HOME"]
        )
        if not self.adb_path:
            found = shutil.which("adb")
            self.adb_path = found or "adb"

    def run(
        self,
        args: Sequence[str],
        *,
        serial: str | None = None,
        check: bool = True,
        timeout: float | None = 60.0,
    ) -> AdbResult:
        cmd = [self.adb_path]
        if serial:
            cmd.extend(["-s", serial])
        cmd.extend(args)
        try:
            completed = subprocess.run(
                cmd,
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except FileNotFoundError as exc:
            raise DeviceError(
                f"adb executable not found ({self.adb_path!r}). "
                "Install Android platform-tools and ensure adb is on PATH "
                "(or set QUESTLINE_ADB_PATH / ANDROID_HOME)."
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise DeviceError(
                f"adb timed out after {timeout}s: {' '.join(cmd)}"
            ) from exc

        result = AdbResult(
            args=tuple(cmd),
            returncode=completed.returncode,
            stdout=completed.stdout or "",
            stderr=completed.stderr or "",
        )
        if check and not result.ok:
            detail = (result.stderr or result.stdout or "").strip() or f"exit {result.returncode}"
            raise DeviceError(f"adb failed ({' '.join(cmd)}): {detail}")
        return result


def _adb_from_sdk(android_home: str) -> str | None:
    candidate = os.path.join(android_home, "platform-tools", "adb")
    if os.name == "nt":
        candidate += ".exe"
    return candidate if os.path.isfile(candidate) else None


Handler = Callable[[Sequence[str], str | None], AdbResult | str | int | None]


@dataclass
class FakeAdb:
    """Scripted adb for unit tests — match by argv prefix / exact tuple.

    Handlers may return:
    - ``AdbResult``
    - ``str`` (stdout, returncode 0)
    - ``int`` (returncode, empty stdout)
    - ``None`` → treat as empty success
    """

    responses: dict[tuple[str, ...], AdbResult | str | int | Handler] = field(
        default_factory=dict
    )
    default: AdbResult | str | int | Handler | None = None
    calls: list[tuple[str | None, tuple[str, ...]]] = field(default_factory=list)

    def add(self, args: Sequence[str], response: AdbResult | str | int | Handler) -> None:
        self.responses[tuple(args)] = response

    def run(
        self,
        args: Sequence[str],
        *,
        serial: str | None = None,
        check: bool = True,
        timeout: float | None = 60.0,
    ) -> AdbResult:
        _ = timeout
        key = tuple(args)
        self.calls.append((serial, key))
        raw = self.responses.get(key, self.default)
        if raw is None:
            # Prefix match for flexible scripts (longest wins).
            matches = [k for k in self.responses if key[: len(k)] == k]
            if matches:
                best = max(matches, key=len)
                raw = self.responses[best]
        if raw is None:
            raise DeviceError(f"FakeAdb has no response for args={key!r} serial={serial!r}")
        result = self._normalize(raw, args, serial)
        if check and not result.ok:
            detail = (result.stderr or result.stdout or "").strip() or f"exit {result.returncode}"
            raise DeviceError(f"adb failed ({' '.join(args)}): {detail}")
        return result

    def _normalize(
        self,
        raw: AdbResult | str | int | Handler,
        args: Sequence[str],
        serial: str | None,
    ) -> AdbResult:
        if callable(raw) and not isinstance(raw, AdbResult):
            out = raw(args, serial)
            if isinstance(out, AdbResult):
                return out
            raw = out  # type: ignore[assignment]
        if isinstance(raw, AdbResult):
            return raw
        if isinstance(raw, str):
            return AdbResult(args=tuple(args), returncode=0, stdout=raw, stderr="")
        if isinstance(raw, int):
            return AdbResult(args=tuple(args), returncode=raw, stdout="", stderr="")
        if raw is None:
            return AdbResult(args=tuple(args), returncode=0, stdout="", stderr="")
        raise DeviceError(f"FakeAdb invalid response type: {type(raw).__name__}")
