"""Best-effort AVD emulator start + boot wait (Windows-friendly)."""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from collections.abc import Callable
from pathlib import Path

from questline.core.errors import DeviceError
from questline.devices.adb.client import AdbClient
from questline.devices.adb.parse import online_devices


def find_emulator_binary(emulator_path: str | None = None) -> str:
    if emulator_path:
        return emulator_path
    env = os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT")
    if env:
        candidate = Path(env) / "emulator" / ("emulator.exe" if os.name == "nt" else "emulator")
        if candidate.is_file():
            return str(candidate)
    found = shutil.which("emulator")
    if found:
        return found
    raise DeviceError(
        "emulator binary not found. Install Android SDK emulator tools and ensure "
        "`emulator` is on PATH, or set ANDROID_HOME / QUESTLINE_EMULATOR_PATH."
    )


def start_avd(
    avd_name: str,
    *,
    emulator_path: str | None = None,
    extra_args: list[str] | None = None,
    popen: Callable[..., subprocess.Popen[str]] = subprocess.Popen,
) -> subprocess.Popen[str]:
    """Launch ``emulator -avd <name>`` detached (best-effort)."""
    binary = find_emulator_binary(emulator_path)
    cmd = [binary, "-avd", avd_name]
    if extra_args:
        cmd.extend(extra_args)
    try:
        # DETACHED_PROCESS on Windows so pytest/session exit does not kill it immediately.
        kwargs: dict[str, object] = {
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
            "stdin": subprocess.DEVNULL,
        }
        if os.name == "nt":
            kwargs["creationflags"] = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(
                subprocess, "CREATE_NEW_PROCESS_GROUP", 0
            )
        else:
            kwargs["start_new_session"] = True
        return popen(cmd, **kwargs)  # type: ignore[arg-type]
    except FileNotFoundError as exc:
        raise DeviceError(
            f"failed to start emulator {avd_name!r}: binary not found ({binary})"
        ) from exc
    except OSError as exc:
        raise DeviceError(f"failed to start emulator {avd_name!r}: {exc}") from exc


def wait_for_boot(
    adb: AdbClient,
    *,
    serial: str | None = None,
    timeout_s: float = 180.0,
    poll_s: float = 2.0,
    clock: Callable[[], float] = time.monotonic,
    sleeper: Callable[[float], None] = time.sleep,
) -> str:
    """Wait until an online device reports ``sys.boot_completed=1``.

    Returns the serial that booted.
    """
    deadline = clock() + timeout_s
    last_err = "no device online"
    while clock() < deadline:
        try:
            listed = adb.run(["devices", "-l"], check=False)
            devices = online_devices(listed.stdout)
        except DeviceError as exc:
            last_err = str(exc)
            sleeper(poll_s)
            continue
        candidates = [d for d in devices if serial is None or d.id == serial]
        if not candidates and serial and serial.startswith("emulator-"):
            # Emulator serial may appear after boot; keep waiting.
            sleeper(poll_s)
            continue
        for dev in candidates:
            boot = adb.run(
                ["shell", "getprop", "sys.boot_completed"],
                serial=dev.id,
                check=False,
            )
            if boot.stdout.strip() == "1":
                return dev.id
            last_err = f"device {dev.id} online but boot_completed={boot.stdout.strip()!r}"
        sleeper(poll_s)
    raise DeviceError(
        f"emulator/device did not finish booting within {timeout_s:.0f}s ({last_err}). "
        "See docs/android.md troubleshooting."
    )


def ensure_emulator(
    avd_name: str,
    adb: AdbClient,
    *,
    emulator_path: str | None = None,
    timeout_s: float = 180.0,
    start_if_needed: bool = True,
) -> str:
    """If no online device, optionally start *avd_name* and wait for boot.

    Returns a ready device serial.
    """
    listed = adb.run(["devices", "-l"], check=False)
    online = online_devices(listed.stdout)
    if online:
        # Prefer an already-booted device; if boot prop missing, wait on first.
        try:
            return wait_for_boot(adb, serial=online[0].id, timeout_s=min(timeout_s, 30.0))
        except DeviceError:
            if not start_if_needed:
                raise
    if not start_if_needed:
        raise DeviceError(
            f"no online Android device/emulator and start_if_needed=False "
            f"(configured AVD={avd_name!r})."
        )
    start_avd(avd_name, emulator_path=emulator_path)
    return wait_for_boot(adb, timeout_s=timeout_s)
