"""Context key-value store for step data flow."""

from __future__ import annotations

import pytest

from questline.authoring.context import Context
from questline.core.errors import AuthoringError
from questline.core.events import EventBus
from questline.core.waits import WaitPolicy
from questline.drivers.handle import DriverHandle
from questline.drivers.mock import MockDriver


def _ctx() -> Context:
    return Context(
        driver=DriverHandle(MockDriver()),
        bus=EventBus(),
        run_id="run",
        test_id="test",
        wait_policy=WaitPolicy(probe=0.1, deadline=1.0, interval=0.05),
    )


def test_save_get_and_missing_key() -> None:
    ctx = _ctx()
    ctx.save("coins", 10)
    assert ctx["coins"] == 10
    assert ctx.get("missing") is None
    assert "coins" in ctx
    assert ctx.keys() == ["coins"]
    assert ctx.as_dict() == {"coins": 10}
    with pytest.raises(AuthoringError, match="not set"):
        _ = ctx["missing"]
    with pytest.raises(AuthoringError, match="non-empty"):
        ctx.save("", 1)
