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
    # Last pytest/console lines (drained from subprocess stdout) for HUD Status.
    log_tail: str = ""

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
        self._log_lines: list[str] = []
        self._log_lock = threading.Lock()
        self._log_max_lines = 80

    def status(self) -> LaunchStatus:
        self._reconcile_finished()
        with self._lock:
            return LaunchStatus(**asdict(self._status))

    def launch(self, req: LaunchRequest) -> LaunchStatus:
        self._reconcile_finished()
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
                # Do NOT hold the adb lock across the pytest child — the plugin's
                # setup_android_session acquires it. Holding it here caused
                # DeviceError + 0-test failed runs (HUD lock vs pytest lock).
                try:
                    DeviceLock(self.lock_dir).ensure_available(serial)
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
                # PIPE + dedicated drain thread (never unread PIPE — INC-0005).
                # Tail is surfaced on LaunchStatus.log_tail so HUD Status shows
                # session errors that Live (EventBus only) cannot.
                proc = self._spawn(
                    argv,
                    cwd=str(cwd),
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
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
            with self._log_lock:
                self._log_lines = []
            self._status.state = "running"
            self._status.pid = proc.pid
            self._status.log_tail = ""
            threading.Thread(
                target=self._drain_stdout,
                args=(proc,),
                name=f"hud-launcher-log-{job_id}",
                daemon=True,
            ).start()
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

    def _drain_stdout(self, proc: subprocess.Popen[Any]) -> None:
        stream = getattr(proc, "stdout", None)
        if stream is None:
            return
        try:
            for line in stream:
                text = line.rstrip("\r\n")
                with self._log_lock:
                    self._log_lines.append(text)
                    if len(self._log_lines) > self._log_max_lines:
                        self._log_lines = self._log_lines[-self._log_max_lines :]
                    tail = "\n".join(self._log_lines)
                with self._lock:
                    if self._status.job_id:
                        self._status.log_tail = tail
        except Exception:
            logger.debug("launcher stdout drain ended", exc_info=True)
        finally:
            try:
                stream.close()
            except Exception:
                pass

    def _log_tail_snapshot(self) -> str:
        with self._log_lock:
            return "\n".join(self._log_lines)

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
                self._status.log_tail = self._log_tail_snapshot()
                self._status.finished_at = time.time()
                self._release_device_lock()
                self._proc = None
            return
        tail = self._log_tail_snapshot()
        with self._lock:
            self._status.returncode = code
            self._status.finished_at = time.time()
            self._status.state = "finished"
            self._status.pid = None
            self._status.log_tail = tail
            if code not in (0, None) and not self._status.error:
                # Surface pytest/session failures that never became EventBus tests.
                self._status.error = self._format_exit_error(code, tail)
            self._release_device_lock()
            self._proc = None

    @staticmethod
    def _format_exit_error(code: int, tail: str) -> str:
        lines = [ln.strip() for ln in tail.splitlines() if ln.strip()]
        interesting = [
            ln
            for ln in lines
            if ln.startswith(("ERROR ", "FAILED ", "E ", "E\t"))
            or "Error:" in ln
            or "DeviceError" in ln
            or "InfraError" in ln
            or "SessionLost" in ln
            or "short test summary" in ln
            or ln.startswith("!")
        ]
        # Drop coverage noise if anything actionable remains.
        interesting = [
            ln
            for ln in interesting
            if "cov-fail-under" not in ln and "Total coverage" not in ln
        ]
        picked = interesting[-12:] if interesting else lines[-8:]
        detail = " | ".join(picked) if picked else "(see log_tail)"
        return f"pytest exited {code}: {detail}"

    def _reconcile_finished(self) -> None:
        """If the child exited but the waiter has not updated yet, sync status."""
        with self._lock:
            proc = self._proc
            if proc is None or self._status.state not in {"starting", "running", "stopping"}:
                return
            code = proc.poll()
            if code is None:
                return
            self._status.returncode = code
            self._status.finished_at = time.time()
            self._status.state = "finished"
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
        # Clear repo pyproject addopts (``--cov --cov-fail-under=85``). Live HUD
        # runs are not the coverage gate — cov floods logs and fails green suites.
        argv.extend(["-o", "addopts=", "-q", "--tb=short"])
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
