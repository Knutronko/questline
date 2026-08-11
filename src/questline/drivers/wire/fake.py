"""In-memory / local fake Wire transport for CI (no Unity)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from questline.core.errors import AuthoringError, SessionLostError, TestError
from questline.drivers.port import ConnectionTarget
from questline.drivers.wire.driver import QuestlineDriver
from questline.drivers.wire.protocol import PROTOCOL_VERSION


class FakeWireTransport:
    """Speaks the Wire ops in-process with a tiny hook registry."""

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
        self._scene = "FakeWireScene"
        self._perf_sample = {
            "fps": 60.0,
            "allocated_mb": 128.0,
            "draw_calls": 42.0,
        }

    def request(self, op: str, params: dict[str, Any] | None = None) -> Any:
        if self._closed:
            raise SessionLostError("fake wire closed", kind="disposed")
        params = params or {}
        if op == "hello":
            return {
                "protocol_version": PROTOCOL_VERSION,
                "companion_version": "0.1.0",
                "scene": self._scene,
            }
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
        raise AuthoringError(f"unknown op: {op}")

    def close(self) -> None:
        self._closed = True


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
