"""Typed key-value context flowing between steps (architecture §4)."""

from __future__ import annotations

from typing import Any

from questline.core.errors import AuthoringError
from questline.core.events import EventBus
from questline.core.waits import WaitPolicy
from questline.drivers.handle import DriverHandle


class Context:
    """Per-test runtime bag: driver handle, wait policy, event ids, and saved data."""

    def __init__(
        self,
        *,
        driver: DriverHandle,
        bus: EventBus,
        run_id: str,
        test_id: str,
        wait_policy: WaitPolicy,
        data: dict[str, Any] | None = None,
    ) -> None:
        self.driver = driver
        self.bus = bus
        self.run_id = run_id
        self.test_id = test_id
        self.wait_policy = wait_policy
        self._data: dict[str, Any] = dict(data or {})

    def save(self, key: str, value: Any) -> Any:
        """Store *value* under *key* and return it (convenient for inline callables)."""
        if not key:
            raise AuthoringError("Context.save requires a non-empty key")
        self._data[key] = value
        return value

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def __getitem__(self, key: str) -> Any:
        try:
            return self._data[key]
        except KeyError as exc:
            raise AuthoringError(
                f"Context key {key!r} is not set. "
                "Save it in an earlier step with ctx.save(...) or Save(...)."
            ) from exc

    def __contains__(self, key: object) -> bool:
        return key in self._data

    def keys(self) -> list[str]:
        return list(self._data.keys())

    def as_dict(self) -> dict[str, Any]:
        return dict(self._data)
