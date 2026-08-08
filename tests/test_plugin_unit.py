"""In-process coverage for plugin helpers (pytester subprocesses do not feed cov)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from questline.authoring import plugin as pl
from questline.authoring.assertions import expect
from questline.authoring.context import Context
from questline.core.events import EventBus
from questline.core.waits import WaitPolicy
from questline.drivers.handle import DriverHandle
from questline.drivers.mock import MockDriver


def test_feature_id_for_item_variants() -> None:
    item = MagicMock()
    item.get_closest_marker.return_value = None
    assert pl.feature_id_for_item(item) is None

    item.get_closest_marker.return_value = SimpleNamespace(args=("shop",), kwargs={})
    assert pl.feature_id_for_item(item) == "shop"

    item.get_closest_marker.return_value = SimpleNamespace(args=(), kwargs={"id": "hud"})
    assert pl.feature_id_for_item(item) == "hud"

    item.get_closest_marker.return_value = SimpleNamespace(args=(), kwargs={"value": "x"})
    assert pl.feature_id_for_item(item) == "x"

    item.get_closest_marker.return_value = SimpleNamespace(args=(), kwargs={"name": "y"})
    assert pl.feature_id_for_item(item) == "y"

    item.get_closest_marker.return_value = SimpleNamespace(args=(), kwargs={})
    assert pl.feature_id_for_item(item) is None


def test_questline_active_and_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = MagicMock()
    config.getoption.side_effect = lambda name, default=None: {
        "--questline-profile": None,
        "--questline-config": None,
        "--questline-quarantine": None,
    }.get(name, default)
    config.rootpath = tmp_path
    monkeypatch.delenv("QUESTLINE_PROFILE", raising=False)
    assert pl.questline_active(config) is False

    config.getoption.side_effect = lambda name, default=None: {
        "--questline-profile": "mock",
        "--questline-config": None,
        "--questline-quarantine": str(tmp_path / "q.yaml"),
    }.get(name, default)
    assert pl.questline_active(config) is True
    assert pl.quarantine_path_from_config(config) == tmp_path / "q.yaml"

    monkeypatch.setenv("QUESTLINE_PROFILE", "ci")
    config.getoption.side_effect = lambda name, default=None: {
        "--questline-profile": None,
        "--questline-config": None,
        "--questline-quarantine": None,
    }.get(name, default)
    assert pl.questline_active(config) is True
    assert pl.quarantine_path_from_config(config) == tmp_path / "quarantine.yaml"


def test_collection_modifyitems_filters() -> None:
    config = MagicMock()
    config.getoption.side_effect = lambda name, default=None: {
        "--include-quarantined": False,
        "questline_feature": "shop",
    }.get(name, default)

    def _item(markers: dict[str, object]) -> MagicMock:
        it = MagicMock()
        it.get_closest_marker.side_effect = lambda n: markers.get(n)
        return it

    keep = _item({"feature": SimpleNamespace(args=("shop",), kwargs={})})
    drop_q = _item(
        {
            "quest_quarantined": SimpleNamespace(args=(), kwargs={}),
            "feature": SimpleNamespace(args=("shop",), kwargs={}),
        }
    )
    drop_feat = _item({"feature": SimpleNamespace(args=("hud",), kwargs={})})
    items = [keep, drop_q, drop_feat]
    pl.pytest_collection_modifyitems(config, items)
    assert items == [keep]
    config.hook.pytest_deselected.assert_called()


def test_profile_custom_markers(tmp_path: Path) -> None:
    cfg = tmp_path / "questline.toml"
    cfg.write_text(
        "[profile.mock]\n"
        'driver = "mock"\n'
        'markers = ["quest_demo"]\n',
        encoding="utf-8",
    )
    marks = pl._profile_custom_markers(tmp_path, "mock", cfg)
    assert ("quest_demo", "custom marker from profile 'mock'") in marks
    assert pl._profile_custom_markers(tmp_path, "mock", tmp_path / "missing.toml") == []

    cfg2 = tmp_path / "questline2.toml"
    cfg2.write_text(
        "[profile.mock]\n"
        'markers = [{name = "quest_nightly", description = "night"}]\n',
        encoding="utf-8",
    )
    marks2 = pl._profile_custom_markers(tmp_path, "mock", cfg2)
    assert ("quest_nightly", "night") in marks2


def test_uses_questline_and_fixture_value() -> None:
    item = MagicMock()
    item.fixturenames = ["questline_ctx"]
    assert pl._uses_questline(item) is True
    item.fixturenames = ["tmp_path"]
    assert pl._uses_questline(item) is False

    item.funcargs = {"questline_bus": "bus"}
    assert pl._fixture_value(item, "questline_bus") == "bus"


def test_lazy_package_exports() -> None:
    import questline.authoring as auth

    assert auth.expect is expect
    assert auth.Context is Context
    assert callable(auth.Scenario)
    with pytest.raises(AttributeError):
        _ = auth.not_a_real_export  # type: ignore[attr-defined]


def test_load_session_ledger(tmp_path: Path) -> None:
    q = tmp_path / "quarantine.yaml"
    q.write_text("version: 1\nentries: []\n", encoding="utf-8")
    config = MagicMock()
    config.getoption.return_value = str(q)
    config.rootpath = tmp_path
    ledger = pl.load_session_ledger(config)
    assert ledger.entries() == []


def test_wire_driver_handle_mock() -> None:
    from questline.core.config import Settings

    handle = pl.wire_driver_handle(Settings(driver="mock"))
    assert handle.is_alive()
    handle.disconnect()


def test_wire_driver_handle_unknown() -> None:
    from questline.core.config import Settings
    from questline.core.errors import AuthoringError

    with pytest.raises(AuthoringError, match="not available"):
        pl.wire_driver_handle(Settings(driver="poco"))


def test_wire_driver_handle_alttester_android(monkeypatch: pytest.MonkeyPatch) -> None:
    from questline.core.config import Settings
    from questline.devices.port import Device
    from questline.drivers.alttester import AltTesterDriver
    from questline.drivers.alttester.fake import fake_transport_factory

    factory = fake_transport_factory()

    import questline.drivers.alttester as altmod

    monkeypatch.setattr(
        altmod, "AltTesterDriver", lambda: AltTesterDriver(transport_factory=factory)
    )

    settings = Settings(
        driver="alttester",
        target_host="127.0.0.1",
        target_port=13000,
        target_platform="android",
        target_app_name="__default__",
    )
    bundle = {"device": Device(id="emulator-5554", platform="android"), "provider": None}
    handle = pl.wire_driver_handle(settings, bundle)
    assert handle.is_alive()
    handle.disconnect()


def test_handle_optional_then_steps() -> None:
    from questline.authoring.steps import HandleOptional, Tap
    from questline.drivers.locators import Locator, LocatorStrategy
    from questline.drivers.mock.scene import MockNode, MockScene
    from questline.drivers.port import ConnectionTarget

    scene = MockScene()
    pop = MockNode(id="pop", name="P", visible=True)
    btn = MockNode(id="btn", name="B", visible=True)
    scene.add(pop)
    scene.add(btn)
    seen: list[str] = []
    btn.on_tap = lambda: seen.append("btn")
    pop.on_tap = lambda: seen.append("pop")
    driver = MockDriver(scene)
    driver.connect(ConnectionTarget())
    ctx = Context(
        driver=DriverHandle(driver),
        bus=EventBus(),
        run_id="r",
        test_id="t",
        wait_policy=WaitPolicy(probe=0.05, deadline=0.2, interval=0.01),
    )
    HandleOptional(
        Locator(by=LocatorStrategy.ID, value="pop"),
        Tap(Locator(by=LocatorStrategy.ID, value="btn"), budget="probe"),
        lambda c: seen.append("lambda"),
    ).execute(ctx)
    assert "btn" in seen
    assert "lambda" in seen
