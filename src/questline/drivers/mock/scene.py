"""In-memory scene graph for MockDriver."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from questline.drivers.port import Element


@dataclass
class MockNode:
    """Mutable scene node. Visibility/text/handlers can change at runtime."""

    id: str
    name: str = ""
    path: str = ""
    text: str = ""
    visible: bool = True
    enabled: bool = True
    component: str | None = None
    bounds: tuple[float, float, float, float] | None = (0.0, 0.0, 10.0, 10.0)
    attrs: dict[str, str] = field(default_factory=dict)
    children: list[MockNode] = field(default_factory=list)
    parent: MockNode | None = field(default=None, repr=False)
    on_tap: Callable[[], None] | None = field(default=None, repr=False)
    # If set, node is hidden until monotonic clock >= appear_at.
    appear_at: float | None = None

    def to_element(self, *, now: float | None = None) -> Element:
        return Element(
            id=self.id,
            name=self.name,
            path=self.path or self._default_path(),
            text=self.text,
            visible=self.is_visible(now=now),
            enabled=self.enabled,
            component=self.component,
            bounds=self.bounds,
            attrs=dict(self.attrs),
        )

    def _default_path(self) -> str:
        parts: list[str] = []
        node: MockNode | None = self
        while node is not None:
            parts.append(node.name or node.id)
            node = node.parent
        return "/" + "/".join(reversed(parts))

    def is_visible(self, *, now: float | None = None) -> bool:
        if not self.visible:
            return False
        if self.appear_at is None:
            return True
        if now is None:
            # Pending timed appearance without a clock → not yet visible.
            return False
        return now >= self.appear_at

    def iter_depth_first(self) -> list[MockNode]:
        out = [self]
        for child in self.children:
            out.extend(child.iter_depth_first())
        return out


class MockScene:
    """Rooted forest of MockNodes plus hook registry."""

    def __init__(self) -> None:
        self.roots: list[MockNode] = []
        self.hooks: dict[str, Callable[..., object]] = {}
        self.scene_name: str = "MockScene"
        self.paused: bool = False
        self.foreground: bool = True

    def add(self, node: MockNode, *, parent: MockNode | None = None) -> MockNode:
        if parent is None:
            self.roots.append(node)
            node.parent = None
        else:
            parent.children.append(node)
            node.parent = parent
        if not node.path:
            node.path = node._default_path()
        return node

    def get(self, node_id: str) -> MockNode | None:
        for root in self.roots:
            for node in root.iter_depth_first():
                if node.id == node_id:
                    return node
        return None

    def all_nodes(self) -> list[MockNode]:
        out: list[MockNode] = []
        for root in self.roots:
            out.extend(root.iter_depth_first())
        return out

    def clear(self) -> None:
        self.roots.clear()
