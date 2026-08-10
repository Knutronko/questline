"""Unit tests for HUD query helpers."""

from __future__ import annotations

from pathlib import Path

from questline.hud.fixtures import seed_fixture_store
from questline.hud.queries import (
    allowlisted_artifact,
    duration_seconds,
    enrich_run,
    parse_meta,
    trends,
)


def test_parse_meta_and_duration() -> None:
    assert parse_meta('{"driver":"mock"}')["driver"] == "mock"
    assert parse_meta("{not-json") == {}
    assert parse_meta(None) == {}
    assert parse_meta({"device": "adb"})["device"] == "adb"
    assert duration_seconds(None, "2026-01-01T00:00:01") is None
    assert duration_seconds("2026-01-01T00:00:00+00:00", "2026-01-01T00:00:02+00:00") == 2.0
    assert duration_seconds("2026-01-01T00:00:00Z", "2026-01-01T00:00:01Z") == 1.0
    assert duration_seconds("bad", "also-bad") is None


def test_allowlisted_artifact_name() -> None:
    art = allowlisted_artifact(
        {
            "path": r"C:\tmp\run\shot.png",
            "kind": "screenshot",
            "size_bytes": 12,
            "secret": "nope",
        }
    )
    assert "secret" not in art
    assert art["name"] == "shot.png"
    assert art["kind"] == "screenshot"


def test_trends_and_enrich(tmp_path: Path) -> None:
    store = seed_fixture_store(tmp_path / "store.db")
    try:
        run = store.get_run("run-a")
        assert run is not None
        enriched = enrich_run(store, run)
        assert enriched["infra_failures"] == 1
        assert enriched["driver"] == "questline"
        data = trends(store, limit_runs=10)
        assert len(data["series"]) == 2
        assert any(f["nodeid"].endswith("test_shop") for f in data["flaky_tests"])
    finally:
        store.close()
