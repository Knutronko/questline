"""DeviceProviderPort protocol and shared device types (architecture §3.2)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Protocol, runtime_checkable

PortDirection = Literal["forward", "reverse"]


@dataclass(frozen=True, slots=True)
class DeviceSpec:
    """Request for a device from a provider (acquire filter)."""

    platform: str  # android | ios | …
    id: str | None = None  # serial / UDID pin; None = first matching
    api_level: int | None = None
    caps: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Device:
    """Acquired device handle (id + platform + optional caps)."""

    id: str
    platform: str
    api_level: int | None = None
    caps: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PortMapping:
    """Host↔device TCP mapping. For reverse: remote=device, local=host."""

    local_port: int
    remote_port: int
    direction: PortDirection = "reverse"


@runtime_checkable
class DeviceProviderPort(Protocol):
    """Device lifecycle: discover, lock, install, launch, ports, logs, shell."""

    def list_devices(self) -> list[Device]:
        """Return currently visible devices (online)."""
        ...

    def acquire(self, spec: DeviceSpec) -> Device:
        """Claim a device matching *spec* (exclusive lock). Raises DeviceError."""
        ...

    def release(self, device: Device) -> None:
        """Release lock and clean session state for *device*."""
        ...

    def install(self, device: Device, artifact: Path, *, package: str | None = None) -> None:
        """Install an APK/IPA artifact; optional package for version check."""
        ...

    def launch(
        self,
        device: Device,
        *,
        package: str,
        activity: str | None = None,
    ) -> None:
        """Start the app on *device*."""
        ...

    def stop(self, device: Device, *, package: str) -> None:
        """Force-stop the app on *device*."""
        ...

    def forward_ports(self, device: Device, mappings: list[PortMapping]) -> None:
        """``adb forward`` (host→device). Verifies ``adb forward --list`` after mount."""
        ...

    def reverse_ports(self, device: Device, mappings: list[PortMapping]) -> None:
        """``adb reverse`` (device→host). Verifies ``adb reverse --list`` after mount.

        A silent reverse failure is a design-rule violation — empty list after mount
        must raise DeviceError.
        """
        ...

    def clear_port_mappings(self, device: Device) -> None:
        """Remove all forward/reverse mappings for *device*."""
        ...

    def logs(self, device: Device, *, clear: bool = False) -> str:
        """Return recent logcat (or start buffer dump). Optionally clear first."""
        ...

    def shell(self, device: Device, command: str) -> str:
        """Run a shell command on *device*; return stdout (stderr merged on failure)."""
        ...
