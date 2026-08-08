"""AltTesterDriver — DriverPort adapter over AltTester Python bindings."""

from __future__ import annotations

import tempfile
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal

from questline.core.errors import (
    AuthoringError,
    ElementNotFoundError,
    SessionLostError,
)
from questline.core.waits import WaitPolicy, wait_for
from questline.drivers.alttester.errors import map_alttester_error
from questline.drivers.alttester.hooks import (
    HOOKS_ASSEMBLY,
    HOOKS_TYPE_NAME,
    INVOKE_METHOD,
    MANIFEST_METHOD,
    HookManifestEntry,
    decode_invoke_result,
    encode_invoke_args,
    parse_hooks_manifest,
)
from questline.drivers.alttester.queries import AltNativeQuery, compile_locator
from questline.drivers.alttester.transport import (
    AltElementData,
    AltTransport,
    connect_real_transport,
)
from questline.drivers.locators import Locator
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

TransportFactory = Callable[[ConnectionTarget], AltTransport]

# Platforms accepted on ConnectionTarget.platform (android used in Phase 05).
SUPPORTED_PLATFORMS = frozenset({"editor", "standalone_exe", "android", "standalone"})


class AltTesterDriver:
    """DriverPort implementation backed by AltTester (or an injected transport)."""

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
        self._transport: AltTransport | None = None
        self._target: ConnectionTarget | None = None
        self._alive = False
        self._disposed = False
        self._commands = 0
        self._drop_after: int | None = None
        self._manifest_by_name: dict[str, HookManifestEntry] = {}

    # --- fault-injection hooks (unit / conformance with fake transport) ---

    def force_disconnect(self) -> None:
        """Simulate an abrupt session drop without a clean stop()."""
        self._alive = False

    def drop_after_commands(self, n: int) -> None:
        if n < 1:
            raise AuthoringError("drop_after_commands requires n >= 1")
        self._drop_after = n
        self._commands = 0

    # --- DriverPort ---

    def connect(self, target: ConnectionTarget) -> None:
        self._ensure_not_disposed()
        platform = (target.platform or "editor").lower()
        if platform not in SUPPORTED_PLATFORMS:
            raise AuthoringError(
                f"unsupported AltTester platform {platform!r}; "
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
            raise map_alttester_error(exc) from exc
        self._target = normalized
        self._alive = True
        self._commands = 0

    def disconnect(self) -> None:
        transport = self._transport
        self._transport = None
        self._alive = False
        self._disposed = True
        self._target = None
        if transport is not None:
            try:
                transport.stop()
            except Exception as exc:
                raise map_alttester_error(exc) from exc

    def is_alive(self) -> bool:
        return self._alive and not self._disposed and self._transport is not None

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
            return _to_element(matches[0])

        seconds = policy.probe if kind == "probe" else policy.deadline
        wait_policy = WaitPolicy(probe=policy.probe, deadline=seconds, interval=policy.interval)

        def condition() -> Element | bool:
            self._touch()
            matches = self._query(locator)
            if matches:
                return _to_element(matches[0])
            return False

        try:
            result = wait_for(
                condition,
                wait_policy,
                on_timeout="return_false",
                clock=self._clock,
                sleeper=self._sleeper,
            )
        except Exception as exc:
            raise map_alttester_error(exc) from exc
        if result is False:
            raise ElementNotFoundError(
                f"element not found within {kind} budget ({seconds}s): "
                f"{locator.by.value}={locator.value!r}"
            )
        return result  # type: ignore[return-value]

    def find_all(self, locator: Locator) -> list[Element]:
        self._touch()
        return [_to_element(e) for e in self._query(locator)]

    def hierarchy(self) -> HierarchySnapshot:
        self._touch()
        transport = self._require_transport()
        try:
            elements = transport.get_all_elements(enabled=True)
            scene = transport.get_current_scene()
        except Exception as exc:
            raise map_alttester_error(exc) from exc
        return _build_hierarchy(elements, scene=scene)

    def screenshot(self) -> bytes:
        self._touch()
        transport = self._require_transport()
        try:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                path = Path(tmp.name)
            try:
                transport.get_png_screenshot(str(path))
                data = path.read_bytes()
            finally:
                path.unlink(missing_ok=True)
        except Exception as exc:
            raise map_alttester_error(exc) from exc
        if not data:
            raise SessionLostError(
                "screenshot returned empty payload",
                kind="screenshot_empty",
                close_code=None,
            )
        return data

    def tap(self, target: Element | Point) -> None:
        self._touch()
        transport = self._require_transport()
        x, y = _resolve_point(target)
        try:
            transport.tap_xy(x, y)
        except Exception as exc:
            raise map_alttester_error(exc) from exc

    def press(self, target: Element | Point, duration: float = 0.1) -> None:
        self._touch()
        transport = self._require_transport()
        x, y = _resolve_point(target)
        try:
            transport.hold_xy(x, y, duration)
        except Exception as exc:
            raise map_alttester_error(exc) from exc

    def swipe(
        self,
        start: Element | Point,
        end: Element | Point,
        duration: float = 0.2,
    ) -> None:
        self._touch()
        transport = self._require_transport()
        sx, sy = _resolve_point(start)
        ex, ey = _resolve_point(end)
        try:
            transport.swipe_xy(sx, sy, ex, ey, duration)
        except Exception as exc:
            raise map_alttester_error(exc) from exc

    def text_input(self, element: Element, text: str, *, clear: bool = True) -> None:
        self._touch()
        transport = self._require_transport()
        # Clear is best-effort: set_text replaces content when clear=True.
        payload = text if clear else (element.text + text)
        data = AltElementData(
            id=element.id,
            name=element.name,
            text=element.text,
            enabled=element.enabled,
        )
        try:
            transport.set_text(data, payload, submit=False)
        except Exception as exc:
            raise map_alttester_error(exc) from exc

    def call_game_method(self, hook: GameHook, *args: Any) -> Any:
        self._touch()
        transport = self._require_transport()
        try:
            raw = transport.call_static_method(
                HOOKS_TYPE_NAME,
                INVOKE_METHOD,
                HOOKS_ASSEMBLY,
                parameters=[hook.name, encode_invoke_args(args)],
                type_of_parameters=["System.String", "System.String"],
            )
        except Exception as exc:
            raise map_alttester_error(exc) from exc
        result = decode_invoke_result(raw)
        if self._hook_causes_soft_reload(hook):
            self._rehandshake()
        return result

    def app_state(self) -> AppState:
        self._touch()
        transport = self._require_transport()
        try:
            scene = transport.get_current_scene()
        except Exception as exc:
            raise map_alttester_error(exc) from exc
        return AppState(foreground=True, scene=scene, paused=False)

    def compile(self, locator: Locator) -> AltNativeQuery:
        return compile_locator(locator)

    def hooks_manifest(self) -> list[HookManifestEntry]:
        """Fetch the companion QuestlineHooks registry dump (addendum §5.3)."""
        self._touch()
        transport = self._require_transport()
        try:
            raw = transport.call_static_method(
                HOOKS_TYPE_NAME,
                MANIFEST_METHOD,
                HOOKS_ASSEMBLY,
                parameters=[],
                type_of_parameters=[],
            )
        except Exception as exc:
            raise map_alttester_error(exc) from exc
        if not isinstance(raw, (str, dict, list)):
            raise AuthoringError(
                f"GetManifestJson must return JSON string or object, got {type(raw).__name__}"
            )
        entries = parse_hooks_manifest(raw)
        self._manifest_by_name = {e.name: e for e in entries}
        return entries

    # --- internals ---

    def _hook_causes_soft_reload(self, hook: GameHook) -> bool:
        if hook.causes_soft_reload:
            return True
        entry = self._manifest_by_name.get(hook.name)
        return bool(entry and entry.causes_soft_reload)

    def _rehandshake(self) -> None:
        """Reconnect after a soft-reload hook so the next step has a live session."""
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
                transport.stop()
            except Exception:
                pass
        if self._rehandshake_delay_s > 0:
            self._sleeper(self._rehandshake_delay_s)
        # connect() marks disposed-check; we are not disposed — only session dropped.
        self._disposed = False
        self.connect(target)

    def _ensure_not_disposed(self) -> None:
        if self._disposed:
            raise SessionLostError(
                "alttester driver disposed",
                kind="disposed",
                close_code=None,
            )

    def _require_transport(self) -> AltTransport:
        if self._transport is None or not self._alive:
            raise SessionLostError(
                "alttester session lost",
                kind="disconnect",
                close_code=None,
            )
        return self._transport

    def _touch(self) -> None:
        self._ensure_not_disposed()
        if not self._alive or self._transport is None:
            raise SessionLostError(
                "alttester session lost",
                kind="disconnect",
                close_code=None,
            )
        if self._drop_after is not None:
            self._commands += 1
            if self._commands >= self._drop_after:
                self._alive = False
                self._drop_after = None
                raise SessionLostError(
                    "alttester session dropped by fault injection",
                    kind="fault_inject",
                    close_code=1006,
                )

    def _query(self, locator: Locator) -> list[AltElementData]:
        transport = self._require_transport()
        compiled = self.compile(locator)
        try:
            found = transport.find_objects(compiled.by, compiled.value, enabled=True)
        except Exception as exc:
            mapped = map_alttester_error(exc)
            if isinstance(mapped, ElementNotFoundError):
                return []
            raise mapped from exc
        if compiled.scope:
            found = [e for e in found if _in_scope(e, compiled.scope)]
        return found


def _to_element(data: AltElementData) -> Element:
    path = data.attrs.get("path", "")
    return Element(
        id=data.id,
        name=data.name,
        path=path,
        text=data.text,
        visible=True,
        enabled=data.enabled,
        component=data.type or None,
        bounds=(data.x, data.y, 0.0, 0.0),
        attrs=dict(data.attrs),
    )


def _resolve_point(target: Element | Point) -> tuple[float, float]:
    if isinstance(target, Point):
        return target.x, target.y
    if target.bounds is not None:
        x, y, w, h = target.bounds
        return x + w / 2.0, y + h / 2.0
    return 0.0, 0.0


def _in_scope(element: AltElementData, scope: str) -> bool:
    path = element.attrs.get("path", "")
    return scope in (element.id, element.name, path) or scope in path


def _build_hierarchy(elements: list[AltElementData], *, scene: str | None) -> HierarchySnapshot:
    by_tid: dict[int, AltElementData] = {}
    children: dict[int, list[int]] = {}
    for el in elements:
        tid = el.transform_id or _stable_tid(el)
        by_tid[tid] = el
        children.setdefault(tid, [])
    root_ids: list[int] = []
    for el in elements:
        tid = el.transform_id or _stable_tid(el)
        parent = el.transform_parent_id
        if parent and parent in by_tid:
            children.setdefault(parent, []).append(tid)
        else:
            root_ids.append(tid)

    def build(tid: int) -> HierarchyNode:
        el = by_tid[tid]
        kids = tuple(build(cid) for cid in children.get(tid, []) if cid in by_tid)
        return HierarchyNode(element=_to_element(el), children=kids)

    # Deduplicate root ids while preserving order.
    seen: set[int] = set()
    roots: list[HierarchyNode] = []
    for rid in root_ids:
        if rid in seen or rid not in by_tid:
            continue
        seen.add(rid)
        roots.append(build(rid))
    return HierarchySnapshot(roots=tuple(roots), scene=scene)


def _stable_tid(el: AltElementData) -> int:
    if el.transform_id:
        return el.transform_id
    return abs(hash(el.id)) % (10**9) or 1


def _parse_budget(budget: str) -> BudgetKind:
    if budget not in ("probe", "deadline"):
        raise AuthoringError(f"budget must be 'probe' or 'deadline', got {budget!r}")
    return budget  # type: ignore[return-value]
