"""pytest plugin — profile → DriverHandle → store; markers; quarantine; feature filter."""

from __future__ import annotations

import os
import time
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from questline.authoring.context import Context
    from questline.authoring.quarantine import QuarantineLedger
    from questline.core.config import Settings
    from questline.core.events import EventBus
    from questline.core.store import RunStore
    from questline.drivers.handle import DriverHandle

_STASH_RUN_ID = pytest.StashKey[str]()
_STASH_RUN_T0 = pytest.StashKey[float]()
_STASH_WATCHDOG = pytest.StashKey[Any]()
_STASH_RECOVERY = pytest.StashKey[Any]()


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("questline", "questline authoring")
    group.addoption(
        "--questline-profile",
        action="store",
        default=None,
        help="Profile name from questline.toml (overrides QUESTLINE_PROFILE)",
    )
    group.addoption(
        "--questline-config",
        action="store",
        default=None,
        help="Path to questline.toml",
    )
    group.addoption(
        "--include-quarantined",
        action="store_true",
        default=False,
        help="Run tests marked quest_quarantined (excluded by default)",
    )
    group.addoption(
        "--feature",
        action="store",
        default=None,
        dest="questline_feature",
        help="Only collect tests tagged with feature=<id>",
    )
    group.addoption(
        "--questline-quarantine",
        action="store",
        default=None,
        help="Path to quarantine.yaml (default: <root>/quarantine.yaml)",
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "quest_smoke: smoke-suite marker (alias: quest.smoke)")
    config.addinivalue_line(
        "markers", "quest_regression: regression-suite marker (alias: quest.regression)"
    )
    config.addinivalue_line(
        "markers",
        "quest_quarantined: excluded by default; run with --include-quarantined",
    )
    config.addinivalue_line(
        "markers",
        "feature(id): optional feature-pipeline id stored on the test result",
    )


def pytest_collection_modifyitems(
    config: pytest.Config,
    items: list[pytest.Item],
) -> None:
    include_q = bool(config.getoption("--include-quarantined"))
    feature_filter = config.getoption("questline_feature")

    kept: list[pytest.Item] = []
    deselected: list[pytest.Item] = []
    for item in items:
        if not include_q and item.get_closest_marker("quest_quarantined") is not None:
            deselected.append(item)
            continue
        if feature_filter:
            feat = feature_id_for_item(item)
            if feat != feature_filter:
                deselected.append(item)
                continue
        kept.append(item)

    if deselected:
        config.hook.pytest_deselected(items=deselected)
        items[:] = kept


def feature_id_for_item(item: pytest.Item) -> str | None:
    mark = item.get_closest_marker("feature")
    if mark is None:
        return None
    if mark.args:
        return str(mark.args[0])
    for key in ("id", "value", "name"):
        if key in mark.kwargs:
            return str(mark.kwargs[key])
    return None


def questline_active(config: pytest.Config) -> bool:
    if config.getoption("--questline-profile"):
        return True
    if config.getoption("--questline-config"):
        return True
    if os.environ.get("QUESTLINE_PROFILE"):
        return True
    return False


def quarantine_path_from_config(config: pytest.Config) -> Path:
    opt = config.getoption("--questline-quarantine")
    if opt:
        return Path(opt)
    return Path(config.rootpath) / "quarantine.yaml"


def load_session_ledger(config: pytest.Config) -> QuarantineLedger:
    from questline.authoring.quarantine import QuarantineLedger

    return QuarantineLedger.load(quarantine_path_from_config(config))


@pytest.fixture(scope="session")
def questline_settings(pytestconfig: pytest.Config) -> Settings:
    from questline.core.config import load_settings
    from questline.core.errors import AuthoringError

    profile = pytestconfig.getoption("--questline-profile")
    config_opt = pytestconfig.getoption("--questline-config")
    config_path = Path(config_opt) if config_opt else None
    root = Path(pytestconfig.rootpath)
    try:
        settings = load_settings(
            config_path=config_path,
            profile=profile,
            project_root=root,
        )
    except AuthoringError:
        if not questline_active(pytestconfig):
            return load_settings(project_root=root, profile="default")
        raise

    for name, desc in _profile_custom_markers(root, settings.profile, config_path):
        pytestconfig.addinivalue_line("markers", f"{name}: {desc}")
    return settings


def _profile_custom_markers(
    root: Path,
    profile: str,
    config_path: Path | None,
) -> list[tuple[str, str]]:
    import tomllib

    path = config_path if config_path is not None else root / "questline.toml"
    if not path.is_file():
        return []
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    table = (data.get("profile") or {}).get(profile) or {}
    raw = table.get("markers") or []
    out: list[tuple[str, str]] = []
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, str):
                out.append((item, f"custom marker from profile '{profile}'"))
            elif isinstance(item, dict) and "name" in item:
                out.append(
                    (str(item["name"]), str(item.get("description", "custom marker")))
                )
    return out


@pytest.fixture(scope="session")
def questline_bus() -> EventBus:
    from questline.core.events import EventBus

    return EventBus()


@pytest.fixture(scope="session")
def questline_store(
    questline_settings: Settings,
    questline_bus: EventBus,
) -> Any:
    from questline.core.store import RunStore

    store = RunStore(
        questline_settings.store_db,
        artifacts_dir=questline_settings.artifacts_dir,
        ledger_path=questline_settings.ledger_path,
    )
    store.attach(questline_bus)
    yield store
    store.close()


@pytest.fixture(scope="session")
def questline_run_id(
    questline_settings: Settings,
    questline_bus: EventBus,
    questline_store: RunStore,
    pytestconfig: pytest.Config,
) -> Any:
    from questline.core.events import RunFinished, RunStarted
    from questline.core.watchdog import Watchdog

    _ = questline_store
    run_id = str(uuid.uuid4())
    pytestconfig.stash[_STASH_RUN_ID] = run_id
    t0 = time.perf_counter()
    pytestconfig.stash[_STASH_RUN_T0] = t0
    questline_bus.publish(RunStarted(run_id=run_id, profile=questline_settings.profile))

    def _watchdog_exit(code: int) -> None:
        pytest.exit(f"questline watchdog fired (exit {code})", returncode=code)

    watchdog = Watchdog(
        timeout_s=questline_settings.resilience.watchdog_timeout_s,
        bus=questline_bus,
        run_id=run_id,
        exit_fn=_watchdog_exit,
    )
    pytestconfig.stash[_STASH_WATCHDOG] = watchdog
    watchdog.start()
    yield run_id
    watchdog.stop()
    if watchdog.fired:
        return
    status = "passed"
    tr = pytestconfig.pluginmanager.get_plugin("terminalreporter")
    if tr is not None and (tr.stats.get("failed") or tr.stats.get("error")):
        status = "failed"
    questline_bus.publish(
        RunFinished(
            run_id=run_id,
            status=status,
            duration_s=time.perf_counter() - t0,
        )
    )


def wire_driver_handle(
    settings: Settings,
    questline_device: Any = None,
) -> Any:
    """Build and connect a DriverHandle for *settings* (used by the session fixture)."""
    from questline.core.errors import AuthoringError
    from questline.drivers.handle import DriverHandle
    from questline.drivers.mock import MockDriver
    from questline.drivers.port import ConnectionTarget, DriverPort

    driver_name = (settings.driver or "mock").lower()
    if driver_name not in {"mock", "alttester", "questline"}:
        raise AuthoringError(
            f"Driver '{driver_name}' is not available. "
            'Use profile driver = "mock", "questline" (QuestlineWire), '
            'or "alttester" (requires questline[alttester]).'
        )

    def _provider() -> DriverPort:
        if driver_name == "mock":
            return MockDriver()
        if driver_name == "questline":
            from questline.drivers.wire import QuestlineDriver

            return QuestlineDriver()
        from questline.drivers.alttester import AltTesterDriver

        return AltTesterDriver()

    handle = DriverHandle(provider=_provider)
    if driver_name == "mock":
        handle.connect(ConnectionTarget(host="mock", port=0))
    else:
        extras: dict[str, str] = {}
        if settings.target_app_name:
            extras["app_name"] = settings.target_app_name
        if questline_device is not None:
            extras["device_serial"] = questline_device["device"].id
        handle.connect(
            ConnectionTarget(
                host=settings.target_host,
                port=settings.target_port,
                platform=settings.target_platform or "editor",
                extras=extras,
            )
        )
    return handle


@pytest.fixture(scope="session")
def questline_device(
    questline_settings: Settings,
    questline_run_id: str,
) -> Any:
    """Acquire a local adb device when profile ``device`` is adb/android; else None."""
    from questline.devices.session import (
        needs_adb_device,
        setup_android_session,
        teardown_android_session,
    )

    _ = questline_run_id
    if not needs_adb_device(questline_settings):
        yield None
        return

    bundle = setup_android_session(questline_settings)
    yield bundle
    teardown_android_session(bundle, app_package=questline_settings.app_package)


def _connection_target_for(settings: Settings, questline_device: Any) -> Any:
    from questline.drivers.port import ConnectionTarget

    driver_name = (settings.driver or "mock").lower()
    if driver_name == "mock":
        return ConnectionTarget(host="mock", port=0)
    extras: dict[str, str] = {}
    if settings.target_app_name:
        extras["app_name"] = settings.target_app_name
    if questline_device is not None:
        extras["device_serial"] = questline_device["device"].id
    return ConnectionTarget(
        host=settings.target_host,
        port=settings.target_port,
        platform=settings.target_platform or "editor",
        extras=extras,
    )


@pytest.fixture(scope="session")
def driver_handle(
    questline_settings: Settings,
    questline_run_id: str,
    questline_device: Any,
    questline_bus: EventBus,
    pytestconfig: pytest.Config,
) -> Any:
    from questline.core.recovery import RecoveryPolicy

    handle = wire_driver_handle(questline_settings, questline_device)
    target = _connection_target_for(questline_settings, questline_device)
    device_provider = None
    device = None
    if questline_device is not None:
        device_provider = questline_device.get("provider")
        device = questline_device.get("device")

    watchdog = pytestconfig.stash.get(_STASH_WATCHDOG, None)

    def _breaker_exit(code: int) -> None:
        pytest.exit(
            f"questline circuit breaker tripped (exit {code})",
            returncode=code,
        )

    recovery = RecoveryPolicy(
        handle,
        bus=questline_bus,
        run_id=questline_run_id,
        target=target,
        device_provider=device_provider,
        device=device,
        app_package=questline_settings.app_package,
        app_activity=questline_settings.app_activity,
        max_consecutive_losses=questline_settings.resilience.circuit_breaker_losses,
        on_progress=(watchdog.mark_progress if watchdog is not None else None),
        abort_fn=_breaker_exit,
    )
    pytestconfig.stash[_STASH_RECOVERY] = recovery
    yield handle
    try:
        if handle.is_alive():
            handle.disconnect()
    except Exception:  # pragma: no cover - disposal must not fail the session
        pass


@pytest.fixture
def questline_ctx(
    driver_handle: DriverHandle,
    questline_bus: EventBus,
    questline_run_id: str,
    questline_settings: Settings,
    request: pytest.FixtureRequest,
) -> Context:
    from questline.authoring.context import Context

    return Context(
        driver=driver_handle,
        bus=questline_bus,
        run_id=questline_run_id,
        test_id=request.node.nodeid,
        wait_policy=questline_settings.wait_policy(),
    )


def _uses_questline(item: pytest.Item) -> bool:
    names = set(getattr(item, "fixturenames", ()))
    return bool(
        names
        & {
            "questline_ctx",
            "driver_handle",
            "questline_run_id",
            "questline_store",
            "questline_bus",
            "questline_device",
        }
    )


def _save_failure_artifacts(
    *,
    store: Any,
    handle: Any,
    device_bundle: Any,
    run_id: str,
    test_id: str,
    tags: dict[str, str],
) -> None:
    """Best-effort screenshot + logcat into the run store on failure."""
    safe_test = test_id.replace("/", "_").replace("\\", "_").replace(":", "_")
    if store is not None and handle is not None:
        try:
            png = handle.screenshot()
            if png:
                path = store.save_artifact(
                    png,
                    run_id=run_id,
                    name=f"{safe_test}-screenshot.png",
                    kind="screenshot",
                    test_id=test_id,
                )
                tags["artifact_screenshot"] = str(path)
        except Exception as exc:  # pragma: no cover - artifact capture is best-effort
            tags["artifact_screenshot_error"] = f"{type(exc).__name__}: {exc}"
    if store is not None and device_bundle is not None:
        try:
            provider = device_bundle["provider"]
            device = device_bundle["device"]
            log_text = provider.logs(device)
            path = store.save_artifact(
                log_text.encode("utf-8", errors="replace"),
                run_id=run_id,
                name=f"{safe_test}-logcat.txt",
                kind="logcat",
                test_id=test_id,
            )
            tags["artifact_logcat"] = str(path)
        except Exception as exc:  # pragma: no cover
            tags["artifact_logcat_error"] = f"{type(exc).__name__}: {exc}"


def _fixture_value(item: pytest.Item, name: str) -> Any:
    funcargs = getattr(item, "funcargs", None)
    if isinstance(funcargs, dict) and name in funcargs:
        return funcargs[name]
    try:  # pragma: no cover - cache walk is a best-effort fallback
        defs = item.session._fixturemanager.getfixturedefs(name, item.nodeid)  # noqa: SLF001
    except Exception:  # pragma: no cover
        return None
    if not defs:  # pragma: no cover
        return None
    for fixturedef in defs:  # pragma: no cover
        cached = getattr(fixturedef, "cached_result", None)
        if cached is not None:
            return cached[0]
    return None  # pragma: no cover


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_setup(item: pytest.Item) -> Any:
    yield
    if not _uses_questline(item):
        return
    watchdog = item.config.stash.get(_STASH_WATCHDOG, None)
    if watchdog is not None:
        watchdog.mark_progress()
    bus = _fixture_value(item, "questline_bus")
    run_id = _fixture_value(item, "questline_run_id")
    if bus is None or run_id is None:
        return
    if getattr(item, "_questline_started_emitted", False):
        return
    from questline.core.events import TestStarted

    feature_id = feature_id_for_item(item)
    bus.publish(
        TestStarted(
            run_id=run_id,
            test_id=item.nodeid,
            nodeid=item.nodeid,
            feature_id=feature_id,
        )
    )
    item._questline_started_emitted = True  # type: ignore[attr-defined]
    item._questline_t0 = time.perf_counter()  # type: ignore[attr-defined]
    item._questline_feature_id = feature_id  # type: ignore[attr-defined]


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo[Any]) -> Any:
    outcome = yield
    report: pytest.TestReport = outcome.get_result()
    if report.when != "call" or not _uses_questline(item):
        return
    bus = _fixture_value(item, "questline_bus")
    run_id = _fixture_value(item, "questline_run_id")
    handle = _fixture_value(item, "driver_handle")
    if bus is None or run_id is None:
        return

    watchdog = item.config.stash.get(_STASH_WATCHDOG, None)
    if watchdog is not None:
        watchdog.mark_progress()

    from questline.core.errors import SessionLostError, classify, normalize_exception
    from questline.core.events import TestFinished, TestStarted
    from questline.core.health import HealthMonitor

    feature_id = getattr(item, "_questline_feature_id", None) or feature_id_for_item(item)
    if not getattr(item, "_questline_started_emitted", False):
        bus.publish(
            TestStarted(
                run_id=run_id,
                test_id=item.nodeid,
                nodeid=item.nodeid,
                feature_id=feature_id,
            )
        )
        item._questline_started_emitted = True  # type: ignore[attr-defined]

    status = "passed"
    verdict = None
    error_type = None
    error_message = None
    tags: dict[str, str] = {}
    if feature_id:
        tags["feature_id"] = feature_id

    normalized_exc: BaseException | None = None
    if report.failed:
        status = "failed"
        if call.excinfo is not None:
            err = call.excinfo.value
            normalized_exc = normalize_exception(err)
            verdict = classify(err).value
            error_type = type(normalized_exc).__name__
            error_message = str(normalized_exc)
        else:  # pragma: no cover - pytest always provides excinfo on failed call
            verdict = "unknown"
            error_message = str(report.longrepr)
    elif report.skipped:
        status = "skipped"

    recovery = item.config.stash.get(_STASH_RECOVERY, None)
    settings = _fixture_value(item, "questline_settings")

    if status == "passed" and recovery is not None:
        recovery.record_pass()

    if status == "failed" and handle is not None:
        device_bundle = _fixture_value(item, "questline_device")
        device_provider = device_bundle.get("provider") if device_bundle else None
        device = device_bundle.get("device") if device_bundle else None
        monitor = HealthMonitor(handle, device_provider=device_provider, device=device)
        snap = None
        try:
            snap = monitor.check()
            tags.update(snap.as_tags())
            try:
                state = handle.app_state()
                tags["app_scene"] = state.scene or ""
                tags["app_foreground"] = "true" if state.foreground else "false"
                tags["app_paused"] = "true" if state.paused else "false"
            except Exception as state_exc:  # pragma: no cover
                tags["app_state_error"] = f"{type(state_exc).__name__}: {state_exc}"
        except Exception as health_exc:  # pragma: no cover - health probe is best-effort
            tags["driver_health_error"] = f"{type(health_exc).__name__}: {health_exc}"

        store = _fixture_value(item, "questline_store")
        _save_failure_artifacts(
            store=store,
            handle=handle,
            device_bundle=device_bundle,
            run_id=run_id,
            test_id=item.nodeid,
            tags=tags,
        )

        session_lost = isinstance(normalized_exc, SessionLostError)
        unhealthy = snap is not None and snap.suggests_session_loss
        recovery_enabled = True
        if settings is not None:
            recovery_enabled = bool(settings.resilience.recovery_enabled)
        if recovery is not None and recovery_enabled and (session_lost or unhealthy):
            if watchdog is not None:
                watchdog.mark_progress()
            try:
                recovery.recover(normalized_exc)
            except Exception as recover_exc:  # pragma: no cover
                tags["recovery_error"] = f"{type(recover_exc).__name__}: {recover_exc}"
            if watchdog is not None:
                watchdog.mark_progress()

    t0 = getattr(item, "_questline_t0", time.perf_counter())
    bus.publish(
        TestFinished(
            run_id=run_id,
            test_id=item.nodeid,
            nodeid=item.nodeid,
            status=status,
            verdict=verdict,
            error_type=error_type,
            error_message=error_message,
            duration_s=time.perf_counter() - float(t0),
            tags=tags,
        )
    )
