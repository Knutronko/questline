"""DeviceProviderPort conformance cases (fake adb / any conformant provider).

Provide a factory ``() -> DeviceProviderPort`` that returns a fresh provider with at
least one acquire-able android device. LocalAdbProvider + FakeAdb is the reference.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from questline.core.errors import DeviceError, Verdict, classify
from questline.devices.port import Device, DeviceProviderPort, DeviceSpec, PortMapping

ProviderFactory = Callable[[], DeviceProviderPort]


def case_list_and_acquire_release(factory: ProviderFactory) -> None:
    p = factory()
    devices = p.list_devices()
    assert devices, "conformance fixture must expose ≥1 online device"
    spec = DeviceSpec(platform="android", id=devices[0].id)
    d = p.acquire(spec)
    assert isinstance(d, Device)
    assert d.id == devices[0].id
    assert d.platform == "android"
    p.release(d)


def case_acquire_missing_serial(factory: ProviderFactory) -> None:
    p = factory()
    with pytest.raises(DeviceError):
        p.acquire(DeviceSpec(platform="android", id="no-such-serial-xyz"))
    assert classify(DeviceError("x")) is Verdict.INFRA


def case_double_acquire_lock(factory: ProviderFactory) -> None:
    """Second acquire of the same serial must fail while the first holds the lock."""
    a = factory()
    devices = a.list_devices()
    assert devices
    serial = devices[0].id
    d = a.acquire(DeviceSpec(platform="android", id=serial))
    b = factory()
    with pytest.raises(DeviceError, match="locked"):
        b.acquire(DeviceSpec(platform="android", id=serial))
    a.release(d)
    # After release, another provider can acquire.
    d2 = b.acquire(DeviceSpec(platform="android", id=serial))
    b.release(d2)


def case_install_launch_stop(factory: ProviderFactory, apk: Path) -> None:
    p = factory()
    devices = p.list_devices()
    d = p.acquire(DeviceSpec(platform="android", id=devices[0].id))
    try:
        p.install(d, apk, package="com.questline.smoke")
        p.launch(d, package="com.questline.smoke", activity=".MainActivity")
        p.stop(d, package="com.questline.smoke")
    finally:
        p.release(d)


def case_reverse_ports_verified(factory: ProviderFactory) -> None:
    p = factory()
    devices = p.list_devices()
    d = p.acquire(DeviceSpec(platform="android", id=devices[0].id))
    try:
        p.reverse_ports(
            d,
            [PortMapping(local_port=13000, remote_port=13000, direction="reverse")],
        )
        p.clear_port_mappings(d)
    finally:
        p.release(d)


def case_forward_ports_verified(factory: ProviderFactory) -> None:
    p = factory()
    devices = p.list_devices()
    d = p.acquire(DeviceSpec(platform="android", id=devices[0].id))
    try:
        p.forward_ports(
            d,
            [PortMapping(local_port=13000, remote_port=13000, direction="forward")],
        )
        p.clear_port_mappings(d)
    finally:
        p.release(d)


def case_logs_and_shell(factory: ProviderFactory) -> None:
    p = factory()
    devices = p.list_devices()
    d = p.acquire(DeviceSpec(platform="android", id=devices[0].id))
    try:
        out = p.shell(d, "echo questline")
        assert "questline" in out
        logs = p.logs(d)
        assert isinstance(logs, str)
    finally:
        p.release(d)


CONFORMANCE_CASES = (
    case_list_and_acquire_release,
    case_acquire_missing_serial,
    case_double_acquire_lock,
    case_reverse_ports_verified,
    case_forward_ports_verified,
    case_logs_and_shell,
)
