"""Managed pytest subprocess launcher for the HUD control center."""

from __future__ import annotations

import logging
import os
import signal
import subprocess
import sys
import threading
import time
import uuid
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from questline.core.errors import DeviceError
from questline.devices.adb.lock import DeviceLock

logger = logging.getLogger("questline.hud.launcher")

SpawnFn = Callable[..., subprocess.Popen[Any]]


@dataclass
class LaunchRequest:
    profile: str
    tests: list[str] = field(default_factory=list)
    markers: str | None = None
    device_serial: str | None = None
    reporters: list[str] | None = None
    config_path: Path | None = None
    include_quarantined: bool = False
    extra_env: dict[str, str] = field(default_factory=dict)
    cwd: Path | None = None


@dataclass
class LaunchStatus:
    job_id: str | None = None
    state: str = "idle"  # idle | starting | running | stopping | finished | error
    profile: str | None = None
    pid: int | None = None
    argv: list[str] = field(default_factory=list)
    started_at: float | None = None
    finished_at: float | None = None
    returncode: int | None = None
    error: str | None = None
    device_serial: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class RunLauncher:
    """One-at-a-time managed pytest run (same public flags as CLI/plugin)."""

    def __init__(
        self,
        *,
        project_root: Path,
        config_path: Path | None = None,
        forward_url: str | None = None,
        csrf_token: str | None = None,
        lock_dir: Path | None = None,
        spawn: SpawnFn | None = None,
    ) -> None:
        self.project_root = Path(project_root).resolve()
        if config_path:
            self.config_path = Path(config_path)
        else:
            self.config_path = self.project_root / "questline.toml"
        self.forward_url = forward_url
        self.csrf_token = csrf_token
        if lock_dir:
            self.lock_dir = Path(lock_dir)
        else:
            self.lock_dir = self.project_root / ".questline" / "device-locks"
        self._spawn = spawn or subprocess.Popen
        self._lock = threading.Lock()
        self._proc: subprocess.Popen[Any] | None = None
        self._device_lock: DeviceLock | None = None
        self._held_serial: str | None = None
        self._status = LaunchStatus()
        self._waiter: threading.Thread | None = None

    def status(self) -> LaunchStatus:
        with self._lock:
            return LaunchStatus(**asdict(self._status))

    def launch(self, req: LaunchRequest) -> LaunchStatus:
        with self._lock:
            if self._status.state in {"starting", "running", "stopping"}:
                raise RuntimeError(
                    f"a run is already {self._status.state} (job {self._status.job_id}); "
                    "stop it before launching another"
                )
            job_id = uuid.uuid4().hex[:12]
            argv = self._build_argv(req)
            env = self._build_env(req)
            cwd = Path(req.cwd) if req.cwd else self.project_root

            serial = req.device_serial
            if serial:
                try:
                    self._device_lock = DeviceLock(self.lock_dir)
                    self._device_lock.acquire(serial, owner=f"hud-launcher:{job_id}")
                    self._held_serial = serial
                except DeviceError as exc:
                    self._status = LaunchStatus(
                        job_id=job_id,
                        state="error",
                        profile=req.profile,
                        error=str(exc),
                        device_serial=serial,
                    )
                    raise

            self._status = LaunchStatus(
                job_id=job_id,
                state="starting",
                profile=req.profile,
                argv=argv,
                started_at=time.time(),
                device_serial=serial,
            )
            try:
                proc = self._spawn(
                    argv,
                    cwd=str(cwd),
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    # Windows: create new process group for cleaner terminate.
                    creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
                )
            except Exception as exc:
                self._release_device_lock()
                self._status = LaunchStatus(
                    job_id=job_id,
                    state="error",
                    profile=req.profile,
                    argv=argv,
                    error=str(exc),
                    device_serial=serial,
                    finished_at=time.time(),
                )
                raise

            self._proc = proc
            self._status.state = "running"
            self._status.pid = proc.pid
            self._waiter = threading.Thread(
                target=self._wait_proc,
                name=f"hud-launcher-{job_id}",
                daemon=True,
            )
            self._waiter.start()
            return LaunchStatus(**asdict(self._status))

    def stop(self, *, grace_s: float = 5.0) -> LaunchStatus:
        with self._lock:
            proc = self._proc
            if proc is None or self._status.state not in {"starting", "running"}:
                return LaunchStatus(**asdict(self._status))
            self._status.state = "stopping"
            pid = proc.pid
        try:
            if sys.platform == "win32":
                proc.send_signal(signal.CTRL_BREAK_EVENT)  # type: ignore[attr-defined]
            else:
                proc.send_signal(signal.SIGTERM)
        except (ProcessLookupError, OSError, ValueError):
            logger.debug("stop: process already gone", exc_info=True)
        deadline = time.time() + grace_s
        while time.time() < deadline:
            if proc.poll() is not None:
                break
            time.sleep(0.1)
        if proc.poll() is None:
            try:
                proc.kill()
            except OSError:
                logger.debug("stop: kill failed for pid %s", pid, exc_info=True)
        # waiter thread finalizes status
        if self._waiter is not None:
            self._waiter.join(timeout=grace_s + 2.0)
        return self.status()

    def _wait_proc(self) -> None:
        proc = self._proc
        if proc is None:
            return
        code: int | None = None
        try:
            code = proc.wait()
        except Exception as exc:
            logger.exception("launcher wait failed")
            with self._lock:
                self._status.state = "error"
                self._status.error = str(exc)
                self._status.finished_at = time.time()
                self._release_device_lock()
                self._proc = None
            return
        with self._lock:
            self._status.returncode = code
            self._status.finished_at = time.time()
            self._status.state = "finished" if code == 0 else "finished"
            self._status.pid = None
            self._release_device_lock()
            self._proc = None

    def _release_device_lock(self) -> None:
        if self._device_lock is not None and self._held_serial:
            try:
                self._device_lock.release(self._held_serial)
            except DeviceError:
                logger.exception("failed to release HUD device lock")
        self._device_lock = None
        self._held_serial = None

    def _build_argv(self, req: LaunchRequest) -> list[str]:
        argv = [sys.executable, "-m", "pytest"]
        cfg = req.config_path or self.config_path
        if cfg.is_file():
            argv.extend(["--questline-config", str(cfg)])
        argv.extend(["--questline-profile", req.profile])
        if req.include_quarantined:
            argv.append("--include-quarantined")
        if req.markers:
            argv.extend(["-m", req.markers])
        if req.tests:
            argv.extend(req.tests)
        else:
            argv.append(".")
        argv.extend(["-q", "--tb=short"])
        return argv

    def _build_env(self, req: LaunchRequest) -> dict[str, str]:
        env = dict(os.environ)
        env["QUESTLINE_PROFILE"] = req.profile
        if req.device_serial:
            env["QUESTLINE_DEVICE_SERIAL"] = req.device_serial
        if req.reporters is not None:
            env["QUESTLINE_REPORTERS"] = ",".join(req.reporters)
        if self.forward_url:
            env["QUESTLINE_HUD_FORWARD_URL"] = self.forward_url
        if self.csrf_token:
            env["QUESTLINE_HUD_CSRF"] = self.csrf_token
        env.update(req.extra_env)
        return env
