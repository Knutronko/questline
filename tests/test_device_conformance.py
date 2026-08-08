"""DevicePort conformance against LocalAdbProvider + FakeAdb."""

from __future__ import annotations

from pathlib import Path

import pytest

from questline.devices import conformance as conf
from questline.devices.adb.client import FakeAdb
from questline.devices.adb.provider import LocalAdbProvider

_DEVICES_L = """\
List of devices attached
emulator-5554          device product:sdk model:emu device:emu transport_id:1
"""


@pytest.fixture
def provider_factory(tmp_path: Path):
    apk_holder = {"path": tmp_path / "app.apk"}
    apk_holder["path"].write_bytes(b"PK\x03\x04")

    def factory() -> LocalAdbProvider:
        fake = FakeAdb(
            responses={
                ("devices", "-l"): _DEVICES_L,
                ("logcat", "-c"): "",
                ("logcat", "-d"): "I/tag: line\n",
                ("reverse", "tcp:13000", "tcp:13000"): "",
                ("reverse", "--list"): "UsbFfs tcp:13000 tcp:13000\n",
                ("forward", "tcp:13000", "tcp:13000"): "",
                ("forward", "--list"): "emulator-5554 tcp:13000 tcp:13000\n",
                ("forward", "--remove-all"): "",
                ("reverse", "--remove-all"): "",
                ("shell", "echo questline"): "questline\n",
                ("install", "-r", str(apk_holder["path"])): "Success\n",
                ("shell", "am", "start", "-n", "com.questline.smoke/.MainActivity"): "",
                ("shell", "am", "force-stop", "com.questline.smoke"): "",
            }
        )
        return LocalAdbProvider(adb=fake, lock_dir=tmp_path / "locks")

    factory.apk = apk_holder["path"]  # type: ignore[attr-defined]
    return factory


@pytest.mark.parametrize("case", conf.CONFORMANCE_CASES, ids=lambda c: c.__name__)
def test_device_conformance(case, provider_factory) -> None:
    case(provider_factory)


def test_device_conformance_install(provider_factory) -> None:
    conf.case_install_launch_stop(provider_factory, provider_factory.apk)
