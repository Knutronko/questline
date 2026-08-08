"""Tests for android session setup helpers (plugin coverage path)."""

from __future__ import annotations

from pathlib import Path

import pytest

from questline.core.config import Settings
from questline.core.errors import DeviceError
from questline.devices.adb.client import FakeAdb
from questline.devices.adb.provider import LocalAdbProvider
from questline.devices.port import DeviceSpec
from questline.devices.session import (
    needs_adb_device,
    setup_android_session,
    teardown_android_session,
)

_DEVICES = (
    "List of devices attached\n"
    "emulator-5554          device product:sdk model:emu device:emu\n"
)


def test_needs_adb_device() -> None:
    assert needs_adb_device(Settings(device="adb")) is True
    assert needs_adb_device(Settings(device="android_local")) is True
    assert needs_adb_device(Settings(target_platform="android")) is True
    assert needs_adb_device(Settings(device="local", target_platform="editor")) is False


def test_setup_android_session_full(tmp_path: Path) -> None:
    apk = tmp_path / "app.apk"
    apk.write_bytes(b"PK")
    fake = FakeAdb(
        responses={
            ("devices", "-l"): _DEVICES,
            ("logcat", "-c"): "",
            ("reverse", "tcp:13000", "tcp:13000"): "",
            ("reverse", "--list"): "UsbFfs tcp:13000 tcp:13000\n",
            ("install", "-r", str(apk)): "Success\n",
            ("shell", "am", "start", "-n", "com.ex/.Main"): "",
            ("shell", "am", "force-stop", "com.ex"): "",
            ("forward", "--remove-all"): "",
            ("reverse", "--remove-all"): "",
        }
    )
    settings = Settings(
        project_root=tmp_path,
        store_dir=tmp_path / ".questline",
        device="adb",
        target_platform="android",
        target_port=13000,
        apk_path=str(apk),
        app_package="com.ex",
        app_activity=".Main",
        install_apk=True,
        expected_app_version=None,
    )
    provider = LocalAdbProvider(adb=fake, lock_dir=tmp_path / "locks")
    bundle = setup_android_session(settings, adb=fake, provider=provider, start_emulator=False)
    assert bundle["device"].id == "emulator-5554"
    teardown_android_session(bundle, app_package="com.ex")


def test_setup_android_session_reverse_fail_releases(tmp_path: Path) -> None:
    fake = FakeAdb(
        responses={
            ("devices", "-l"): _DEVICES,
            ("logcat", "-c"): "",
            ("reverse", "tcp:13000", "tcp:13000"): "",
            ("reverse", "--list"): "",
            ("forward", "--remove-all"): "",
            ("reverse", "--remove-all"): "",
        }
    )
    settings = Settings(
        project_root=tmp_path,
        store_dir=tmp_path / ".questline",
        device="adb",
        target_platform="android",
        target_port=13000,
    )
    provider = LocalAdbProvider(adb=fake, lock_dir=tmp_path / "locks")
    with pytest.raises(DeviceError, match="reverse"):
        setup_android_session(settings, adb=fake, provider=provider, start_emulator=False)
    # Lock released — re-acquire works.
    d = provider.acquire(DeviceSpec(platform="android"))
    provider.release(d)


def test_teardown_none_is_noop() -> None:
    teardown_android_session(None)
