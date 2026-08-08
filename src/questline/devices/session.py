"""Session helpers to acquire/prepare an Android device for a pytest run."""

from __future__ import annotations

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


def setup_android_session(
    settings: Settings,
    *,
    adb: AdbClient | None = None,
    provider: LocalAdbProvider | None = None,
    start_emulator: bool = True,
) -> dict[str, Any]:
    """Acquire device, reverse ports, optional install/launch.

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

    reverse_port = settings.reverse_port or settings.target_port
    try:
        prov.reverse_ports(
            device,
            [
                PortMapping(
                    local_port=reverse_port,
                    remote_port=reverse_port,
                    direction="reverse",
                )
            ],
        )
        apk = settings.apk_path
        if settings.install_apk and apk:
            prov.install(device, Path(apk), package=settings.app_package)
        if settings.app_package:
            prov.launch(
                device,
                package=settings.app_package,
                activity=settings.app_activity,
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
