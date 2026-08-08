"""LocalAdbProvider — DeviceProviderPort over adb (real or fake)."""

from __future__ import annotations

from pathlib import Path

from questline.core.errors import DeviceError
from questline.devices.adb.client import AdbClient, RealAdb
from questline.devices.adb.lock import DeviceLock
from questline.devices.adb.logcat import LogcatBuffer
from questline.devices.adb.parse import (
    online_devices,
    parse_forward_list,
    parse_reverse_list,
    parse_version_name,
)
from questline.devices.port import Device, DeviceSpec, PortMapping


class LocalAdbProvider:
    """Acquire/lock local Android devices via adb."""

    def __init__(
        self,
        *,
        adb: AdbClient | None = None,
        lock_dir: Path | None = None,
        logcat_maxlen: int = 5000,
    ) -> None:
        self._adb = adb or RealAdb()
        self._lock = DeviceLock(lock_dir or Path.cwd() / ".questline" / "device-locks")
        self._logcats: dict[str, LogcatBuffer] = {}
        self._logcat_maxlen = logcat_maxlen
        self._held: set[str] = set()

    @property
    def adb(self) -> AdbClient:
        return self._adb

    def list_devices(self) -> list[Device]:
        result = self._adb.run(["devices", "-l"], check=False)
        if not result.ok:
            detail = (result.stderr or result.stdout).strip()
            raise DeviceError(
                f"adb devices failed: {detail or f'exit {result.returncode}'}. "
                "Is the adb server running? See docs/android.md."
            )
        return online_devices(result.stdout)

    def acquire(self, spec: DeviceSpec) -> Device:
        if spec.platform.lower() not in {"android", "adb"}:
            raise DeviceError(
                f"LocalAdbProvider only supports platform='android' (got {spec.platform!r})"
            )
        devices = self.list_devices()
        if not devices:
            raise DeviceError(
                "No online Android device or emulator found (`adb devices` empty). "
                "Enable USB debugging, authorize this PC, start an emulator, or set "
                "emulator_avd in questline.toml. See docs/android.md."
            )
        chosen: Device | None = None
        if spec.id:
            for d in devices:
                if d.id == spec.id:
                    chosen = d
                    break
            if chosen is None:
                available = ", ".join(d.id for d in devices)
                raise DeviceError(
                    f"Configured device_serial={spec.id!r} is not online. "
                    f"Online devices: {available or '(none)'}. "
                    "Check USB / emulator, or clear device_serial to auto-pick."
                )
        else:
            chosen = devices[0]

        if spec.api_level is not None:
            level = self._read_api_level(chosen.id)
            if level is not None and level < spec.api_level:
                raise DeviceError(
                    f"device {chosen.id} api_level={level} < required {spec.api_level}"
                )
            if level is not None:
                chosen = Device(
                    id=chosen.id,
                    platform=chosen.platform,
                    api_level=level,
                    caps=dict(chosen.caps),
                )

        self._lock.acquire(chosen.id, owner="questline")
        self._held.add(chosen.id)
        self._logcats[chosen.id] = LogcatBuffer(maxlen=self._logcat_maxlen)
        # Clear stale logcat so failure dumps are session-scoped.
        self._adb.run(["logcat", "-c"], serial=chosen.id, check=False)
        merged_caps = {**chosen.caps, **spec.caps}
        return Device(
            id=chosen.id,
            platform=chosen.platform,
            api_level=chosen.api_level,
            caps=merged_caps,
        )

    def release(self, device: Device) -> None:
        serial = device.id
        try:
            self.clear_port_mappings(device)
        except DeviceError:
            # Still release the lock — design rule: never leave a silent stuck lock
            # without attempting cleanup; surface via re-raise only if lock fails.
            pass
        self._logcats.pop(serial, None)
        self._held.discard(serial)
        self._lock.release(serial)

    def install(self, device: Device, artifact: Path, *, package: str | None = None) -> None:
        path = Path(artifact)
        if not path.is_file():
            raise DeviceError(f"APK not found: {path}")
        result = self._adb.run(["install", "-r", str(path)], serial=device.id, check=False)
        combined = f"{result.stdout}\n{result.stderr}"
        lowered = combined.lower()
        if "success" not in lowered:
            detail = combined.strip() or f"exit {result.returncode}"
            raise DeviceError(f"adb install failed for {path.name}: {detail}")
        if package:
            expected = device.caps.get("expected_version") or None
            if expected:
                self._assert_package_version(device.id, package, expected)

    def launch(
        self,
        device: Device,
        *,
        package: str,
        activity: str | None = None,
    ) -> None:
        if activity:
            component = activity if "/" in activity else f"{package}/{activity}"
            self._adb.run(
                ["shell", "am", "start", "-n", component],
                serial=device.id,
            )
        else:
            # monkey launches the default launcher activity for the package.
            self._adb.run(
                [
                    "shell",
                    "monkey",
                    "-p",
                    package,
                    "-c",
                    "android.intent.category.LAUNCHER",
                    "1",
                ],
                serial=device.id,
            )

    def stop(self, device: Device, *, package: str) -> None:
        self._adb.run(["shell", "am", "force-stop", package], serial=device.id)

    def forward_ports(self, device: Device, mappings: list[PortMapping]) -> None:
        for m in mappings:
            local = m.local_port
            remote = m.remote_port
            self._adb.run(
                ["forward", f"tcp:{local}", f"tcp:{remote}"],
                serial=device.id,
            )
        listed = self._adb.run(["forward", "--list"], serial=device.id, check=False)
        present = parse_forward_list(listed.stdout)
        for m in mappings:
            if (m.local_port, m.remote_port) not in present:
                raise DeviceError(
                    f"adb forward post-verification failed: expected "
                    f"tcp:{m.local_port} → tcp:{m.remote_port} in "
                    f"`adb forward --list`, got: {listed.stdout.strip()!r}"
                )

    def reverse_ports(self, device: Device, mappings: list[PortMapping]) -> None:
        for m in mappings:
            # adb reverse tcp:<device> tcp:<host>
            device_port = m.remote_port
            host_port = m.local_port
            self._adb.run(
                ["reverse", f"tcp:{device_port}", f"tcp:{host_port}"],
                serial=device.id,
            )
        listed = self._adb.run(["reverse", "--list"], serial=device.id, check=False)
        present = parse_reverse_list(listed.stdout)
        if not present and mappings:
            raise DeviceError(
                "adb reverse post-verification failed: `adb reverse --list` is empty "
                f"after mounting {[(m.remote_port, m.local_port) for m in mappings]}. "
                "Silent reverse failure is a design-rule violation — check USB "
                "authorization and adb version. See docs/android.md."
            )
        for m in mappings:
            if (m.remote_port, m.local_port) not in present:
                raise DeviceError(
                    f"adb reverse post-verification failed: expected "
                    f"tcp:{m.remote_port} → tcp:{m.local_port} in "
                    f"`adb reverse --list`, got: {listed.stdout.strip()!r}"
                )

    def clear_port_mappings(self, device: Device) -> None:
        self._adb.run(["forward", "--remove-all"], serial=device.id, check=False)
        self._adb.run(["reverse", "--remove-all"], serial=device.id, check=False)

    def logs(self, device: Device, *, clear: bool = False) -> str:
        buf = self._logcats.setdefault(
            device.id, LogcatBuffer(maxlen=self._logcat_maxlen)
        )
        return buf.refresh_from_adb(self._adb, serial=device.id, clear_device=clear)

    def shell(self, device: Device, command: str) -> str:
        result = self._adb.run(["shell", command], serial=device.id)
        return result.stdout

    def _read_api_level(self, serial: str) -> int | None:
        result = self._adb.run(
            ["shell", "getprop", "ro.build.version.sdk"],
            serial=serial,
            check=False,
        )
        raw = result.stdout.strip()
        if not raw:
            return None
        try:
            return int(raw)
        except ValueError:
            return None

    def _assert_package_version(self, serial: str, package: str, expected: str) -> None:
        dump = self._adb.run(
            ["shell", "dumpsys", "package", package],
            serial=serial,
            check=False,
        )
        version = parse_version_name(dump.stdout)
        if version is None:
            raise DeviceError(
                f"could not read versionName for package {package!r} after install"
            )
        if version != expected:
            raise DeviceError(
                f"installed versionName={version!r} for {package!r} "
                f"does not match expected {expected!r}"
            )
