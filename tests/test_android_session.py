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
    """Legacy / AltTester path: adb reverse (device→host)."""
    apk = tmp_path / "app.apk"
    apk.write_bytes(b"PK")
    fake = FakeAdb(
        responses={
            ("devices", "-l"): _DEVICES,
            ("logcat", "-c"): "",
            ("forward", "--remove-all"): "",
            ("reverse", "--remove-all"): "",
            ("reverse", "tcp:13000", "tcp:13000"): "",
            ("reverse", "--list"): "UsbFfs tcp:13000 tcp:13000\n",
            ("install", "-r", str(apk)): "Success\n",
            ("shell", "am", "start", "-n", "com.ex/.Main"): "",
            ("shell", "am", "force-stop", "com.ex"): "",
        }
    )
    settings = Settings(
        project_root=tmp_path,
        store_dir=tmp_path / ".questline",
        device="adb",
        driver="alttester",
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


def test_setup_android_session_wire_uses_forward(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """QuestlineWire listens on device — session must use adb forward, not reverse."""
    apk = tmp_path / "app.apk"
    apk.write_bytes(b"PK")
    fake = FakeAdb(
        responses={
            ("devices", "-l"): _DEVICES,
            ("logcat", "-c"): "",
            ("forward", "--remove-all"): "",
            ("reverse", "--remove-all"): "",
            ("forward", "tcp:13000", "tcp:13000"): "",
            ("forward", "--list"): "emulator-5554 tcp:13000 tcp:13000\n",
            ("install", "-r", str(apk)): "Success\n",
            ("shell", "am", "force-stop", "com.ex"): "",
            ("shell", "am", "start", "-n", "com.ex/.Main"): "",
        },
        default="",
    )
    monkeypatch.setattr(
        "questline.devices.session.wait_for_wire_ready",
        lambda **_kwargs: None,
    )
    settings = Settings(
        project_root=tmp_path,
        store_dir=tmp_path / ".questline",
        device="adb",
        driver="questline",
        target_platform="android",
        target_port=13000,
        apk_path=str(apk),
        app_package="com.ex",
        app_activity=".Main",
        install_apk=True,
    )
    provider = LocalAdbProvider(adb=fake, lock_dir=tmp_path / "locks")
    bundle = setup_android_session(settings, adb=fake, provider=provider, start_emulator=False)
    assert bundle["device"].id == "emulator-5554"
    argv = [c[1] for c in fake.calls]
    assert ("forward", "tcp:13000", "tcp:13000") in argv
    assert not any(a[:1] == ("reverse",) and len(a) >= 2 and a[1].startswith("tcp:") for a in argv)
    teardown_android_session(bundle, app_package="com.ex")


def test_wait_for_wire_ready_succeeds_on_hello() -> None:
    import json
    import socket
    import threading

    from questline.devices.port import Device
    from questline.devices.session import wait_for_wire_ready

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", 0))
    port = srv.getsockname()[1]
    srv.listen(1)
    stop = threading.Event()

    def _serve() -> None:
        srv.settimeout(0.2)
        while not stop.is_set():
            try:
                conn, _ = srv.accept()
            except TimeoutError:
                continue
            except OSError:
                break
            with conn:
                data = b""
                while b"\n" not in data:
                    chunk = conn.recv(4096)
                    if not chunk:
                        break
                    data += chunk
                reply = json.dumps({"v": 1, "id": "ready", "ok": True, "result": {}}) + "\n"
                try:
                    conn.sendall(reply.encode("utf-8"))
                except OSError:
                    pass

    thread = threading.Thread(target=_serve, daemon=True)
    thread.start()
    try:
        wait_for_wire_ready(
            adb=FakeAdb(default=""),
            device=Device(id="emu", platform="android", caps={}),
            host="127.0.0.1",
            port=port,
            timeout_s=3.0,
            interval_s=0.1,
        )
    finally:
        stop.set()
        srv.close()
        thread.join(timeout=2.0)


def test_setup_android_session_reverse_fail_releases(tmp_path: Path) -> None:
    fake = FakeAdb(
        responses={
            ("devices", "-l"): _DEVICES,
            ("logcat", "-c"): "",
            ("forward", "--remove-all"): "",
            ("reverse", "--remove-all"): "",
            ("reverse", "tcp:13000", "tcp:13000"): "",
            ("reverse", "--list"): "",
        }
    )
    settings = Settings(
        project_root=tmp_path,
        store_dir=tmp_path / ".questline",
        device="adb",
        driver="alttester",
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
