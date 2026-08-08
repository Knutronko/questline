"""In-process session fixture coverage for the authoring plugin."""

from __future__ import annotations

import pytest

from questline.authoring.assertions import expect
from questline.core.store import RunStore


@pytest.mark.feature("inprocess")
def test_questline_ctx_and_store_inprocess(
    questline_ctx,
    questline_store: RunStore,
    questline_run_id: str,
    driver_handle,
) -> None:
    assert questline_ctx.run_id == questline_run_id
    assert questline_ctx.test_id
    assert driver_handle.is_alive()
    expect(1).equals(1).evaluate()
    # Store should already have RunStarted from the session fixture.
    run = questline_store.get_run(questline_run_id)
    assert run is not None
    assert run["status"] == "running"


def test_questline_settings_mock_profile(questline_settings) -> None:
    assert questline_settings.driver == "mock"
