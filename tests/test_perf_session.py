"""PerfProbe session wiring + report helpers + companion edge cases."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from questline.core.config import PerfSettings, Settings
from questline.core.errors import AuthoringError
from questline.core.events import EventBus
from questline.drivers.port import ConnectionTarget
from questline.drivers.wire.fake import FakeWireDriverHarness
from questline.perf.asserts import assert_avg, assert_no_samples_below, clear_perf_context
from questline.perf.companion import CompanionPerfCollector, companion_collector_from_driver
from questline.perf.report import render_perf_report, write_perf_report
from questline.perf.session import build_collectors, create_probe


def test_create_probe_disabled() -> None:
    settings = Settings(perf=PerfSettings(enabled=False))
    assert create_probe(settings, bus=EventBus(), run_id="r") is None


def test_create_probe_companion_editor() -> None:
    settings = Settings(
        driver="questline",
        target_platform="editor",
        perf=PerfSettings(enabled=True, interval_s=0.5, source="companion"),
    )
    harness = FakeWireDriverHarness()
    driver = harness()
    driver.connect(ConnectionTarget(host="127.0.0.1", port=13000, platform="editor"))
    bus = EventBus()
    probe = create_probe(settings, bus=bus, run_id="r1", driver=driver)
    assert probe is not None
    n = probe.sample_once()
    assert n >= 1
    driver.disconnect()


def test_build_collectors_android_with_fake_shell() -> None:
    settings = Settings(
        driver="questline",
        target_platform="android",
        app_package="com.example.game",
        perf=PerfSettings(enabled=True, source="android"),
    )

    class _Prov:
        def shell(self, device: Any, command: str) -> str:
            _ = device, command
            return ""

    bundle = {"provider": _Prov(), "device": object()}
    cols = build_collectors(settings, device_bundle=bundle)
    assert len(cols) == 1


def test_build_collectors_auto_fallback_companion() -> None:
    settings = Settings(
        driver="questline",
        target_platform="android",
        perf=PerfSettings(enabled=True, source="auto"),
    )
    harness = FakeWireDriverHarness()
    driver = harness()
    driver.connect(ConnectionTarget(host="127.0.0.1", port=13000, platform="android"))
    cols = build_collectors(settings, driver=driver, device_bundle=None)
    assert len(cols) == 1
    driver.disconnect()


def test_create_probe_no_collectors_returns_none() -> None:
    settings = Settings(
        driver="mock",
        perf=PerfSettings(enabled=True, source="android"),
    )
    assert create_probe(settings, bus=EventBus(), run_id="r") is None


def test_companion_bad_payload_and_hook_error() -> None:
    bad = CompanionPerfCollector(call_hook=lambda: "not-json")
    assert dict(bad.collect()) == {}

    def boom() -> Any:
        raise RuntimeError("no hook")

    err = CompanionPerfCollector(call_hook=boom)
    assert dict(err.collect()) == {}
    assert dict(err.collect()) == {}


def test_write_perf_report_empty(tmp_path: Path) -> None:
    path = write_perf_report(
        run_id="empty",
        samples=[],
        output_dir=tmp_path,
        fmt="text",
    )
    assert path.is_file()
    assert "(no perf samples)" in path.read_text(encoding="utf-8")
    html = render_perf_report(run_id="empty", samples=[], fmt="html")
    assert "no perf samples" in html


def test_assert_authoring_errors() -> None:
    clear_perf_context()
    with pytest.raises(AuthoringError):
        assert_avg("fps", ">=", 1)
    with pytest.raises(AuthoringError):
        assert_no_samples_below("fps", 1, tolerance=-1)


def test_companion_from_driver_aliases() -> None:
    harness = FakeWireDriverHarness()
    driver = harness()
    driver.connect(ConnectionTarget(host="127.0.0.1", port=13000, platform="editor"))
    transport = driver._transport  # noqa: SLF001
    assert transport is not None
    transport._perf_sample = {  # type: ignore[attr-defined]
        "fps": 59.0,
        "allocated_memory_mb": 64.0,
        "drawcalls": 7.0,
    }
    sample = dict(companion_collector_from_driver(driver).collect())
    assert sample["fps"] == 59.0
    assert sample["allocated_mb"] == 64.0
    assert sample["draw_calls"] == 7.0
    driver.disconnect()
