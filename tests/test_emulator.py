"""Emulator helper unit tests (no real AVD)."""

from __future__ import annotations

from typing import Any

import pytest

from questline.core.errors import DeviceError
from questline.devices.adb.client import FakeAdb
from questline.devices.adb.emulator import ensure_emulator, wait_for_boot


def test_wait_for_boot_success() -> None:
    fake = FakeAdb(
        responses={
            ("devices", "-l"): (
                "List of devices attached\n"
                "emulator-5554          device product:sdk model:emu device:emu\n"
            ),
            ("shell", "getprop", "sys.boot_completed"): "1\n",
        }
    )
    serial = wait_for_boot(fake, timeout_s=5.0, poll_s=0.01)
    assert serial == "emulator-5554"


def test_wait_for_boot_timeout() -> None:
    fake = FakeAdb(
        responses={
            ("devices", "-l"): "List of devices attached\n",
        }
    )
    with pytest.raises(DeviceError, match="did not finish booting"):
        wait_for_boot(fake, timeout_s=0.05, poll_s=0.01)


def test_ensure_emulator_uses_online_device() -> None:
    fake = FakeAdb(
        responses={
            ("devices", "-l"): (
                "List of devices attached\n"
                "emulator-5554          device product:sdk model:emu device:emu\n"
            ),
            ("shell", "getprop", "sys.boot_completed"): "1\n",
        }
    )
    serial = ensure_emulator("Pixel_6_API_34", fake, start_if_needed=False)
    assert serial == "emulator-5554"


def test_ensure_emulator_start_if_needed_false_empty() -> None:
    fake = FakeAdb(responses={("devices", "-l"): "List of devices attached\n"})
    with pytest.raises(DeviceError, match="no online"):
        ensure_emulator("Pixel_6_API_34", fake, start_if_needed=False)


def test_start_avd_invokes_popen(monkeypatch: pytest.MonkeyPatch) -> None:
    from questline.devices.adb import emulator as em

    calls: list[list[str]] = []

    class FakePopen:
        def __init__(self, cmd: list[str], **kwargs: Any) -> None:
            calls.append(cmd)
            self.kwargs = kwargs

    monkeypatch.setattr(em, "find_emulator_binary", lambda path=None: "emulator")
    proc = em.start_avd("MyAVD", popen=FakePopen)  # type: ignore[arg-type]
    assert isinstance(proc, FakePopen)
    assert calls[0][:3] == ["emulator", "-avd", "MyAVD"]
