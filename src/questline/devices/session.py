"""Session helpers to acquire/prepare an Android device for a pytest run."""

from __future__ import annotations

import json
import socket
import time
from pathlib import Path
from typing import Any

from questline.core.config import Settings
from questline.core.errors import DeviceError
from questline.devices.adb import LocalAdbProvider
from questline.devices.adb.client import AdbClient, RealAdb
from questline.devices.adb.emulator import ensure_emulator
from questline.devices.port import Device, DeviceSpec, PortMapping


def needs_adb_device(settings: Settings) -> bool:
    device_name = (settings.device or "").lower()
    platform = (settings.target_platform or "").lower()
    return device_name in {"adb", "android", "android_local"} or platform == "android"


def _dismiss_android_system_dialogs(adb: AdbClient, serial: str) -> None:
    """Best-effort dismiss of blocking system UI (e.g. DeprecatedAbi / 32-bit warning).

    Mono + ARMv7 Questline Dev APKs trigger Android 14+ ABI warnings on 64-bit
    devices. Wire only starts once Unity has focus — ENTER / center tap usually
    clears the dialog without requiring a maintainer tap.
    """
    for args in (
        ["shell", "input", "keyevent", "KEYCODE_WAKEUP"],
        ["shell", "wm", "dismiss-keyguard"],
        ["shell", "input", "keyevent", "KEYCODE_ENTER"],
        ["shell", "input", "keyevent", "KEYCODE_DPAD_CENTER"],
        # Rough center tap on common phone resolutions (no-op if off-dialog).
        ["shell", "input", "tap", "540", "1400"],
    ):
        try:
            adb.run(args, serial=serial, check=False)
        except Exception:  # pragma: no cover - best-effort infra
            pass


def wait_for_wire_ready(
    *,
    adb: AdbClient,
    device: Device,
    host: str,
    port: int,
    timeout_s: float,
    interval_s: float = 0.5,
) -> None:
    """Poll until a Wire ``hello`` succeeds via host ``adb forward``.

    Also nudges system dialogs that steal focus before Unity Awake can bind.
    """
    deadline = time.monotonic() + max(timeout_s, 1.0)
    last_err = "not attempted"
    hello = (
        json.dumps({"v": 1, "id": "ready", "op": "hello", "params": {}}) + "\n"
    ).encode("utf-8")
    while time.monotonic() < deadline:
        _dismiss_android_system_dialogs(adb, device.id)
        try:
            with socket.create_connection((host, port), timeout=1.5) as sock:
                sock.settimeout(2.0)
                sock.sendall(hello)
                buf = b""
                while b"\n" not in buf:
                    chunk = sock.recv(4096)
                    if not chunk:
                        raise OSError("peer closed before hello reply")
                    buf += chunk
                line = buf.split(b"\n", 1)[0].decode("utf-8")
                msg = json.loads(line)
                if msg.get("ok") is True:
                    return
                last_err = f"hello not ok: {msg!r}"
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            last_err = str(exc)
        time.sleep(interval_s)
    raise DeviceError(
        f"QuestlineWire not ready on {host}:{port} within {timeout_s:.0f}s "
        f"({last_err}). Dismiss any DeprecatedAbi / 'Android version not "
        f"supported' system dialog on the device, confirm logcat shows "
        f"[QuestlineWire] listening, and use adb forward (not reverse) for "
        f"driver=questline. See docs/android.md."
    )


def setup_android_session(
    settings: Settings,
    *,
    adb: AdbClient | None = None,
    provider: LocalAdbProvider | None = None,
    start_emulator: bool = True,
) -> dict[str, Any]:
    """Acquire device, mount ports, optional install/launch.

    Port direction depends on the live driver:

    - ``driver = "questline"`` (Wire): **``adb forward``** (host→device). Wire
      listens on the device; ``adb reverse`` would steal device ``:port`` and
      Wire fails with "Address already in use".
    - ``driver = "alttester"`` (legacy) and other cases: **``adb reverse``**
      (device→host) so the app can connect out to a host-side hub.

    Returns ``{"provider": LocalAdbProvider, "device": Device}``.
    Caller must ``teardown_android_session`` (or ``provider.release``).
    """
    client = adb or RealAdb(settings.adb_path)
    prov = provider or LocalAdbProvider(
        adb=client,
        lock_dir=settings.questline_dir / "device-locks",
    )
    if start_emulator and settings.emulator_avd and not prov.list_devices():
        ensure_emulator(
            settings.emulator_avd,
            client,
            emulator_path=settings.emulator_path,
        )

    caps: dict[str, str] = {}
    if settings.expected_app_version:
        caps["expected_version"] = settings.expected_app_version
    spec = DeviceSpec(
        platform="android",
        id=settings.device_serial or None,
        caps=caps,
    )
    device: Device = prov.acquire(spec)

    tunnel_port = settings.reverse_port or settings.target_port
    driver = (settings.driver or "").lower()
    use_forward = driver == "questline"
    try:
        # Drop any leftover reverse/forward so the chosen direction owns the port.
        prov.clear_port_mappings(device)
        mapping = PortMapping(
            local_port=tunnel_port,
            remote_port=tunnel_port,
            direction="forward" if use_forward else "reverse",
        )
        if use_forward:
            prov.forward_ports(device, [mapping])
        else:
            prov.reverse_ports(device, [mapping])
        apk = settings.apk_path
        if settings.install_apk and apk:
            prov.install(device, Path(apk), package=settings.app_package)
        if settings.app_package:
            # Cold start so Wire Awake runs after the tunnel is correct (a prior
            # reverse session may have left the process without a listener).
            if use_forward:
                try:
                    prov.stop(device, package=settings.app_package)
                except Exception:  # pragma: no cover - best-effort
                    pass
            prov.launch(
                device,
                package=settings.app_package,
                activity=settings.app_activity,
            )
            if use_forward:
                wait_for_wire_ready(
                    adb=client,
                    device=device,
                    host=settings.target_host or "127.0.0.1",
                    port=tunnel_port,
                    timeout_s=float(settings.wait.deadline or 45.0),
                    interval_s=float(settings.wait.interval or 0.5),
                )
    except DeviceError:
        prov.release(device)
        raise

    return {"provider": prov, "device": device}


def teardown_android_session(
    bundle: dict[str, Any] | None,
    *,
    app_package: str | None = None,
) -> None:
    if not bundle:
        return
    provider: LocalAdbProvider = bundle["provider"]
    device: Device = bundle["device"]
    try:
        if app_package:
            provider.stop(device, package=app_package)
    except Exception:  # pragma: no cover - teardown must not raise
        pass
    try:
        provider.release(device)
    except Exception:  # pragma: no cover
        pass
