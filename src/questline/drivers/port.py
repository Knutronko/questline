"""DriverPort protocol and shared driver types (architecture §3.1)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from questline.core.waits import WaitPolicy
from questline.drivers.locators import Locator

# Circular import avoided: locators does not import port.


@dataclass(frozen=True, slots=True)
class ConnectionTarget:
    """Where and how a driver should attach to a game/session."""

    host: str = "127.0.0.1"
    port: int = 13000
    platform: str | None = None  # editor | standalone | android | ios | …
    app_id: str | None = None
    extras: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Point:
    x: float
    y: float


@dataclass(frozen=True, slots=True)
class Element:
    """Driver-agnostic UI element snapshot."""

    id: str
    name: str = ""
    path: str = ""
    text: str = ""
    visible: bool = True
    enabled: bool = True
    component: str | None = None
    bounds: tuple[float, float, float, float] | None = None  # x, y, w, h
    attrs: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class HierarchyNode:
    element: Element
    children: tuple[HierarchyNode, ...] = ()


@dataclass(frozen=True, slots=True)
class HierarchySnapshot:
    """Normalized scene tree — adapters must not leak native node types here."""

    roots: tuple[HierarchyNode, ...]
    scene: str | None = None


@dataclass(frozen=True, slots=True)
class AppState:
    foreground: bool = True
    scene: str | None = None
    paused: bool = False
    extras: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class GameHook:
    """Named debug hook exposed by the Unity companion package (Phase 04)."""

    name: str
    causes_soft_reload: bool = False


@runtime_checkable
class DriverPort(Protocol):
    """Game UI automation port. Adapters compile Locator → native query."""

    def connect(self, target: ConnectionTarget) -> None: ...

    def disconnect(self) -> None: ...

    def is_alive(self) -> bool: ...

    def find(
        self,
        locator: Locator,
        policy: WaitPolicy | None = None,
        *,
        budget: str = "deadline",
    ) -> Element: ...

    def find_all(self, locator: Locator) -> list[Element]: ...

    def hierarchy(self) -> HierarchySnapshot: ...

    def screenshot(self) -> bytes: ...

    def tap(self, target: Element | Point) -> None: ...

    def press(self, target: Element | Point, duration: float = 0.1) -> None: ...

    def swipe(
        self, start: Element | Point, end: Element | Point, duration: float = 0.2
    ) -> None: ...

    def text_input(self, element: Element, text: str, *, clear: bool = True) -> None: ...

    def call_game_method(self, hook: GameHook, *args: Any) -> Any: ...

    def app_state(self) -> AppState: ...

    def compile(self, locator: Locator) -> Any:
        """Compile a driver-agnostic Locator into this adapter's native query."""
        ...
