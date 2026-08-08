"""Unit tests for LocalAdbProvider with FakeAdb (no real device)."""

from __future__ import annotations

from pathlib import Path

import pytest

from questline.core.errors import DeviceError, Verdict, classify
from questline.devices.adb.client import AdbResult, FakeAdb
from questline.devices.adb.lock import DeviceLock
from questline.devices.adb.parse import (
    online_devices,
    parse_adb_devices_l,
    parse_reverse_list,
    parse_version_name,
)
from questline.devices.adb.provider import LocalAdbProvider
from questline.devices.port import DeviceSpec, PortMapping

_DEVICES_L = """\
List of devices attached
emulator-5554          device product:sdk_gphone model:sdk_gphone64_x86_64 \
device:emu64xa transport_id:1
"""


def _provider(tmp_path: Path, fake: FakeAdb) -> LocalAdbProvider:
    return LocalAdbProvider(adb=fake, lock_dir=tmp_path / "locks")


def test_parse_adb_devices_l() -> None:
    rows = parse_adb_devices_l(_DEVICES_L)
    assert len(rows) == 1
    assert rows[0].serial == "emulator-5554"
    assert rows[0].state == "device"
    assert rows[0].model == "sdk_gphone64_x86_64"
    devices = online_devices(_DEVICES_L)
    assert devices[0].id == "emulator-5554"


def test_parse_reverse_list() -> None:
    assert parse_reverse_list("UsbFfs tcp:13000 tcp:13000\n") == [(13000, 13000)]
    assert parse_reverse_list("") == []


def test_parse_version_name() -> None:
    assert parse_version_name("versionName=1.2.3\nversionCode=4") == "1.2.3"
    assert parse_version_name("nothing") is None


def test_acquire_release_and_list(tmp_path: Path) -> None:
    fake = FakeAdb(
        responses={
            ("devices", "-l"): _DEVICES_L,
            ("logcat", "-c"): "",
        }
    )
    p = _provider(tmp_path, fake)
    devices = p.list_devices()
    assert len(devices) == 1
    d = p.acquire(DeviceSpec(platform="android"))
    assert d.id == "emulator-5554"
    p.release(d)


def test_acquire_no_device(tmp_path: Path) -> None:
    fake = FakeAdb(responses={("devices", "-l"): "List of devices attached\n"})
    p = _provider(tmp_path, fake)
    with pytest.raises(DeviceError, match="No online Android"):
        p.acquire(DeviceSpec(platform="android"))


def test_acquire_pin_missing(tmp_path: Path) -> None:
    fake = FakeAdb(responses={("devices", "-l"): _DEVICES_L})
    p = _provider(tmp_path, fake)
    with pytest.raises(DeviceError, match="device_serial"):
        p.acquire(DeviceSpec(platform="android", id="phone-xyz"))


def test_device_lock_blocks_second(tmp_path: Path) -> None:
    fake = FakeAdb(
        responses={
            ("devices", "-l"): _DEVICES_L,
            ("logcat", "-c"): "",
            ("forward", "--remove-all"): "",
            ("reverse", "--remove-all"): "",
        }
    )
    a = _provider(tmp_path, fake)
    b = _provider(tmp_path, fake)
    d = a.acquire(DeviceSpec(platform="android", id="emulator-5554"))
    with pytest.raises(DeviceError, match="locked"):
        b.acquire(DeviceSpec(platform="android", id="emulator-5554"))
    a.release(d)
    d2 = b.acquire(DeviceSpec(platform="android", id="emulator-5554"))
    b.release(d2)


def test_reverse_post_verification_empty_raises(tmp_path: Path) -> None:
    """Design rule: silent reverse failure (empty --list) must raise."""
    fake = FakeAdb(
        responses={
            ("devices", "-l"): _DEVICES_L,
            ("logcat", "-c"): "",
            ("reverse", "tcp:13000", "tcp:13000"): "",
            ("reverse", "--list"): "",  # empty → must raise
            ("forward", "--remove-all"): "",
            ("reverse", "--remove-all"): "",
        }
    )
    p = _provider(tmp_path, fake)
    d = p.acquire(DeviceSpec(platform="android"))
    with pytest.raises(DeviceError, match="reverse post-verification"):
        p.reverse_ports(
            d,
            [PortMapping(local_port=13000, remote_port=13000, direction="reverse")],
        )
    p.release(d)


def test_reverse_post_verification_ok(tmp_path: Path) -> None:
    fake = FakeAdb(
        responses={
            ("devices", "-l"): _DEVICES_L,
            ("logcat", "-c"): "",
            ("reverse", "tcp:13000", "tcp:13000"): "",
            ("reverse", "--list"): "UsbFfs tcp:13000 tcp:13000\n",
            ("forward", "--remove-all"): "",
            ("reverse", "--remove-all"): "",
        }
    )
    p = _provider(tmp_path, fake)
    d = p.acquire(DeviceSpec(platform="android"))
    p.reverse_ports(
        d,
        [PortMapping(local_port=13000, remote_port=13000, direction="reverse")],
    )
    p.release(d)


def test_forward_post_verification_ok(tmp_path: Path) -> None:
    fake = FakeAdb(
        responses={
            ("devices", "-l"): _DEVICES_L,
            ("logcat", "-c"): "",
            ("forward", "tcp:13000", "tcp:13000"): "",
            ("forward", "--list"): "emulator-5554 tcp:13000 tcp:13000\n",
            ("forward", "--remove-all"): "",
            ("reverse", "--remove-all"): "",
        }
    )
    p = _provider(tmp_path, fake)
    d = p.acquire(DeviceSpec(platform="android"))
    p.forward_ports(
        d,
        [PortMapping(local_port=13000, remote_port=13000, direction="forward")],
    )
    p.release(d)


def test_install_launch_stop_logs_shell(tmp_path: Path) -> None:
    apk = tmp_path / "app.apk"
    apk.write_bytes(b"PK\x03\x04fake")
    fake = FakeAdb(
        responses={
            ("devices", "-l"): _DEVICES_L,
            ("logcat", "-c"): "",
            ("install", "-r", str(apk)): "Success\n",
            ("shell", "am", "start", "-n", "com.questline.smoke/.MainActivity"): "",
            ("shell", "am", "force-stop", "com.questline.smoke"): "",
            ("shell", "echo questline"): "questline\n",
            ("logcat", "-d"): "I/Questline: hello\n",
            ("forward", "--remove-all"): "",
            ("reverse", "--remove-all"): "",
        }
    )
    p = _provider(tmp_path, fake)
    d = p.acquire(DeviceSpec(platform="android"))
    p.install(d, apk, package="com.questline.smoke")
    p.launch(d, package="com.questline.smoke", activity=".MainActivity")
    assert "questline" in p.shell(d, "echo questline")
    assert "Questline" in p.logs(d)
    p.stop(d, package="com.questline.smoke")
    p.release(d)


def test_install_missing_apk(tmp_path: Path) -> None:
    fake = FakeAdb(
        responses={
            ("devices", "-l"): _DEVICES_L,
            ("logcat", "-c"): "",
            ("forward", "--remove-all"): "",
            ("reverse", "--remove-all"): "",
        }
    )
    p = _provider(tmp_path, fake)
    d = p.acquire(DeviceSpec(platform="android"))
    with pytest.raises(DeviceError, match="APK not found"):
        p.install(d, tmp_path / "missing.apk")
    p.release(d)


def test_install_version_mismatch(tmp_path: Path) -> None:
    apk = tmp_path / "app.apk"
    apk.write_bytes(b"PK")
    fake = FakeAdb(
        responses={
            ("devices", "-l"): _DEVICES_L,
            ("logcat", "-c"): "",
            ("install", "-r", str(apk)): "Success\n",
            ("shell", "dumpsys", "package", "com.x"): "versionName=9.9.9\n",
            ("forward", "--remove-all"): "",
            ("reverse", "--remove-all"): "",
        }
    )
    p = _provider(tmp_path, fake)
    d = p.acquire(
        DeviceSpec(platform="android", caps={"expected_version": "1.0.0"})
    )
    assert d.caps.get("expected_version") == "1.0.0"
    with pytest.raises(DeviceError, match="does not match expected"):
        p.install(d, apk, package="com.x")
    p.release(d)


def test_device_error_is_infra() -> None:
    assert classify(DeviceError("adb failed")) is Verdict.INFRA


def test_lock_stale_pid(tmp_path: Path) -> None:
    lock = DeviceLock(tmp_path / "locks")
    path = lock.path_for("serial-a")
    path.write_text("pid=999999991\nowner=dead\n", encoding="utf-8")
    # Force stale via dead pid detection
    lock.acquire("serial-a", stale_s=0.0)
    lock.release("serial-a")


def test_fake_adb_check_raises() -> None:
    fake = FakeAdb(
        responses={
            ("boom",): AdbResult(args=("boom",), returncode=1, stdout="", stderr="nope"),
        }
    )
    with pytest.raises(DeviceError, match="adb failed"):
        fake.run(["boom"], check=True)
