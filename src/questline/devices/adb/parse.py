"""Parse ``adb devices -l`` and related adb text outputs."""

from __future__ import annotations

import re
from dataclasses import dataclass

from questline.devices.port import Device

_DEVICE_LINE = re.compile(
    r"^(?P<serial>[^\s*]+)\s+(?P<state>device|offline|unauthorized|no\spermissions|authorizing)\b(?:\s+(?P<rest>.*))?$"
)
_PROP = re.compile(r"(\w+):(\S+)")


@dataclass(frozen=True, slots=True)
class AdbDeviceRow:
    serial: str
    state: str
    product: str | None = None
    model: str | None = None
    device: str | None = None
    transport_id: str | None = None
    usb: str | None = None


def parse_adb_devices_l(text: str) -> list[AdbDeviceRow]:
    """Parse ``adb devices -l`` stdout into rows (excludes header / empties)."""
    rows: list[AdbDeviceRow] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.lower().startswith("list of devices"):
            continue
        m = _DEVICE_LINE.match(stripped)
        if not m:
            continue
        rest = m.group("rest") or ""
        props = {k: v for k, v in _PROP.findall(rest)}
        rows.append(
            AdbDeviceRow(
                serial=m.group("serial"),
                state=m.group("state"),
                product=props.get("product"),
                model=props.get("model"),
                device=props.get("device"),
                transport_id=props.get("transport_id"),
                usb=props.get("usb"),
            )
        )
    return rows


def online_devices(text: str, *, platform: str = "android") -> list[Device]:
    """Return Device models for rows in state ``device`` (ready)."""
    out: list[Device] = []
    for row in parse_adb_devices_l(text):
        if row.state != "device":
            continue
        caps: dict[str, str] = {"state": row.state}
        if row.model:
            caps["model"] = row.model
        if row.product:
            caps["product"] = row.product
        if row.device:
            caps["device"] = row.device
        if row.usb:
            caps["usb"] = row.usb
        if row.transport_id:
            caps["transport_id"] = row.transport_id
        out.append(Device(id=row.serial, platform=platform, caps=caps))
    return out


def parse_reverse_list(text: str) -> list[tuple[int, int]]:
    """Parse ``adb reverse --list`` → list of (device_port, host_port).

    Example line: ``UsbFfs tcp:13000 tcp:13000``
    """
    mappings: list[tuple[int, int]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        ports = re.findall(r"tcp:(\d+)", stripped)
        if len(ports) >= 2:
            mappings.append((int(ports[0]), int(ports[1])))
    return mappings


def parse_forward_list(text: str) -> list[tuple[int, int]]:
    """Parse ``adb forward --list`` → list of (host_port, device_port)."""
    return parse_reverse_list(text)


_VERSION_NAME = re.compile(r"versionName=([^\s]+)")


def parse_version_name(dumpsys_package: str) -> str | None:
    m = _VERSION_NAME.search(dumpsys_package)
    return m.group(1) if m else None
