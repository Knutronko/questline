"""Extra coverage for adb helpers and plugin failure artifacts."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from questline.authoring import plugin as pl
from questline.core.errors import DeviceError
from questline.core.events import EventBus
from questline.core.store import RunStore
from questline.devices.adb.client import FakeAdb
from questline.devices.adb.emulator import find_emulator_binary
from questline.devices.adb.lock import DeviceLock
from questline.devices.adb.logcat import LogcatBuffer, dump_logcat
from questline.devices.adb.parse import parse_adb_devices_l
from questline.devices.adb.provider import LocalAdbProvider
from questline.devices.port import Device, DeviceSpec, PortMapping
from questline.drivers.handle import DriverHandle
from questline.drivers.mock import MockDriver


def test_parse_skips_junk_lines() -> None:
    text = "List of devices attached\n* daemon not running\nbogus\n"
    assert parse_adb_devices_l(text) == []


def test_parse_offline_and_unauthorized() -> None:
    text = (
        "List of devices attached\n"
        "ABC offline\n"
        "DEF unauthorized\n"
        "GHI device model:Pixel\n"
    )
    rows = parse_adb_devices_l(text)
    assert [r.serial for r in rows] == ["ABC", "DEF", "GHI"]
    from questline.devices.adb.parse import online_devices

    assert [d.id for d in online_devices(text)] == ["GHI"]


def test_logcat_buffer_clear_and_dump(tmp_path: Path) -> None:
    fake = FakeAdb(
        responses={
            ("logcat", "-c"): "",
            ("logcat", "-d"): "line-a\nline-b\n",
        }
    )
    buf = LogcatBuffer(maxlen=10)
    buf.extend("old\n")
    text = dump_logcat(fake, serial="emu", buffer=buf, clear=True)
    assert "line-a" in text
    assert "old" not in text


def test_provider_wrong_platform(tmp_path: Path) -> None:
    p = LocalAdbProvider(adb=FakeAdb(), lock_dir=tmp_path / "locks")
    with pytest.raises(DeviceError, match="platform='android'"):
        p.acquire(DeviceSpec(platform="ios"))


def test_provider_list_devices_adb_failure(tmp_path: Path) -> None:
    from questline.devices.adb.client import AdbResult

    fake = FakeAdb(
        responses={
            ("devices", "-l"): AdbResult(
                args=("devices", "-l"),
                returncode=1,
                stdout="",
                stderr="adb server error",
            ),
        }
    )
    p = LocalAdbProvider(adb=fake, lock_dir=tmp_path / "locks")
    with pytest.raises(DeviceError, match="adb devices failed"):
        p.list_devices()


def test_provider_api_level_gate(tmp_path: Path) -> None:
    devices = (
        "List of devices attached\n"
        "serial-1 device product:p model:m device:d\n"
    )
    fake = FakeAdb(
        responses={
            ("devices", "-l"): devices,
            ("shell", "getprop", "ro.build.version.sdk"): "28\n",
            ("logcat", "-c"): "",
            ("forward", "--remove-all"): "",
            ("reverse", "--remove-all"): "",
        }
    )
    p = LocalAdbProvider(adb=fake, lock_dir=tmp_path / "locks")
    with pytest.raises(DeviceError, match="api_level"):
        p.acquire(DeviceSpec(platform="android", api_level=30))
    d = p.acquire(DeviceSpec(platform="android", api_level=28))
    assert d.api_level == 28
    p.release(d)


def test_provider_launch_monkey_and_forward_miss(tmp_path: Path) -> None:
    devices = (
        "List of devices attached\n"
        "serial-1 device product:p model:m device:d\n"
    )
    fake = FakeAdb(
        responses={
            ("devices", "-l"): devices,
            ("logcat", "-c"): "",
            (
                "shell",
                "monkey",
                "-p",
                "com.x",
                "-c",
                "android.intent.category.LAUNCHER",
                "1",
            ): "",
            ("forward", "tcp:1", "tcp:2"): "",
            ("forward", "--list"): "",
            ("forward", "--remove-all"): "",
            ("reverse", "--remove-all"): "",
        }
    )
    p = LocalAdbProvider(adb=fake, lock_dir=tmp_path / "locks")
    d = p.acquire(DeviceSpec(platform="android"))
    p.launch(d, package="com.x")
    with pytest.raises(DeviceError, match="forward post-verification"):
        p.forward_ports(d, [PortMapping(local_port=1, remote_port=2, direction="forward")])
    p.release(d)


def test_provider_reverse_mismatch_not_empty(tmp_path: Path) -> None:
    devices = (
        "List of devices attached\n"
        "serial-1 device product:p model:m device:d\n"
    )
    fake = FakeAdb(
        responses={
            ("devices", "-l"): devices,
            ("logcat", "-c"): "",
            ("reverse", "tcp:13000", "tcp:13000"): "",
            ("reverse", "--list"): "UsbFfs tcp:9999 tcp:9999\n",
            ("forward", "--remove-all"): "",
            ("reverse", "--remove-all"): "",
        }
    )
    p = LocalAdbProvider(adb=fake, lock_dir=tmp_path / "locks")
    d = p.acquire(DeviceSpec(platform="android"))
    with pytest.raises(DeviceError, match="expected"):
        p.reverse_ports(
            d,
            [PortMapping(local_port=13000, remote_port=13000, direction="reverse")],
        )
    p.release(d)


def test_lock_release_all_and_reacquire(tmp_path: Path) -> None:
    lock = DeviceLock(tmp_path / "locks")
    lock.acquire("a")
    lock.acquire("a")  # idempotent
    lock.release_all()
    lock.acquire("a")
    lock.release("a")


def test_lock_ensure_available_does_not_hold(tmp_path: Path) -> None:
    lock = DeviceLock(tmp_path / "locks")
    lock.ensure_available("phone")
    assert not lock.path_for("phone").exists()
    lock.acquire("phone", owner="holder")
    with pytest.raises(DeviceError, match="locked"):
        DeviceLock(tmp_path / "locks").ensure_available("phone")
    lock.release("phone")
    DeviceLock(tmp_path / "locks").ensure_available("phone")


def test_lock_ensure_available_clears_dead_pid(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lock = DeviceLock(tmp_path / "locks")
    path = lock.path_for("dead")
    path.write_text("pid=99999999\nowner=gone\nacquired_at=1.0\n", encoding="utf-8")
    monkeypatch.setattr("questline.devices.adb.lock._pid_alive", lambda _pid: False)
    lock.ensure_available("dead")
    assert not path.exists()


def test_find_emulator_from_android_home(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    emu_dir = tmp_path / "emulator"
    emu_dir.mkdir()
    binary = emu_dir / ("emulator.exe" if __import__("os").name == "nt" else "emulator")
    binary.write_text("", encoding="utf-8")
    monkeypatch.setenv("ANDROID_HOME", str(tmp_path))
    monkeypatch.delenv("ANDROID_SDK_ROOT", raising=False)
    assert find_emulator_binary() == str(binary)


def test_find_emulator_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANDROID_HOME", raising=False)
    monkeypatch.delenv("ANDROID_SDK_ROOT", raising=False)
    monkeypatch.setattr("questline.devices.adb.emulator.shutil.which", lambda _: None)
    with pytest.raises(DeviceError, match="emulator binary not found"):
        find_emulator_binary()


def test_save_failure_artifacts(tmp_path: Path) -> None:
    bus = EventBus()
    store = RunStore(tmp_path / "store.db", artifacts_dir=tmp_path / "arts")
    store.attach(bus)
    driver = MockDriver()
    from questline.drivers.port import ConnectionTarget

    driver.connect(ConnectionTarget())
    handle = DriverHandle(driver)

    fake = FakeAdb(responses={("logcat", "-d"): "I/fail: boom\n", ("logcat", "-c"): ""})
    provider = LocalAdbProvider(adb=fake, lock_dir=tmp_path / "locks")
    device = Device(id="serial-1", platform="android")
    provider._logcats[device.id] = LogcatBuffer()  # noqa: SLF001

    tags: dict[str, str] = {}
    pl._save_failure_artifacts(
        store=store,
        handle=handle,
        device_bundle={"provider": provider, "device": device},
        run_id="run-1",
        test_id="tests/test_x.py::test_y",
        tags=tags,
    )
    assert "artifact_screenshot" in tags
    assert "artifact_logcat" in tags
    assert Path(tags["artifact_screenshot"]).is_file()
    assert Path(tags["artifact_logcat"]).is_file()
    store.close()


def test_save_failure_artifacts_errors_tolerated() -> None:
    tags: dict[str, str] = {}
    handle = MagicMock()
    handle.screenshot.side_effect = RuntimeError("no png")
    bundle = {
        "provider": MagicMock(**{"logs.side_effect": RuntimeError("no log")}),
        "device": SimpleNamespace(id="x"),
    }
    store = MagicMock()
    pl._save_failure_artifacts(
        store=store,
        handle=handle,
        device_bundle=bundle,
        run_id="r",
        test_id="t",
        tags=tags,
    )
    assert "artifact_screenshot_error" in tags
    assert "artifact_logcat_error" in tags
