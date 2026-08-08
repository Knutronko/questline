"""MockDriver: full DriverPort against an in-memory scene graph."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal

from questline.core.errors import (
    AuthoringError,
    ElementNotFoundError,
    SessionLostError,
)
from questline.core.waits import WaitPolicy, wait_for
from questline.drivers.locators import Locator, LocatorStrategy
from questline.drivers.mock.scene import MockNode, MockScene
from questline.drivers.port import (
    AppState,
    ConnectionTarget,
    Element,
    GameHook,
    HierarchyNode,
    HierarchySnapshot,
    Point,
)

BudgetKind = Literal["probe", "deadline"]


@dataclass(frozen=True, slots=True)
class MockNativeQuery:
    """Compiled form of a Locator for the mock adapter."""

    by: LocatorStrategy
    value: str
    scope: str | None = None


class MockDriver:
    """In-memory driver used by conformance tests and later fault-injection phases."""

    def __init__(
        self,
        scene: MockScene | None = None,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        self.scene = scene if scene is not None else MockScene()
        self._clock = clock
        self._sleeper = sleeper
        self._alive = False
        self._connected_target: ConnectionTarget | None = None
        self._commands = 0
        self._drop_after: int | None = None
        self._hang_after: int | None = None
        self._hang_block: Callable[[], None] | None = None
        self._hang_on_connect_block: Callable[[], None] | None = None
        self._screenshot_bytes = b"\x89PNG\r\n\x1a\nmock-screenshot"
        self._disposed = False

    # --- fault injection / scripting ---

    def schedule_appear(self, node_id: str, after_s: float) -> None:
        """Make *node_id* become visible after *after_s* seconds (from now)."""
        node = self.scene.get(node_id)
        if node is None:
            raise AuthoringError(f"schedule_appear: unknown node '{node_id}'")
        node.visible = True
        node.appear_at = self._clock() + after_s

    def drop_after_commands(self, n: int) -> None:
        """Force SessionLostError on the Nth subsequent port command (N >= 1)."""
        if n < 1:
            raise AuthoringError("drop_after_commands requires n >= 1")
        self._drop_after = n
        self._commands = 0

    def hang_after_commands(self, n: int, block: Callable[[], None] | None = None) -> None:
        """Block forever (or via *block*) on the Nth subsequent port command."""
        if n < 1:
            raise AuthoringError("hang_after_commands requires n >= 1")
        self._hang_after = n
        self._commands = 0
        if block is not None:
            self._hang_block = block
        else:
            never = threading.Event()

            def _block_forever() -> None:
                never.wait()

            self._hang_block = _block_forever

    def hang_on_connect(self, block: Callable[[], None] | None = None) -> None:
        """Block inside ``connect`` (for hung-recovery watchdog tests)."""
        if block is not None:
            self._hang_on_connect_block = block
        else:
            never = threading.Event()

            def _block_forever() -> None:
                never.wait()

            self._hang_on_connect_block = _block_forever

    def force_disconnect(self) -> None:
        """Simulate an abrupt session drop."""
        self._alive = False
        self._connected_target = None

    def set_screenshot(self, data: bytes) -> None:
        self._screenshot_bytes = data

    # --- DriverPort ---

    def connect(self, target: ConnectionTarget) -> None:
        self._ensure_not_disposed()
        if self._hang_on_connect_block is not None:
            blocker = self._hang_on_connect_block
            self._hang_on_connect_block = None
            blocker()
        self._connected_target = target
        self._alive = True
        self._commands = 0

    def disconnect(self) -> None:
        self._alive = False
        self._connected_target = None
        self._disposed = True

    def is_alive(self) -> bool:
        return self._alive and not self._disposed

    def find(
        self,
        locator: Locator,
        policy: WaitPolicy | None = None,
        *,
        budget: str = "deadline",
    ) -> Element:
        self._touch()
        kind = _parse_budget(budget)
        if policy is None:
            matches = self._query(locator)
            if not matches:
                raise ElementNotFoundError(
                    f"element not found: {locator.by.value}={locator.value!r}"
                )
            return matches[0].to_element(now=self._clock())

        seconds = policy.probe if kind == "probe" else policy.deadline
        wait_policy = WaitPolicy(probe=policy.probe, deadline=seconds, interval=policy.interval)

        def condition() -> Element | bool:
            self._touch()
            matches = self._query(locator)
            if matches:
                return matches[0].to_element(now=self._clock())
            return False

        result = wait_for(
            condition,
            wait_policy,
            on_timeout="return_false",
            clock=self._clock,
            sleeper=self._sleeper,
        )
        if result is False:
            raise ElementNotFoundError(
                f"element not found within {kind} budget ({seconds}s): "
                f"{locator.by.value}={locator.value!r}"
            )
        return result  # type: ignore[return-value]

    def find_all(self, locator: Locator) -> list[Element]:
        self._touch()
        now = self._clock()
        return [n.to_element(now=now) for n in self._query(locator)]

    def hierarchy(self) -> HierarchySnapshot:
        self._touch()
        now = self._clock()

        def convert(node: MockNode) -> HierarchyNode | None:
            if not node.is_visible(now=now):
                return None
            kids = tuple(
                child
                for child in (convert(c) for c in node.children)
                if child is not None
            )
            return HierarchyNode(element=node.to_element(now=now), children=kids)

        roots = tuple(n for n in (convert(r) for r in self.scene.roots) if n is not None)
        return HierarchySnapshot(roots=roots, scene=self.scene.scene_name)

    def screenshot(self) -> bytes:
        self._touch()
        return self._screenshot_bytes

    def tap(self, target: Element | Point) -> None:
        self._touch()
        if isinstance(target, Point):
            return
        node = self.scene.get(target.id)
        if node is None or not node.is_visible(now=self._clock()):
            raise ElementNotFoundError(f"tap target not found: {target.id}")
        if not node.enabled:
            raise ElementNotFoundError(f"tap target disabled: {target.id}")
        if node.on_tap is not None:
            node.on_tap()

    def press(self, target: Element | Point, duration: float = 0.1) -> None:
        _ = duration
        self.tap(target)

    def swipe(
        self,
        start: Element | Point,
        end: Element | Point,
        duration: float = 0.2,
    ) -> None:
        _ = start, end, duration
        self._touch()

    def text_input(self, element: Element, text: str, *, clear: bool = True) -> None:
        self._touch()
        node = self.scene.get(element.id)
        if node is None:
            raise ElementNotFoundError(f"text_input target not found: {element.id}")
        node.text = text if clear else node.text + text

    def call_game_method(self, hook: GameHook, *args: Any) -> Any:
        self._touch()
        fn = self.scene.hooks.get(hook.name)
        if fn is None:
            raise AuthoringError(f"unknown game hook: {hook.name}")
        return fn(*args)

    def hooks_manifest(self) -> list[Any]:
        """Synthesize a manifest from MockScene.hooks (no soft-reload metadata)."""
        from questline.drivers.hooks import HookManifestEntry

        self._touch()
        return [
            HookManifestEntry(name=name, args=(), causes_soft_reload=False, feature=None)
            for name in sorted(self.scene.hooks)
        ]

    def app_state(self) -> AppState:
        self._touch()
        return AppState(
            foreground=self.scene.foreground,
            scene=self.scene.scene_name,
            paused=self.scene.paused,
        )

    def compile(self, locator: Locator) -> MockNativeQuery:
        return MockNativeQuery(by=locator.by, value=locator.value, scope=locator.scope)

    # --- internals ---

    def _ensure_not_disposed(self) -> None:
        if self._disposed:
            raise SessionLostError("mock driver disposed", kind="disposed", close_code=None)

    def _touch(self) -> None:
        """Count a port command; raise SessionLostError if dropped or dead; hang if scripted."""
        self._ensure_not_disposed()
        if not self._alive:
            raise SessionLostError("mock session lost", kind="disconnect", close_code=1006)

        counting = self._hang_after is not None or self._drop_after is not None
        if counting:
            self._commands += 1

        if self._hang_after is not None and self._commands >= self._hang_after:
            self._hang_after = None
            blocker = self._hang_block
            self._hang_block = None
            if blocker is not None:
                blocker()
            return

        if self._drop_after is not None and self._commands >= self._drop_after:
            self._alive = False
            self._drop_after = None
            raise SessionLostError(
                "mock session dropped by fault injection",
                kind="fault_inject",
                close_code=1006,
            )

    def _query(self, locator: Locator) -> list[MockNode]:
        compiled = self.compile(locator)
        now = self._clock()
        matches: list[MockNode] = []
        for node in self.scene.all_nodes():
            if not node.is_visible(now=now):
                continue
            if compiled.scope and compiled.scope not in (node.path, node.id, node.name):
                # Scope filters to descendants of a named ancestor when path contains it.
                if compiled.scope not in node.path:
                    continue
            if _matches(node, compiled):
                matches.append(node)
        return matches


def _matches(node: MockNode, query: MockNativeQuery) -> bool:
    if query.by is LocatorStrategy.ID:
        return node.id == query.value
    if query.by is LocatorStrategy.NAME:
        return node.name == query.value
    if query.by is LocatorStrategy.PATH:
        return node.path == query.value or node.path.endswith(query.value)
    if query.by is LocatorStrategy.TEXT:
        return node.text == query.value
    if query.by is LocatorStrategy.COMPONENT:
        return node.component == query.value
    return False


def _parse_budget(budget: str) -> BudgetKind:
    if budget not in ("probe", "deadline"):
        raise AuthoringError(f"budget must be 'probe' or 'deadline', got {budget!r}")
    return budget  # type: ignore[return-value]
