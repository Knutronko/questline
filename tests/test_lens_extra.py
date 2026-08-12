"""Extra GameLens coverage: edge paths for normalize/diff/manifest/render."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from questline.core.errors import AuthoringError
from questline.core.store import RunStore
from questline.lens.diff import DiffReport, diff_snapshots
from questline.lens.manifest import load_manifest, parse_manifest
from questline.lens.render import render_diff_text
from questline.lens.report import implications_stub
from questline.lens.snapshot import (
    BalanceSnapshot,
    SnapshotMeta,
    load_snapshot,
    normalize_fields,
    normalize_pack,
    parse_snapshot,
    write_snapshot,
)

FIXTURES = Path(__file__).parent / "fixtures" / "lens"


def test_normalize_fields_series_and_list_curve() -> None:
    fields = normalize_fields(
        {
            "rates": [1, 2, 3.5],
            "curve_list": [[0, 1], [1, 2]],
            "curve_dicts": [{"time": 0, "value": 1}, {"time": 1, "value": 3}],
            "mixed": [1, "x"],
            "flag": True,
            "empty": None,
        }
    )
    assert fields["rates"]["type"] == "series"
    assert fields["rates"]["values"] == [1.0, 2.0, 3.5]
    assert fields["curve_list"]["type"] == "curve"
    assert fields["curve_dicts"]["type"] == "curve"
    assert fields["mixed"]["type"] == "string"
    assert fields["flag"]["type"] == "bool"
    assert fields["empty"]["type"] == "null"


def test_normalize_fields_already_normalized() -> None:
    fields = normalize_fields(
        {
            "fields": {
                "hp": {"type": "number", "value": 10},
                "name": {"type": "string", "value": "x"},
            }
        }
    )
    assert fields["hp"]["value"] == 10


def test_load_write_snapshot_roundtrip(tmp_path: Path) -> None:
    snap = normalize_pack(FIXTURES / "pack-a", game_version="rt")
    path = write_snapshot(snap, tmp_path / "balance_snapshot.json")
    loaded = load_snapshot(path)
    assert loaded.meta.game_version == "rt"
    assert set(loaded.entities) == set(snap.entities)


def test_parse_snapshot_rejects_bad_version() -> None:
    with pytest.raises(AuthoringError, match="schema_version"):
        parse_snapshot({"schema_version": 99, "meta": {"game_version": "x"}, "entities": {}})


def test_diff_field_added_removed_and_series() -> None:
    a = BalanceSnapshot(
        schema_version=1,
        meta=SnapshotMeta(game_version="a"),
        entities={
            "e": {
                "id": "e",
                "system": "waves",
                "kind": "config",
                "fields": {
                    "old": {"type": "string", "value": "gone"},
                    "series": {"type": "series", "values": [1.0, 2.0]},
                },
            }
        },
    )
    b = BalanceSnapshot(
        schema_version=1,
        meta=SnapshotMeta(game_version="b", feature_id="feat-1"),
        entities={
            "e": {
                "id": "e",
                "system": "waves",
                "kind": "config",
                "fields": {
                    "new": {"type": "number", "value": 3},
                    "series": {"type": "series", "values": [1.0, 9.0]},
                },
            }
        },
    )
    report = diff_snapshots(a, b)
    kinds_paths = {(e.kind, e.path) for e in report.entries}
    assert ("changed", "old") in kinds_paths
    assert ("changed", "new") in kinds_paths
    assert ("series_changed", "series") in kinds_paths
    assert report.feature_id == "feat-1"
    text = render_diff_text(report, implications=implications_stub(report))
    assert "[waves]" in text
    assert "series_changed" in text or "series" in text
    assert implications_stub(report).to_dict()["pending"] == "phase-11"
    assert report.to_dict()["by_system"]["waves"]


def test_diff_string_change_and_zero_base_pct() -> None:
    a = BalanceSnapshot(
        schema_version=1,
        meta=SnapshotMeta(game_version="a"),
        entities={
            "e": {
                "id": "e",
                "system": "economy",
                "kind": "config",
                "fields": {
                    "label": {"type": "string", "value": "a"},
                    "n": {"type": "number", "value": 0},
                },
            }
        },
    )
    b = BalanceSnapshot(
        schema_version=1,
        meta=SnapshotMeta(game_version="b"),
        entities={
            "e": {
                "id": "e",
                "system": "economy",
                "kind": "config",
                "fields": {
                    "label": {"type": "string", "value": "b"},
                    "n": {"type": "number", "value": 5},
                },
            }
        },
    )
    report = diff_snapshots(a, b)
    label = next(e for e in report.entries if e.path == "label")
    assert label.before == "a" and label.after == "b"
    n = next(e for e in report.entries if e.path == "n")
    assert n.pct is None
    assert n.delta == 5


def test_manifest_entry_by_id_and_validation_errors() -> None:
    m = parse_manifest(
        {
            "schema_version": 1,
            "entries": [
                {"id": "a", "system": "economy", "source_file": "a.json"},
            ],
            "supplementary": [{"kind": "csv", "path": "x.csv"}],
            "meta": {"k": 1},
        }
    )
    assert m.entry_by_id("a") is not None
    assert m.entry_by_id("nope") is None

    with pytest.raises(AuthoringError, match="non-empty"):
        parse_manifest({"schema_version": 1, "entries": []})
    with pytest.raises(AuthoringError, match="root must be an object"):
        parse_manifest([])
    with pytest.raises(AuthoringError, match="asset_path and/or source_file"):
        parse_manifest(
            {
                "schema_version": 1,
                "entries": [{"id": "x", "system": "economy"}],
            }
        )
    with pytest.raises(AuthoringError, match="kind must be one of"):
        parse_manifest(
            {
                "schema_version": 1,
                "entries": [{"id": "x", "system": "economy", "source_file": "a.json"}],
                "supplementary": [{"kind": "bin", "path": "x"}],
            }
        )


def test_manifest_invalid_json(tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    path.write_text("{not-json", encoding="utf-8")
    with pytest.raises(AuthoringError, match="not valid JSON"):
        load_manifest(path)


def test_store_balance_snapshot_list_and_resolve(tmp_path: Path) -> None:
    store = RunStore(tmp_path / "store.db")
    try:
        payload = json.dumps(
            {
                "schema_version": 1,
                "meta": {"game_version": "1.0.0"},
                "entities": {},
                "supplementary": [],
            }
        )
        store.save_balance_snapshot(
            snapshot_id="snap-1",
            game_version="1.0.0",
            payload=payload,
            feature_id="f1",
        )
        store.save_balance_snapshot(
            snapshot_id="snap-2",
            game_version="1.0.0",
            payload=payload,
        )
        by_id = store.get_balance_snapshot("snap-1")
        assert by_id is not None and by_id["id"] == "snap-1"
        by_ver = store.get_balance_snapshot("1.0.0")
        assert by_ver is not None  # latest
        listed = store.list_balance_snapshots(game_version="1.0.0", feature_id="f1")
        assert len(listed) == 1
        assert store.list_balance_snapshots(limit=1)
    finally:
        store.close()


def test_render_empty_diff() -> None:
    report = DiffReport(
        version_a="a",
        version_b="b",
        snapshot_id_a=None,
        snapshot_id_b=None,
        entries=(),
    )
    text = render_diff_text(report)
    assert "(no differences)" in text


def test_normalize_pack_missing_dir() -> None:
    with pytest.raises(AuthoringError, match="pack directory not found"):
        normalize_pack(Path("no-such-pack-dir"), game_version="x")


def test_normalize_fields_rejects_non_object() -> None:
    with pytest.raises(AuthoringError, match="JSON object"):
        normalize_fields([1, 2, 3])
