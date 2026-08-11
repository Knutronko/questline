"""QuestlineDriver — DriverPort adapter over QuestlineWire (ADR-0005 / ADR-0008)."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal

from questline.core.errors import AuthoringError, ElementNotFoundError, SessionLostError
from questline.core.waits import WaitPolicy, wait_for
from questline.drivers.hooks import (
    HookManifestEntry,
    decode_invoke_result,
    parse_hooks_manifest,
)
from questline.drivers.locators import Locator, LocatorStrategy
from questline.drivers.port import (
    AppState,
    ConnectionTarget,
    Element,
    GameHook,
    HierarchySnapshot,
    Point,
)
from questline.drivers.wire.codec import (
    element_from_dict,
    hierarchy_from_dict,
    png_from_result,
)
from questline.drivers.wire.errors import (
    deferred_gesture_not_implemented,
    map_wire_error,
    ui_not_supported,
)
from questline.drivers.wire.protocol import hello_advertises_ui
from questline.drivers.wire.transport import WireTransport, connect_real_transport

BudgetKind = Literal["probe", "deadline"]
TransportFactory = Callable[[ConnectionTarget], WireTransport]

SUPPORTED_PLATFORMS = frozenset({"editor", "standalone_exe", "android", "standalone"})


@dataclass(frozen=True, slots=True)
class WireNativeQuery:
    """Compiled Locator for QuestlineWire find / find_all params."""

    by: LocatorStrategy
    value: str
    scope: str | None = None

    def to_params(self) -> dict[str, Any]:
        params: dict[str, Any] = {"by": self.by.value, "value": self.value}
        if self.scope:
            params["scope"] = self.scope
        return params


class QuestlineDriver:
    """DriverPort implementation backed by QuestlineWire (or an injected transport)."""

    def __init__(
        self,
        *,
        transport_factory: TransportFactory | None = None,
        clock: Callable[[], float] = time.monotonic,
        sleeper: Callable[[float], None] = time.sleep,
        rehandshake_delay_s: float = 0.5,
    ) -> None:
        self._transport_factory = transport_factory or connect_real_transport
        self._clock = clock
        self._sleeper = sleeper
        self._rehandshake_delay_s = rehandshake_delay_s
        self._transport: WireTransport | None = None
        self._target: ConnectionTarget | None = None
        self._alive = False
        self._disposed = False
        self._commands = 0
        self._drop_after: int | None = None
        self._manifest_by_name: dict[str, HookManifestEntry] = {}
        self._ui_supported = False
        self._hello: dict[str, Any] = {}

    def force_disconnect(self) -> None:
        """Simulate an abrupt session drop without a clean stop()."""
        self._alive = False

    def drop_after_commands(self, n: int) -> None:
        if n < 1:
            raise AuthoringError("drop_after_commands requires n >= 1")
        self._drop_after = n
        self._commands = 0

    def connect(self, target: ConnectionTarget) -> None:
        self._ensure_not_disposed()
        platform = (target.platform or "editor").lower()
        if platform not in SUPPORTED_PLATFORMS:
            raise AuthoringError(
                f"unsupported QuestlineWire platform {platform!r}; "
                f"expected one of {sorted(SUPPORTED_PLATFORMS)}"
            )
        normalized = ConnectionTarget(
            host=target.host,
            port=target.port,
            platform=platform if platform != "standalone" else "standalone_exe",
            app_id=target.app_id,
            extras=dict(target.extras),
        )
        try:
            self._transport = self._transport_factory(normalized)
        except Exception as exc:
            raise map_wire_error(exc) from exc
        self._target = normalized
        self._alive = True
        self._commands = 0
        self._refresh_hello()

    def disconnect(self) -> None:
        transport = self._transport
        self._transport = None
        self._alive = False
        self._disposed = True
        self._target = None
        self._ui_supported = False
        self._hello = {}
        if transport is not None:
            try:
                transport.close()
            except Exception:
                pass

    def is_alive(self) -> bool:
        return self._alive and self._transport is not None and not self._disposed

    def find(
        self,
        locator: Locator,
        policy: WaitPolicy | None = None,
        *,
        budget: str = "deadline",
    ) -> Element:
        self._touch()
        self._require_ui()
        kind = _parse_budget(budget)
        query = self.compile(locator)

        if policy is None:
            return self._find_once(query)

        seconds = policy.probe if kind == "probe" else policy.deadline
        wait_policy = WaitPolicy(probe=policy.probe, deadline=seconds, interval=policy.interval)

        def condition() -> Element | bool:
            self._touch()
            try:
                return self._find_once(query)
            except ElementNotFoundError:
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
        self._require_ui()
        transport = self._require_transport()
        query = self.compile(locator)
        try:
            raw = transport.request("find_all", query.to_params())
        except Exception as exc:
            raise map_wire_error(exc) from exc
        if not isinstance(raw, dict):
            raise AuthoringError("find_all result must be an object")
        elements = raw.get("elements")
        if not isinstance(elements, list):
            raise AuthoringError("find_all.elements must be an array")
        return [element_from_dict(item) for item in elements]

    def hierarchy(self) -> HierarchySnapshot:
        self._touch()
        self._require_ui()
        transport = self._require_transport()
        try:
            raw = transport.request("hierarchy", {})
        except Exception as exc:
            raise map_wire_error(exc) from exc
        return hierarchy_from_dict(raw)

    def screenshot(self) -> bytes:
        self._touch()
        self._require_ui()
        transport = self._require_transport()
        try:
            raw = transport.request("screenshot", {})
        except Exception as exc:
            raise map_wire_error(exc) from exc
        return png_from_result(raw)

    def tap(self, target: Element | Point) -> None:
        self._touch()
        self._require_ui()
        transport = self._require_transport()
        if isinstance(target, Point):
            params: dict[str, Any] = {"point": {"x": target.x, "y": target.y}}
        else:
            params = {"element_id": target.id}
        try:
            transport.request("tap", params)
        except Exception as exc:
            raise map_wire_error(exc) from exc

    def press(self, target: Element | Point, duration: float = 0.1) -> None:
        _ = target, duration
        self._touch()
        raise deferred_gesture_not_implemented("press")

    def swipe(
        self, start: Element | Point, end: Element | Point, duration: float = 0.2
    ) -> None:
        _ = start, end, duration
        self._touch()
        raise deferred_gesture_not_implemented("swipe")

    def text_input(self, element: Element, text: str, *, clear: bool = True) -> None:
        _ = element, text, clear
        self._touch()
        raise deferred_gesture_not_implemented("text_input")

    def call_game_method(self, hook: GameHook, *args: Any) -> Any:
        self._touch()
        transport = self._require_transport()
        params = {"name": hook.name, "args": list(args)}
        try:
            raw = transport.request("call_hook", params)
        except Exception as exc:
            raise map_wire_error(exc) from exc
        value = raw
        if isinstance(raw, dict) and "value" in raw:
            value = raw["value"]
        result = decode_invoke_result(value)
        if self._hook_causes_soft_reload(hook):
            self._rehandshake()
        return result

    def app_state(self) -> AppState:
        self._touch()
        transport = self._require_transport()
        try:
            raw = transport.request("app_state")
        except Exception as exc:
            raise map_wire_error(exc) from exc
        if not isinstance(raw, dict):
            raise AuthoringError("app_state result must be an object")
        return AppState(
            foreground=bool(raw.get("foreground", True)),
            scene=raw.get("scene") if isinstance(raw.get("scene"), str) else None,
            paused=bool(raw.get("paused", False)),
        )

    def compile(self, locator: Locator) -> WireNativeQuery:
        return WireNativeQuery(by=locator.by, value=locator.value, scope=locator.scope)

    def hooks_manifest(self) -> list[HookManifestEntry]:
        """Fetch the companion QuestlineHooks registry dump over Wire."""
        self._touch()
        transport = self._require_transport()
        try:
            raw = transport.request("hooks_manifest")
        except Exception as exc:
            raise map_wire_error(exc) from exc
        if not isinstance(raw, (str, dict, list)):
            raise AuthoringError(
                f"hooks_manifest must return JSON object/array, got {type(raw).__name__}"
            )
        entries = parse_hooks_manifest(raw)
        self._manifest_by_name = {e.name: e for e in entries}
        return entries

    def _find_once(self, query: WireNativeQuery) -> Element:
        transport = self._require_transport()
        try:
            raw = transport.request("find", query.to_params())
        except Exception as exc:
            raise map_wire_error(exc) from exc
        if not isinstance(raw, dict):
            raise AuthoringError("find result must be an object")
        return element_from_dict(raw.get("element"))

    def _refresh_hello(self) -> None:
        transport = self._require_transport()
        try:
            raw = transport.request("hello")
        except Exception as exc:
            raise map_wire_error(exc) from exc
        if not isinstance(raw, dict):
            raise AuthoringError("hello result must be an object")
        self._hello = raw
        self._ui_supported = hello_advertises_ui(raw)

    def _require_ui(self) -> None:
        if not self._ui_supported:
            raise ui_not_supported()

    def _hook_causes_soft_reload(self, hook: GameHook) -> bool:
        if hook.causes_soft_reload:
            return True
        entry = self._manifest_by_name.get(hook.name)
        return bool(entry and entry.causes_soft_reload)

    def _rehandshake(self) -> None:
        target = self._target
        if target is None:
            raise SessionLostError(
                "cannot re-handshake: no prior ConnectionTarget",
                kind="rehandshake",
                close_code=None,
            )
        transport = self._transport
        self._transport = None
        self._alive = False
        if transport is not None:
            try:
                transport.close()
            except Exception:
                pass
        if self._rehandshake_delay_s > 0:
            self._sleeper(self._rehandshake_delay_s)
        self._disposed = False
        self.connect(target)

    def _ensure_not_disposed(self) -> None:
        if self._disposed:
            raise SessionLostError(
                "questline wire driver disposed",
                kind="disposed",
                close_code=None,
            )

    def _require_transport(self) -> WireTransport:
        if self._transport is None or not self._alive:
            raise SessionLostError(
                "questline wire session not connected",
                kind="disconnect",
                close_code=None,
            )
        return self._transport

    def _touch(self) -> None:
        self._ensure_not_disposed()
        if not self._alive or self._transport is None:
            raise SessionLostError(
                "questline wire session lost",
                kind="disconnect",
                close_code=None,
            )
        if self._drop_after is not None:
            self._commands += 1
            if self._commands >= self._drop_after:
                self._alive = False
                self._drop_after = None
                raise SessionLostError(
                    "questline wire session lost (fault injection)",
                    kind="fault_injection",
                    close_code=None,
                )


def _parse_budget(budget: str) -> BudgetKind:
    if budget not in ("probe", "deadline"):
        raise AuthoringError(f"budget must be 'probe' or 'deadline', got {budget!r}")
    return budget  # type: ignore[return-value]
