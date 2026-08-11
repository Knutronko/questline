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


def test_wire_driver_handle_questline(monkeypatch: pytest.MonkeyPatch) -> None:
    import questline.drivers.wire as wiremod
    from questline.core.config import Settings
    from questline.drivers.wire import QuestlineDriver
    from questline.drivers.wire.fake import fake_transport_factory

    monkeypatch.setattr(
        wiremod,
        "QuestlineDriver",
        lambda: QuestlineDriver(
            transport_factory=fake_transport_factory(state={}),
            rehandshake_delay_s=0.0,
            sleeper=lambda _s: None,
        ),
    )
    settings = Settings(
        driver="questline",
        target_host="127.0.0.1",
        target_port=13000,
        target_platform="editor",
    )
    handle = pl.wire_driver_handle(settings)
    assert handle.is_alive()
    assert handle.app_state().foreground is True
    handle.disconnect()


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


def test_attach_session_reporters_and_seal(tmp_path: Path) -> None:
    """In-process coverage for reporter attach + run seal helpers."""
    from _pytest.stash import Stash

    from questline.core.config import Settings
    from questline.core.events import EventBus, RunStarted
    from questline.core.store import RunStore
    from questline.reporters.html import HtmlReporter

    settings = Settings(
        profile="ci",
        driver="mock",
        device="local",
        reporters=["console", "html"],
        store_dir=tmp_path / ".questline",
    )
    bus = EventBus()
    store = RunStore(
        settings.store_db,
        artifacts_dir=settings.artifacts_dir,
        ledger_path=settings.ledger_path,
    )
    store.attach(bus)

    config = MagicMock()
    config.stash = Stash()
    config.pluginmanager.get_plugin.return_value = SimpleNamespace(stats={})

    reporters = pl.attach_session_reporters(settings, bus, store, config)
    assert len(reporters) == 2
    assert config.stash[pl._STASH_REPORTERS] is reporters

    run_id = "r-seal"
    bus.publish(RunStarted(run_id=run_id, profile=settings.profile))
    pl.seal_session_run(
        settings=settings,
        bus=bus,
        store=store,
        reporters=reporters,
        pytestconfig=config,
        run_id=run_id,
        t0=0.0,
        watchdog=SimpleNamespace(fired=False),
    )
    assert store.get_run(run_id)["status"] == "passed"
    html = next(r for r in reporters if isinstance(r, HtmlReporter))
    assert html.last_path is not None
    assert html.last_path.is_file()
    store.close()


def test_seal_session_run_failed_and_watchdog_skip(tmp_path: Path) -> None:
    from _pytest.stash import Stash

    from questline.core.config import Settings
    from questline.core.events import EventBus, RunStarted
    from questline.core.store import RunStore

    settings = Settings(
        profile="ci",
        driver="mock",
        reporters=["console"],
        store_dir=tmp_path / ".questline",
    )
    bus = EventBus()
    store = RunStore(
        settings.store_db,
        artifacts_dir=settings.artifacts_dir,
        ledger_path=settings.ledger_path,
    )
    store.attach(bus)
    config = MagicMock()
    config.stash = Stash()
    config.pluginmanager.get_plugin.return_value = SimpleNamespace(
        stats={"failed": ["t"]}
    )
    reporters = pl.attach_session_reporters(settings, bus, store, config)

    run_id = "r-fail"
    bus.publish(RunStarted(run_id=run_id, profile="ci"))
    pl.seal_session_run(
        settings=settings,
        bus=bus,
        store=store,
        reporters=reporters,
        pytestconfig=config,
        run_id=run_id,
        t0=0.0,
        watchdog=SimpleNamespace(fired=False),
    )
    assert store.get_run(run_id)["status"] == "failed"

    run_id2 = "r-wd"
    bus.publish(RunStarted(run_id=run_id2, profile="ci"))
    pl.seal_session_run(
        settings=settings,
        bus=bus,
        store=store,
        reporters=reporters,
        pytestconfig=config,
        run_id=run_id2,
        t0=0.0,
        watchdog=SimpleNamespace(fired=True),
    )
    assert store.get_run(run_id2)["status"] == "running"
    store.close()


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


def test_perf_helpers_attach_start_stop(tmp_path: Path) -> None:
    """In-process coverage for PerfProbe plugin helpers (authoring gate)."""
    from _pytest.stash import Stash

    from questline.core.config import PerfSettings, Settings
    from questline.core.events import EventBus
    from questline.core.store import RunStore
    from questline.drivers.port import ConnectionTarget
    from questline.drivers.wire.fake import FakeWireDriverHarness
    from questline.perf.asserts import clear_perf_context

    settings = Settings(
        driver="questline",
        target_platform="editor",
        store_dir=tmp_path / ".questline",
        perf=PerfSettings(enabled=True, interval_s=0.5, scope="test", source="companion"),
    )
    bus = EventBus()
    store = RunStore(
        settings.store_db,
        artifacts_dir=settings.artifacts_dir,
        ledger_path=settings.ledger_path,
    )
    store.attach(bus)
    harness = FakeWireDriverHarness()
    driver = harness()
    driver.connect(ConnectionTarget(host="127.0.0.1", port=13000, platform="editor"))
    handle = DriverHandle(driver)

    config = MagicMock()
    config.stash = Stash()
    probe = pl._attach_perf_to_session(
        settings=settings,
        bus=bus,
        store=store,
        run_id="run-perf",
        handle=handle,
        device_bundle=None,
        pytestconfig=config,
    )
    assert probe is not None
    assert config.stash[pl._STASH_PERF_PROBE] is probe

    pl._perf_bind_test_context(
        store=store, bus=bus, run_id="run-perf", test_id="t::perf"
    )
    item = MagicMock()
    item.nodeid = "t::perf"
    pl._perf_on_test_start(item=item, probe=probe, settings=settings)
    assert probe.running
    pl._perf_on_test_finish(probe=probe, settings=settings)
    assert not probe.running

    # No-op paths
    pl._perf_on_test_start(item=item, probe=None, settings=settings)
    pl._perf_on_test_finish(probe=None, settings=settings)

    pl._detach_perf_from_session(probe)
    clear_perf_context()
    handle.disconnect()
    store.close()


def test_perf_helpers_run_scope_starts_immediately(tmp_path: Path) -> None:
    from _pytest.stash import Stash

    from questline.core.config import PerfSettings, Settings
    from questline.core.events import EventBus
    from questline.core.store import RunStore
    from questline.drivers.port import ConnectionTarget
    from questline.drivers.wire.fake import FakeWireDriverHarness

    settings = Settings(
        driver="questline",
        target_platform="editor",
        store_dir=tmp_path / ".questline",
        perf=PerfSettings(enabled=True, scope="run", source="companion"),
    )
    bus = EventBus()
    store = RunStore(settings.store_db, artifacts_dir=settings.artifacts_dir)
    store.attach(bus)
    driver = FakeWireDriverHarness()()
    driver.connect(ConnectionTarget(host="127.0.0.1", port=13000, platform="editor"))
    handle = DriverHandle(driver)
    config = MagicMock()
    config.stash = Stash()
    probe = pl._attach_perf_to_session(
        settings=settings,
        bus=bus,
        store=store,
        run_id="run-scope",
        handle=handle,
        device_bundle=None,
        pytestconfig=config,
    )
    assert probe is not None and probe.running
    pl._detach_perf_from_session(probe)
    handle.disconnect()
    store.close()
