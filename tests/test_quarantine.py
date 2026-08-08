"""Quarantine ledger + audit limbo detection."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from questline.authoring.quarantine import QuarantineLedger
from questline.cli import app
from questline.core.errors import AuthoringError

runner = CliRunner()


def test_ledger_add_remove_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "quarantine.yaml"
    ledger = QuarantineLedger(path)
    ledger.add(
        "tests/t.py::test_a",
        reason="flake",
        owner="dev",
        exit_criteria="20 greens",
        feature="shop",
        issue="ISSUE-1",
    )
    ledger.save()
    loaded = QuarantineLedger.load(path)
    entry = loaded.get("tests/t.py::test_a")
    assert entry is not None
    assert entry.feature == "shop"
    assert entry.issue == "ISSUE-1"
    assert loaded.remove("tests/t.py::test_a") is True
    loaded.save()
    assert QuarantineLedger.load(path).contains("tests/t.py::test_a") is False


def test_audit_detects_limbo(tmp_path: Path) -> None:
    path = tmp_path / "quarantine.yaml"
    ledger = QuarantineLedger(path)
    ledger.add(
        "only_in_ledger",
        reason="r",
        owner="o",
        exit_criteria="e",
    )
    report = ledger.audit({"only_in_marker"})
    assert report.ok is False
    assert report.ledger_only == ["only_in_ledger"]
    assert report.marker_only == ["only_in_marker"]
    assert "LIMBO" in report.summary()


def test_audit_ok_when_in_sync() -> None:
    ledger = QuarantineLedger(Path("unused.yaml"))
    ledger.add("t::a", reason="r", owner="o", exit_criteria="e")
    assert ledger.audit({"t::a"}).ok is True


def test_cli_quarantine_add_remove_audit_limbo(tmp_path: Path) -> None:
    path = tmp_path / "quarantine.yaml"
    add = runner.invoke(
        app,
        [
            "quarantine",
            "add",
            "seeded::limbo",
            "--reason",
            "seed",
            "--owner",
            "ci",
            "--exit-criteria",
            "fix",
            "--feature",
            "demo",
            "--path",
            str(path),
        ],
    )
    assert add.exit_code == 0, add.stdout + add.stderr

    # Audit with empty marker set → limbo (ledger-only).
    # Use --tests pointing at an empty dir so collection finds nothing.
    empty = tmp_path / "empty_tests"
    empty.mkdir()
    audit = runner.invoke(
        app,
        [
            "quarantine",
            "audit",
            "--path",
            str(path),
            "--tests",
            str(empty),
            "--rootdir",
            str(tmp_path),
        ],
    )
    assert audit.exit_code == 1
    assert "LIMBO" in audit.stdout

    remove = runner.invoke(app, ["quarantine", "remove", "seeded::limbo", "--path", str(path)])
    assert remove.exit_code == 0
    audit2 = runner.invoke(
        app,
        [
            "quarantine",
            "audit",
            "--path",
            str(path),
            "--tests",
            str(empty),
            "--rootdir",
            str(tmp_path),
        ],
    )
    assert audit2.exit_code == 0
    assert "ok" in audit2.stdout


def test_invalid_ledger_yaml(tmp_path: Path) -> None:
    path = tmp_path / "quarantine.yaml"
    path.write_text("version: 1\nentries: not-a-list\n", encoding="utf-8")
    with pytest.raises(AuthoringError, match="must be a list"):
        QuarantineLedger.load(path)
