"""Cheap liveness checks for driver / hierarchy / device (architecture §2.6)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from questline.core.errors import AuthoringError, SessionLostError


class _AliveProbe(Protocol):
    def is_alive(self) -> bool: ...


class _DeviceListProbe(Protocol):
    def list_devices(self) -> list[Any]: ...


@dataclass(frozen=True, slots=True)
class HealthSnapshot:
    """Structured result of a cheap health probe."""

    driver_alive: bool
    hierarchy_ok: bool | None = None  # None = skipped / not applicable
    device_online: bool | None = None  # None = no device provider
    details: dict[str, str] = field(default_factory=dict)

    @property
    def is_healthy(self) -> bool:
        if not self.driver_alive:
            return False
        if self.hierarchy_ok is False:
            return False
        if self.device_online is False:
            return False
        return True

    @property
    def suggests_session_loss(self) -> bool:
        """True when the snapshot indicates a lost/dead session (not a test bug)."""
        if not self.driver_alive:
            return True
        if self.hierarchy_ok is False:
            return True
        if self.device_online is False:
            return True
        return False

    def as_tags(self) -> dict[str, str]:
        tags = {
            "driver_alive": "true" if self.driver_alive else "false",
        }
        if self.hierarchy_ok is not None:
            tags["hierarchy_ok"] = "true" if self.hierarchy_ok else "false"
        if self.device_online is not None:
            tags["device_online"] = "true" if self.device_online else "false"
        tags.update(self.details)
        return tags


class HealthMonitor:
    """Cheap liveness: driver ping, optional hierarchy, optional device online."""

    def __init__(
        self,
        driver: _AliveProbe,
        *,
        device_provider: _DeviceListProbe | None = None,
        device: Any | None = None,
        check_hierarchy: bool = True,
    ) -> None:
        self._driver = driver
        self._device_provider = device_provider
        self._device = device
        self._check_hierarchy = check_hierarchy

    def check(self) -> HealthSnapshot:
        details: dict[str, str] = {}
        alive = False
        try:
            alive = bool(self._driver.is_alive())
        except SessionLostError as exc:
            details["driver_alive_error"] = f"{type(exc).__name__}: {exc}"
            alive = False
        except Exception as exc:  # best-effort probe
            details["driver_alive_error"] = f"{type(exc).__name__}: {exc}"
            alive = False

        hierarchy_ok: bool | None = None
        if self._check_hierarchy and alive:
            hierarchy_ok = self._probe_hierarchy(details)

        device_online: bool | None = None
        if self._device_provider is not None and self._device is not None:
            device_online = self._probe_device(details)

        return HealthSnapshot(
            driver_alive=alive,
            hierarchy_ok=hierarchy_ok,
            device_online=device_online,
            details=details,
        )

    def _probe_hierarchy(self, details: dict[str, str]) -> bool | None:
        hierarchy = getattr(self._driver, "hierarchy", None)
        if not callable(hierarchy):
            return None
        try:
            snap = hierarchy()
        except AuthoringError as exc:
            # Wire MVP / adapters without UI hierarchy — skip, not unhealthy.
            details["hierarchy_skipped"] = str(exc)[:200]
            return None
        except SessionLostError as exc:
            details["hierarchy_error"] = f"{type(exc).__name__}: {exc}"
            return False
        except Exception as exc:
            msg = str(exc).lower()
            if "not implement" in msg or "mvp" in msg:
                details["hierarchy_skipped"] = str(exc)[:200]
                return None
            details["hierarchy_error"] = f"{type(exc).__name__}: {exc}"
            return False

        roots = getattr(snap, "roots", None)
        if roots is None:
            details["hierarchy_error"] = "snapshot missing roots"
            return False
        if len(roots) == 0:
            details["hierarchy_error"] = "empty hierarchy"
            return False
        return True

    def _probe_device(self, details: dict[str, str]) -> bool:
        assert self._device_provider is not None and self._device is not None
        try:
            devices = self._device_provider.list_devices()
        except Exception as exc:
            details["device_online_error"] = f"{type(exc).__name__}: {exc}"
            return False
        device_id = getattr(self._device, "id", None)
        if device_id is None:
            details["device_online_error"] = "device has no id"
            return False
        online_ids = {getattr(d, "id", None) for d in devices}
        return device_id in online_ids


__all__ = ["HealthMonitor", "HealthSnapshot"]
