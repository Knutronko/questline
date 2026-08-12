"""GameLens normalize + typed diff unit tests (no Unity)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from questline.core.errors import AuthoringError
from questline.lens.diff import diff_snapshots
from questline.lens.manifest import load_manifest
from questline.lens.report import implications_stub
from questline.lens.snapshot import normalize_pack

FIXTURES = Path(__file__).parent / "fixtures" / "lens"


def test_normalize_pack_a_shapes() -> None:
    snap = normalize_pack(FIXTURES / "pack-a", game_version="1.0.0")
    assert snap.meta.game_version == "1.0.0"
    assert set(snap.entities) == {"economy", "unit_alpha"}
    eco = snap.entities["economy"]["fields"]
    assert eco["amber_per_tick"]["type"] == "number"
    assert eco["amber_per_tick"]["value"] == 1.5
    assert eco["density_curve"]["type"] == "curve"
    assert eco["density_curve"]["points"] == [[0.0, 1.0], [1.0, 1.2]]
    assert snap.entities["unit_alpha"]["fields"]["resist"]["type"] == "object"
    assert snap.supplementary[0]["present"] is True


def test_diff_includes_new_entity_and_numeric_pct() -> None:
    a = normalize_pack(FIXTURES / "pack-a", game_version="1.0.0")
    b = normalize_pack(FIXTURES / "pack-b", game_version="1.1.0")
    report = diff_snapshots(a, b, snapshot_id_a="1.0.0", snapshot_id_b="1.1.0")
    kinds = {e.kind for e in report.entries}
    assert "added_entity" in kinds
    added = [e for e in report.entries if e.kind == "added_entity"]
    assert any(e.entity_id == "unit_beta" for e in added)
    assert added[0].entity is not None
    assert "hp" in added[0].entity["fields"]

    amber = next(
        e
        for e in report.entries
        if e.entity_id == "economy" and e.path == "amber_per_tick"
    )
    assert amber.kind == "changed"
    assert amber.before == 1.5
    assert amber.after == 2.0
    assert amber.delta == pytest.approx(0.5)
    assert amber.pct == pytest.approx((0.5 / 1.5) * 100.0)

    curve = next(
        e
        for e in report.entries
        if e.kind == "curve_changed" and e.entity_id == "economy"
    )
    assert curve.path == "density_curve"

    by_system = report.by_system()
    assert "creatures" in by_system
    assert "economy" in by_system

    stub = implications_stub(report)
    assert stub.status == "pending"
    assert stub.pending == "phase-11"
    assert stub.framing == "model reasoning"


def test_diff_removed_entity() -> None:
    a = normalize_pack(FIXTURES / "pack-b", game_version="1.1.0")
    b = normalize_pack(FIXTURES / "pack-a", game_version="1.0.0")
    report = diff_snapshots(a, b)
    removed = [e for e in report.entries if e.kind == "removed_entity"]
    assert any(e.entity_id == "unit_beta" for e in removed)


def test_manifest_missing_source_errors(tmp_path: Path) -> None:
    manifest = {
        "schema_version": 1,
        "entries": [
            {
                "id": "missing",
                "system": "economy",
                "asset_path": "Assets/X.asset",
                "source_file": "nope.json",
            }
        ],
    }
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(AuthoringError, match="missing source_file"):
        normalize_pack(tmp_path, game_version="x")


def test_manifest_duplicate_id_errors(tmp_path: Path) -> None:
    manifest = {
        "schema_version": 1,
        "entries": [
            {
                "id": "dup",
                "system": "economy",
                "source_file": "a.json",
            },
            {
                "id": "dup",
                "system": "economy",
                "source_file": "b.json",
            },
        ],
    }
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(AuthoringError, match="duplicate"):
        load_manifest(path)


def test_unknown_manifest_path() -> None:
    with pytest.raises(AuthoringError, match="manifest not found"):
        load_manifest(Path("does-not-exist-manifest.json"))
