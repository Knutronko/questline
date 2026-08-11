"""In-memory / local fake Wire transport for CI (no Unity)."""

from __future__ import annotations

import base64
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from questline.core.errors import AuthoringError, ElementNotFoundError, SessionLostError, TestError
from questline.drivers.locators import LocatorStrategy
from questline.drivers.port import ConnectionTarget, Element, HierarchyNode, HierarchySnapshot
from questline.drivers.wire.codec import (
    element_to_dict,
    hierarchy_to_dict,
    png_to_result,
)
from questline.drivers.wire.driver import QuestlineDriver
from questline.drivers.wire.protocol import (
    DEFAULT_FEATURES,
    DEFAULT_MAX_DEPTH,
    DEFAULT_MAX_NODES,
    FEATURE_HOOKS,
    PROTOCOL_VERSION,
)

# Minimal valid 1×1 PNG.
_MIN_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


@dataclass
class FakeUiNode:
    id: str
    name: str
    path: str
    text: str = ""
    visible: bool = True
    enabled: bool = True
    component: str | None = None
    bounds: tuple[float, float, float, float] | None = None
    children: list[FakeUiNode] = field(default_factory=list)
    tapped: bool = False

    def to_element(self) -> Element:
        return Element(
            id=self.id,
            name=self.name,
            path=self.path,
            text=self.text,
            visible=self.visible,
            enabled=self.enabled,
            component=self.component,
            bounds=self.bounds,
        )


def default_fake_ui_tree() -> FakeUiNode:
    """Canvas → OkButton + Greeting + NestedButton (for multi-match / scope)."""
    btn = FakeUiNode(
        id="btn_ok",
        name="OkButton",
        path="/Canvas/OkButton",
        text="OK",
        component="Button",
        bounds=(10.0, 20.0, 80.0, 40.0),
    )
    label = FakeUiNode(
        id="lbl_hi",
        name="Greeting",
        path="/Canvas/Greeting",
        text="Hello",
        component="Text",
        bounds=(10.0, 70.0, 120.0, 24.0),
    )
    nested = FakeUiNode(
        id="btn_nested",
        name="OkButton",
        path="/Canvas/Panel/OkButton",
        text="OK",
        component="Button",
        bounds=(10.0, 100.0, 80.0, 40.0),
    )
    panel = FakeUiNode(
        id="panel",
        name="Panel",
        path="/Canvas/Panel",
        component="RectTransform",
        children=[nested],
    )
    return FakeUiNode(
        id="canvas",
        name="Canvas",
        path="/Canvas",
        component="Canvas",
        children=[btn, label, panel],
    )


class FakeWireTransport:
    """Speaks the Wire ops in-process with hooks + optional UI tree (ADR-0008)."""

    def __init__(self, state: dict[str, Any] | None = None) -> None:
        self._state = state if state is not None else {}
        self._state.setdefault("connects", 0)
        self._state["connects"] = int(self._state["connects"]) + 1
        self._closed = False
        self._hooks = {
            "Ping": {"args": [], "causesSoftReload": False, "feature": "smoke"},
            "GetManifestProbe": {"args": [], "causesSoftReload": False, "feature": None},
            "SoftReload": {"args": [], "causesSoftReload": True, "feature": None},
            "SetLevel": {
                "args": [{"name": "level", "type": "int"}],
                "causesSoftReload": False,
                "feature": "progression",
            },
            "GetPerfSample": {
                "args": [],
                "causesSoftReload": False,
                "feature": "perf",
            },
        }
        self._scene = str(self._state.get("scene", "FakeWireScene"))
        self._perf_sample = {
            "fps": 60.0,
            "allocated_mb": 128.0,
            "draw_calls": 42.0,
        }
        # legacy_mvp=True → hello without UI (protocol_version 1, hooks only).
        self._legacy_mvp = bool(self._state.get("legacy_mvp", False))
        if "ui_root" in self._state:
            # Explicit None = empty tree (distinct from unset → default fixture).
            self._ui_root: FakeUiNode | None = self._state["ui_root"]
        elif self._legacy_mvp:
            self._ui_root = None
        else:
            self._ui_root = default_fake_ui_tree()
            self._state["ui_root"] = self._ui_root
        self._screenshot = self._state.get("screenshot_bytes", _MIN_PNG)
        self._screenshot_fail = bool(self._state.get("screenshot_fail", False))
        self._max_depth = int(self._state.get("max_depth", DEFAULT_MAX_DEPTH))
        self._max_nodes = int(self._state.get("max_nodes", DEFAULT_MAX_NODES))
        self._point_taps: list[tuple[float, float]] = self._state.setdefault("point_taps", [])

    def request(self, op: str, params: dict[str, Any] | None = None) -> Any:
        if self._closed:
            raise SessionLostError("fake wire closed", kind="disposed")
        params = params or {}
        if op == "hello":
            return self._hello()
        if op == "ping":
            return {"pong": True}
        if op == "app_state":
            return {"foreground": True, "scene": self._scene, "paused": False}
        if op == "hooks_manifest":
            hooks = []
            for name, meta in self._hooks.items():
                hooks.append(
                    {
                        "name": name,
                        "args": meta["args"],
                        "causesSoftReload": meta["causesSoftReload"],
                        "feature": meta["feature"],
                    }
                )
            return {"hooks": hooks}
        if op == "call_hook":
            return self._call_hook(params)
        if op in {"hierarchy", "find", "find_all", "tap", "screenshot"}:
            if self._legacy_mvp:
                raise AuthoringError(f"unknown op: {op}")
            return self._ui_op(op, params)
        raise AuthoringError(f"unknown op: {op}")

    def close(self) -> None:
        self._closed = True

    def _hello(self) -> dict[str, Any]:
        if self._legacy_mvp:
            return {
                "protocol_version": 1,
                "companion_version": "0.1.0",
                "scene": self._scene,
                "features": [FEATURE_HOOKS],
            }
        return {
            "protocol_version": PROTOCOL_VERSION,
            "companion_version": "0.1.0",
            "scene": self._scene,
            "features": list(DEFAULT_FEATURES),
        }

    def _call_hook(self, params: dict[str, Any]) -> Any:
        name = params.get("name")
        if not name or not isinstance(name, str):
            raise AuthoringError("call_hook requires params.name")
        if name not in self._hooks:
            raise AuthoringError(f"unknown questline hook: {name}")
        args = params.get("args") or []
        if name == "Ping":
            return {"value": "pong"}
        if name == "GetManifestProbe":
            return {"value": "ok"}
        if name == "SoftReload":
            return {"value": None}
        if name == "SetLevel":
            if not args:
                raise AuthoringError("SetLevel requires level")
            return {"value": None}
        if name == "GetPerfSample":
            return {"value": dict(self._perf_sample)}
        raise TestError(f"hook failed: {name}")

    def _ui_op(self, op: str, params: dict[str, Any]) -> Any:
        if op == "hierarchy":
            return self._hierarchy(params)
        if op == "find":
            matches = self._query(params)
            if not matches:
                raise ElementNotFoundError(
                    f"element not found: {params.get('by')}={params.get('value')!r}"
                )
            return {"element": element_to_dict(matches[0].to_element())}
        if op == "find_all":
            matches = self._query(params)
            return {"elements": [element_to_dict(m.to_element()) for m in matches]}
        if op == "tap":
            return self._tap(params)
        if op == "screenshot":
            if self._screenshot_fail:
                raise AuthoringError("screenshot capture failed")
            data = self._screenshot
            if not isinstance(data, (bytes, bytearray)) or not data:
                raise AuthoringError("screenshot returned empty PNG payload")
            return png_to_result(bytes(data))
        raise AuthoringError(f"unknown op: {op}")

    def _hierarchy(self, params: dict[str, Any]) -> dict[str, Any]:
        max_depth = int(params.get("max_depth", self._max_depth))
        max_nodes = int(params.get("max_nodes", self._max_nodes))
        if self._ui_root is None:
            snap = HierarchySnapshot(roots=(), scene=self._scene)
            return hierarchy_to_dict(snap, truncated=False, node_count=0)
        counter = {"n": 0, "truncated": False}

        def convert(node: FakeUiNode, depth: int) -> HierarchyNode | None:
            if counter["n"] >= max_nodes:
                counter["truncated"] = True
                return None
            if depth > max_depth:
                counter["truncated"] = True
                return None
            if not node.visible:
                return None
            counter["n"] += 1
            kids: list[HierarchyNode] = []
            if depth < max_depth:
                for child in node.children:
                    converted = convert(child, depth + 1)
                    if converted is not None:
                        kids.append(converted)
                    if counter["truncated"] and counter["n"] >= max_nodes:
                        break
            elif node.children:
                counter["truncated"] = True
            return HierarchyNode(element=node.to_element(), children=tuple(kids))

        root = convert(self._ui_root, 0)
        roots = (root,) if root is not None else ()
        snap = HierarchySnapshot(roots=roots, scene=self._scene)
        return hierarchy_to_dict(
            snap, truncated=bool(counter["truncated"]), node_count=counter["n"]
        )

    def _all_nodes(self) -> list[FakeUiNode]:
        if self._ui_root is None:
            return []
        out: list[FakeUiNode] = []

        def walk(node: FakeUiNode) -> None:
            out.append(node)
            for child in node.children:
                walk(child)

        walk(self._ui_root)
        return out

    def _query(self, params: dict[str, Any]) -> list[FakeUiNode]:
        by = params.get("by")
        value = params.get("value")
        scope = params.get("scope")
        if not isinstance(by, str) or not by:
            raise AuthoringError("find requires params.by")
        if not isinstance(value, str) or not value:
            raise AuthoringError("find requires params.value")
        try:
            strategy = LocatorStrategy(by)
        except ValueError as exc:
            raise AuthoringError(f"unsupported locator strategy: {by!r}") from exc
        scope_s = scope if isinstance(scope, str) and scope else None
        matches: list[FakeUiNode] = []
        for node in self._all_nodes():
            if not node.visible:
                continue
            if scope_s and scope_s not in (node.path, node.id, node.name):
                if scope_s not in node.path:
                    continue
            if _matches(node, strategy, value):
                matches.append(node)
        return matches

    def _tap(self, params: dict[str, Any]) -> dict[str, Any]:
        if "element_id" in params and params["element_id"] is not None:
            eid = params["element_id"]
            if not isinstance(eid, str) or not eid:
                raise AuthoringError("tap element_id must be a non-empty string")
            node = next((n for n in self._all_nodes() if n.id == eid), None)
            if node is None or not node.visible:
                raise ElementNotFoundError(f"tap target not found: {eid}")
            if not node.enabled:
                raise ElementNotFoundError(f"tap target disabled: {eid}")
            node.tapped = True
            return {"ok": True}
        point = params.get("point")
        if isinstance(point, dict):
            try:
                x = float(point["x"])
                y = float(point["y"])
            except (KeyError, TypeError, ValueError) as exc:
                raise AuthoringError("tap point requires numeric x/y") from exc
            self._point_taps.append((x, y))
            return {"ok": True}
        raise AuthoringError("tap requires element_id or point")


def _matches(node: FakeUiNode, by: LocatorStrategy, value: str) -> bool:
    if by is LocatorStrategy.ID:
        return node.id == value
    if by is LocatorStrategy.NAME:
        return node.name == value
    if by is LocatorStrategy.PATH:
        return node.path == value or node.path.endswith(value)
    if by is LocatorStrategy.TEXT:
        return node.text == value
    if by is LocatorStrategy.COMPONENT:
        return node.component == value
    return False


def fake_transport_factory(
    state: dict[str, Any] | None = None,
) -> Callable[[ConnectionTarget], FakeWireTransport]:
    shared = state if state is not None else {}

    def factory(_target: ConnectionTarget) -> FakeWireTransport:
        return FakeWireTransport(state=shared)

    return factory


class FakeWireDriverHarness:
    """Zero-arg factory returning a fresh QuestlineDriver with fake transport."""

    def __init__(
        self,
        *,
        sleeper: Callable[[float], None] | None = None,
        rehandshake_delay_s: float = 0.0,
        state: dict[str, Any] | None = None,
    ) -> None:
        self._sleeper = sleeper or (lambda _s: None)
        self._rehandshake_delay_s = rehandshake_delay_s
        self._state = state if state is not None else {}

    def __call__(self) -> QuestlineDriver:
        return QuestlineDriver(
            transport_factory=fake_transport_factory(state=self._state),
            rehandshake_delay_s=self._rehandshake_delay_s,
            sleeper=self._sleeper,
        )


# Re-export for tests that build FakeWire trees without the driver.
__all__ = [
    "FakeUiNode",
    "FakeWireDriverHarness",
    "FakeWireTransport",
    "default_fake_ui_tree",
    "fake_transport_factory",
]
