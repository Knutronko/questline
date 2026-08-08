"""AltTester transport protocol — real AltDriver or a test double."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from questline.core.errors import InfraError
from questline.drivers.port import ConnectionTarget


@dataclass
class AltElementData:
    """Minimal element payload returned by a transport (real or fake)."""

    id: str
    name: str = ""
    text: str = ""
    enabled: bool = True
    x: float = 0.0
    y: float = 0.0
    transform_id: int = 0
    transform_parent_id: int = 0
    type: str = ""
    attrs: dict[str, str] = field(default_factory=dict)


@runtime_checkable
class AltTransport(Protocol):
    """Subset of AltDriver used by AltTesterDriver (mockable in unit tests)."""

    def stop(self) -> None: ...

    def find_object(self, by: str, value: str, *, enabled: bool = True) -> AltElementData: ...

    def find_objects(
        self, by: str, value: str, *, enabled: bool = True
    ) -> list[AltElementData]: ...

    def get_all_elements(self, *, enabled: bool = True) -> list[AltElementData]: ...

    def get_current_scene(self) -> str: ...

    def get_png_screenshot(self, path: str) -> None: ...

    def tap_xy(self, x: float, y: float) -> None: ...

    def hold_xy(self, x: float, y: float, duration: float) -> None: ...

    def swipe_xy(
        self, start_x: float, start_y: float, end_x: float, end_y: float, duration: float
    ) -> None: ...

    def set_text(self, element: AltElementData, text: str, *, submit: bool = False) -> None: ...

    def call_static_method(
        self,
        type_name: str,
        method_name: str,
        assembly: str,
        parameters: list[Any] | None = None,
        type_of_parameters: list[str] | None = None,
    ) -> Any: ...


def connect_real_transport(target: ConnectionTarget) -> AltTransport:
    """Construct a live AltDriver session for *target*."""
    try:
        from alttester import AltDriver
        from alttester import By as AltBy
    except ImportError as exc:  # pragma: no cover - exercised when extra missing
        raise InfraError(
            "AltTester-Driver is not installed. "
            'Install with: pip install "questline[alttester]" '
            "(or uv pip install -e \".[alttester]\")."
        ) from exc

    platform = (target.platform or "editor").lower()
    host = target.host
    port = target.port
    app_name = target.extras.get("app_name", target.app_id or "__default__")
    timeout_raw = target.extras.get("connect_timeout", "60")
    try:
        timeout = float(timeout_raw)
    except ValueError as exc:
        raise InfraError(f"invalid connect_timeout {timeout_raw!r}") from exc

    # android target is wired for Phase 05; connection params still work today.
    if platform == "android":
        host = target.extras.get("host", host)
        port = int(target.extras.get("port", str(port)))

    try:
        driver = AltDriver(
            host=host,
            port=port,
            app_name=app_name,
            timeout=timeout,
            platform=platform,
            app_id=target.app_id or "unknown",
        )
    except Exception as exc:
        from questline.drivers.alttester.errors import map_alttester_error

        raise map_alttester_error(exc) from exc

    return _RealAltTransport(driver, AltBy)


class _RealAltTransport:
    """Thin adapter over ``alttester.AltDriver`` → ``AltTransport``."""

    def __init__(self, driver: Any, by_enum: Any) -> None:
        self._driver = driver
        self._by = by_enum
        self._objects: dict[str, Any] = {}

    def stop(self) -> None:
        try:
            self._driver.stop()
        finally:
            self._objects.clear()

    def _by_value(self, by: str) -> Any:
        try:
            return getattr(self._by, by)
        except AttributeError as exc:
            raise InfraError(f"unknown AltTester By strategy: {by!r}") from exc

    def _to_data(self, obj: Any) -> AltElementData:
        eid = str(getattr(obj, "id", "") or getattr(obj, "transformId", ""))
        data = AltElementData(
            id=eid,
            name=str(getattr(obj, "name", "") or ""),
            text=str(getattr(obj, "text", "") or _safe_get_text(obj)),
            enabled=bool(getattr(obj, "enabled", True)),
            x=float(getattr(obj, "x", 0.0) or 0.0),
            y=float(getattr(obj, "y", 0.0) or 0.0),
            transform_id=int(getattr(obj, "transformId", 0) or 0),
            transform_parent_id=int(getattr(obj, "transformParentId", 0) or 0),
            type=str(getattr(obj, "type", "") or ""),
        )
        self._objects[eid] = obj
        return data

    def find_object(self, by: str, value: str, *, enabled: bool = True) -> AltElementData:
        obj = self._driver.find_object(self._by_value(by), value, enabled=enabled)
        return self._to_data(obj)

    def find_objects(self, by: str, value: str, *, enabled: bool = True) -> list[AltElementData]:
        objs = self._driver.find_objects(self._by_value(by), value, enabled=enabled)
        return [self._to_data(o) for o in objs]

    def get_all_elements(self, *, enabled: bool = True) -> list[AltElementData]:
        objs = self._driver.get_all_elements(enabled=enabled)
        return [self._to_data(o) for o in objs]

    def get_current_scene(self) -> str:
        return str(self._driver.get_current_scene())

    def get_png_screenshot(self, path: str) -> None:
        self._driver.get_png_screenshot(path)

    def tap_xy(self, x: float, y: float) -> None:
        from alttester import AltVector2

        self._driver.tap(AltVector2(x, y))

    def hold_xy(self, x: float, y: float, duration: float) -> None:
        from alttester import AltVector2

        self._driver.hold_button(AltVector2(x, y), duration=duration)

    def swipe_xy(
        self, start_x: float, start_y: float, end_x: float, end_y: float, duration: float
    ) -> None:
        from alttester import AltVector2

        self._driver.swipe(
            AltVector2(start_x, start_y),
            AltVector2(end_x, end_y),
            duration=duration,
        )

    def set_text(self, element: AltElementData, text: str, *, submit: bool = False) -> None:
        obj = self._objects.get(element.id)
        if obj is None:
            raise InfraError(f"no live AltObject cached for element id={element.id!r}")
        obj.set_text(text, submit=submit)

    def call_static_method(
        self,
        type_name: str,
        method_name: str,
        assembly: str,
        parameters: list[Any] | None = None,
        type_of_parameters: list[str] | None = None,
    ) -> Any:
        return self._driver.call_static_method(
            type_name,
            method_name,
            assembly,
            parameters=parameters,
            type_of_parameters=type_of_parameters,
        )


def _safe_get_text(obj: Any) -> str:
    getter = getattr(obj, "get_text", None)
    if callable(getter):
        try:
            return str(getter() or "")
        except Exception:
            return ""
    return ""
