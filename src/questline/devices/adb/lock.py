"""Exclusive device lock files (two runs cannot grab the same serial)."""

from __future__ import annotations

import os
import time
from pathlib import Path

from questline.core.errors import DeviceError


class DeviceLock:
    """PID-file lock under a directory (Windows-friendly exclusive create)."""

    def __init__(self, lock_dir: Path) -> None:
        self.lock_dir = Path(lock_dir)
        self.lock_dir.mkdir(parents=True, exist_ok=True)
        self._held: dict[str, Path] = {}

    def path_for(self, serial: str) -> Path:
        safe = "".join(c if c.isalnum() or c in "-._" else "_" for c in serial)
        return self.lock_dir / f"{safe}.lock"

    def ensure_available(self, serial: str, *, stale_s: float = 0.0) -> None:
        """Raise if *serial* is locked by a live process; remove stale lock files.

        Does **not** acquire — used by the HUD launcher so pytest can still take
        the real exclusive lock inside ``setup_android_session``.
        """
        path = self.path_for(serial)
        if not path.exists():
            return
        if self._is_stale(path, stale_s=stale_s):
            try:
                path.unlink(missing_ok=True)
            except OSError as exc:
                raise DeviceError(
                    f"device {serial!r} lock is stale but could not be removed "
                    f"({path}): {exc}"
                ) from exc
            return
        other = _read_lock(path)
        raise DeviceError(
            f"device {serial!r} is locked by another questline run "
            f"({other.strip() or path}). Wait for that run to finish or remove "
            f"the lock file if the process is dead: {path}"
        )

    def acquire(self, serial: str, *, owner: str | None = None, stale_s: float = 0.0) -> None:
        if serial in self._held:
            return
        path = self.path_for(serial)
        payload = f"pid={os.getpid()}\nowner={owner or ''}\nacquired_at={time.time():.3f}\n"
        try:
            fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            if self._is_stale(path, stale_s=stale_s):
                try:
                    path.unlink(missing_ok=True)
                except OSError as exc:
                    raise DeviceError(
                        f"device {serial!r} lock is stale but could not be removed "
                        f"({path}): {exc}"
                    ) from exc
                return self.acquire(serial, owner=owner, stale_s=stale_s)
            other = _read_lock(path)
            raise DeviceError(
                f"device {serial!r} is locked by another questline run "
                f"({other.strip() or path}). Wait for that run to finish or remove "
                f"the lock file if the process is dead: {path}"
            )
        try:
            os.write(fd, payload.encode("utf-8"))
        finally:
            os.close(fd)
        self._held[serial] = path

    def release(self, serial: str) -> None:
        path = self._held.pop(serial, None)
        if path is None:
            return
        try:
            text = _read_lock(path)
            if f"pid={os.getpid()}" in text or not text:
                path.unlink(missing_ok=True)
        except OSError as exc:
            raise DeviceError(f"failed to release device lock for {serial!r}: {exc}") from exc

    def release_all(self) -> None:
        for serial in list(self._held):
            self.release(serial)

    def _is_stale(self, path: Path, *, stale_s: float) -> bool:
        text = _read_lock(path)
        pid = _pid_from_lock(text)
        if pid is not None and not _pid_alive(pid):
            return True
        if stale_s > 0:
            try:
                age = time.time() - path.stat().st_mtime
                if age >= stale_s:
                    return True
            except OSError:
                return True
        return False


def _read_lock(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _pid_from_lock(text: str) -> int | None:
    for line in text.splitlines():
        if line.startswith("pid="):
            raw = line.split("=", 1)[1].strip()
            try:
                return int(raw)
            except ValueError:
                return None
    return None


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        return _pid_alive_windows(pid)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _pid_alive_windows(pid: int) -> bool:
    try:
        import ctypes

        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        handle = ctypes.windll.kernel32.OpenProcess(  # type: ignore[attr-defined]
            PROCESS_QUERY_LIMITED_INFORMATION, False, pid
        )
        if handle:
            ctypes.windll.kernel32.CloseHandle(handle)  # type: ignore[attr-defined]
            return True
        return False
    except Exception:
        return False
