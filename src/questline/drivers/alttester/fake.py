"""Fake AltTransport for AltTesterDriver unit / conformance tests (no live Unity)."""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from questline.core.errors import AuthoringError, ElementNotFoundError, SessionLostError
from questline.drivers.alttester.hooks import (
    HOOKS_ASSEMBLY,
    HOOKS_TYPE_NAME,
    INVOKE_METHOD,
    MANIFEST_METHOD,
)
from questline.drivers.alttester.transport import AltElementData, AltTransport
from questline.drivers.port import ConnectionTarget


@dataclass
class _Node:
    data: AltElementData
    appear_at: float | None = None
    on_tap: Callable[[], None] | None = None

    def visible(self, now: float) -> bool:
        if self.appear_at is not None and now < self.appear_at:
            return False
        return True


class FakeAltTransport:
    """In-memory AltTransport with a tiny scene + hook registry."""

    def __init__(
        self,
        *,
        clock: Callable[[], float] | None = None,
        screenshot_bytes: bytes = b"\x89PNG\r\n\x1a\nfake-alt",
    ) -> None:
        self._clock = clock or time.monotonic
        self._screenshot_bytes = screenshot_bytes
        self._nodes: dict[str, _Node] = {}
        self._scene = "FakeScene"
        self._alive = True
        self._hooks: dict[str, dict[str, Any]] = {}
        self._hook_impls: dict[str, Callable[..., Any]] = {}
        self.connect_count = 1
        self._seed_default_tree()

    def _seed_default_tree(self) -> None:
        canvas = AltElementData(
            id="1",
            name="Canvas",
            transform_id=1,
            transform_parent_id=0,
            attrs={"path": "/Canvas"},
        )
        btn = AltElementData(
            id="2",
            name="OkButton",
            text="OK",
            x=10.0,
            y=20.0,
            transform_id=2,
            transform_parent_id=1,
            attrs={"path": "/Canvas/OkButton"},
        )
        label = AltElementData(
            id="3",
            name="Greeting",
            text="Hello",
            transform_id=3,
            transform_parent_id=1,
            attrs={"path": "/Canvas/Greeting"},
        )
        # Use id matching conformance expectations (btn_ok).
        btn.id = "btn_ok"
        label.id = "lbl_hi"
        canvas.id = "canvas"
        self._nodes = {
            "canvas": _Node(canvas),
            "btn_ok": _Node(btn),
            "lbl_hi": _Node(label),
        }
        # Register sample companion hooks (mirrors unity-package contract).
        self.register_hook("GetManifestProbe", [], causes_soft_reload=False, feature="smoke")
        self._hook_impls["GetManifestProbe"] = lambda: "ok"
        self.register_hook("SoftReload", [], causes_soft_reload=True, feature=None)
        self._hook_impls["SoftReload"] = self._do_soft_reload

    def register_hook(
        self,
        name: str,
        args: list[dict[str, str]],
        *,
        causes_soft_reload: bool = False,
        feature: str | None = None,
    ) -> None:
        self._hooks[name] = {
            "name": name,
            "args": args,
            "causesSoftReload": causes_soft_reload,
            "feature": feature,
        }

    def schedule_appear(self, node_id: str, after_s: float) -> None:
        node = self._nodes.get(node_id)
        if node is None:
            raise AuthoringError(f"unknown node {node_id!r}")
        node.appear_at = self._clock() + after_s

    def _do_soft_reload(self) -> None:
        # Simulate session death until Python re-handshakes (new transport instance).
        self._alive = False

    def stop(self) -> None:
        self._alive = False

    def _ensure_alive(self) -> None:
        if not self._alive:
            raise SessionLostError(
                "fake alt transport dead",
                kind="app_disconnected",
                close_code=4002,
            )

    def find_object(self, by: str, value: str, *, enabled: bool = True) -> AltElementData:
        found = self.find_objects(by, value, enabled=enabled)
        if not found:
            raise ElementNotFoundError(f"not found: {by}={value}")
        return found[0]

    def find_objects(self, by: str, value: str, *, enabled: bool = True) -> list[AltElementData]:
        self._ensure_alive()
        now = self._clock()
        out: list[AltElementData] = []
        for node in self._nodes.values():
            if not node.visible(now):
                continue
            if enabled and not node.data.enabled:
                continue
            if _matches(node.data, by, value):
                out.append(node.data)
        return out

    def get_all_elements(self, *, enabled: bool = True) -> list[AltElementData]:
        self._ensure_alive()
        now = self._clock()
        return [
            n.data
            for n in self._nodes.values()
            if n.visible(now) and (n.data.enabled if enabled else True)
        ]

    def get_current_scene(self) -> str:
        self._ensure_alive()
        return self._scene

    def get_png_screenshot(self, path: str) -> None:
        self._ensure_alive()
        with open(path, "wb") as fh:
            fh.write(self._screenshot_bytes)

    def tap_xy(self, x: float, y: float) -> None:
        self._ensure_alive()
        _ = x, y
        # Prefer tapping OkButton if present.
        node = self._nodes.get("btn_ok")
        if node and node.on_tap:
            node.on_tap()

    def hold_xy(self, x: float, y: float, duration: float) -> None:
        _ = duration
        self.tap_xy(x, y)

    def swipe_xy(
        self, start_x: float, start_y: float, end_x: float, end_y: float, duration: float
    ) -> None:
        self._ensure_alive()
        _ = start_x, start_y, end_x, end_y, duration

    def set_text(self, element: AltElementData, text: str, *, submit: bool = False) -> None:
        self._ensure_alive()
        _ = submit
        node = self._nodes.get(element.id)
        if node is None:
            # Fall back: match by id field on data.
            for n in self._nodes.values():
                if n.data.id == element.id:
                    node = n
                    break
        if node is None:
            raise ElementNotFoundError(f"text_input target not found: {element.id}")
        node.data.text = text

    def call_static_method(
        self,
        type_name: str,
        method_name: str,
        assembly: str,
        parameters: list[Any] | None = None,
        type_of_parameters: list[str] | None = None,
    ) -> Any:
        self._ensure_alive()
        _ = type_of_parameters
        if type_name != HOOKS_TYPE_NAME or assembly != HOOKS_ASSEMBLY:
            raise AuthoringError(f"unknown type {type_name} in {assembly}")
        params = parameters or []
        if method_name == MANIFEST_METHOD:
            hooks = []
            for h in self._hooks.values():
                entry = {
                    "name": h["name"],
                    "args": h["args"],
                    "causesSoftReload": h["causesSoftReload"],
                }
                if h.get("feature") is not None:
                    entry["feature"] = h["feature"]
                hooks.append(entry)
            return json.dumps({"hooks": hooks})
        if method_name == INVOKE_METHOD:
            name = str(params[0])
            args = json.loads(params[1]) if len(params) > 1 else []
            if name not in self._hook_impls:
                raise AuthoringError(f"unknown questline hook: {name}")
            result = self._hook_impls[name](*args)
            if result is None:
                return ""
            return json.dumps(result)
        raise AuthoringError(f"unknown method {method_name}")


def _matches(data: AltElementData, by: str, value: str) -> bool:
    if by == "ID":
        return data.id == value
    if by == "NAME":
        return data.name == value
    if by == "PATH":
        path = data.attrs.get("path", "")
        return path == value or path.endswith(value)
    if by == "TEXT":
        return data.text == value
    if by == "COMPONENT":
        return data.type == value
    return False


def fake_transport_factory(
    *,
    clock: Callable[[], float] | None = None,
    state: dict[str, Any] | None = None,
) -> Callable[[ConnectionTarget], AltTransport]:
    """Factory compatible with AltTesterDriver(transport_factory=...).

    *state* (optional) collects the latest FakeAltTransport for schedule_appear wiring.
    """
    bucket: dict[str, Any] = state if state is not None else {}

    def factory(target: ConnectionTarget) -> AltTransport:
        _ = target
        transport = FakeAltTransport(clock=clock)
        if "connects" in bucket:
            bucket["connects"] = int(bucket["connects"]) + 1
        else:
            bucket["connects"] = 1
        bucket["transport"] = transport
        return transport

    return factory


@dataclass
class FakeAltDriverHarness:
    """AltTesterDriver + shared fake transport state for conformance."""

    clock: Callable[[], float] = field(default=time.monotonic)
    sleeper: Callable[[float], None] = field(default=lambda _s: None)
    state: dict[str, Any] = field(default_factory=dict)

    def __call__(self) -> Any:
        from questline.drivers.alttester import AltTesterDriver

        driver = AltTesterDriver(
            transport_factory=fake_transport_factory(clock=self.clock, state=self.state),
            clock=self.clock,
            sleeper=self.sleeper,
            rehandshake_delay_s=0.0,
        )

        # Expose schedule_appear for conformance case_find_wait_appear.
        def schedule_appear(node_id: str, after_s: float) -> None:
            transport = self.state.get("transport")
            if transport is None:
                raise AuthoringError("schedule_appear before connect")
            transport.schedule_appear(node_id, after_s)

        driver.schedule_appear = schedule_appear  # type: ignore[attr-defined]
        return driver
