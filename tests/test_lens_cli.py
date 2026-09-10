"""CLI smoke for questline lens snapshot / diff (fixtures, no Unity)."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from questline.cli import app

FIXTURES = Path(__file__).parent / "fixtures" / "lens"
runner = CliRunner()


def test_lens_snapshot_and_diff_cli(tmp_path: Path) -> None:
    db = tmp_path / "store.db"
    r1 = runner.invoke(
        app,
        [
            "lens",
            "snapshot",
            "--pack",
            str(FIXTURES / "pack-a"),
            "--version",
            "1.0.0",
            "--store",
            str(db),
        ],
    )
    assert r1.exit_code == 0, r1.output
    assert "id=1.0.0" in r1.output

    r2 = runner.invoke(
        app,
        [
            "lens",
            "snapshot",
            "--pack",
            str(FIXTURES / "pack-b"),
            "--version",
            "1.1.0",
            "--store",
            str(db),
        ],
    )
    assert r2.exit_code == 0, r2.output

    text = runner.invoke(
        app,
        ["lens", "diff", "1.0.0", "1.1.0", "--store", str(db), "--format", "text"],
    )
    assert text.exit_code == 0, text.output
    assert "unit_beta" in text.output
    assert "added_entity" in text.output or "+ entity unit_beta" in text.output
    assert "pending: no-provider" in text.output
    impl_json = tmp_path / "artifacts" / "lens" / "1.0.0__1.1.0" / "implications.json"
    impl_md = tmp_path / "artifacts" / "lens" / "1.0.0__1.1.0" / "implications.md"
    assert impl_json.is_file(), text.output
    assert impl_md.is_file()
    persisted = json.loads(impl_json.read_text(encoding="utf-8"))
    assert persisted["status"] == "skipped"
    assert persisted["framing"] == "model reasoning"
    assert "combat.damage" in " ".join(persisted["gaps"])
    assert "artifact:" in text.output

    js = runner.invoke(
        app,
        [
            "lens",
            "diff",
            "1.0.0",
            "1.1.0",
            "--store",
            str(db),
            "--format",
            "json",
            "--no-ai",
        ],
    )
    assert js.exit_code == 0, js.output
    payload = json.loads(js.output)
    assert payload["version_a"] == "1.0.0"
    assert payload["version_b"] == "1.1.0"
    kinds = {e["kind"] for e in payload["entries"]}
    assert "added_entity" in kinds
    assert "implications" not in payload


def test_lens_diff_no_ai_does_not_persist(tmp_path: Path) -> None:
    db = tmp_path / "store.db"
    for ver, pack in (("1.0.0", "pack-a"), ("1.1.0", "pack-b")):
        r = runner.invoke(
            app,
            [
                "lens",
                "snapshot",
                "--pack",
                str(FIXTURES / pack),
                "--version",
                ver,
                "--store",
                str(db),
            ],
        )
        assert r.exit_code == 0, r.output
    result = runner.invoke(
        app,
        ["lens", "diff", "1.0.0", "1.1.0", "--store", str(db), "--no-ai"],
    )
    assert result.exit_code == 0, result.output
    impl_dir = tmp_path / "artifacts" / "lens" / "1.0.0__1.1.0"
    assert not (impl_dir / "implications.json").exists()


def test_lens_snapshot_requires_pack_or_import(tmp_path: Path) -> None:
    result = runner.invoke(app, ["lens", "snapshot", "--store", str(tmp_path / "s.db")])
    assert result.exit_code == 2
    assert "exactly one" in result.output


def test_lens_diff_unknown_snapshot(tmp_path: Path) -> None:
    db = tmp_path / "store.db"
    # Create empty store via a snapshot then ask for missing key.
    ok = runner.invoke(
        app,
        [
            "lens",
            "snapshot",
            "--pack",
            str(FIXTURES / "pack-a"),
            "--version",
            "only",
            "--store",
            str(db),
        ],
    )
    assert ok.exit_code == 0, ok.output
    missing = runner.invoke(app, ["lens", "diff", "only", "nope", "--store", str(db)])
    assert missing.exit_code == 1
    assert "unknown snapshot" in missing.output


def test_lens_snapshot_import_and_overrides(tmp_path: Path) -> None:
    snap_path = tmp_path / "in.json"
    from questline.lens.snapshot import normalize_pack, write_snapshot

    write_snapshot(
        normalize_pack(FIXTURES / "pack-a", game_version="orig"),
        snap_path,
    )
    db = tmp_path / "store.db"
    result = runner.invoke(
        app,
        [
            "lens",
            "snapshot",
            "--import",
            str(snap_path),
            "--version",
            "imported",
            "--id",
            "imp-1",
            "--git-commit",
            "abc",
            "--feature-id",
            "feat",
            "--store",
            str(db),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "id=imp-1" in result.output
    assert "version=imported" in result.output

    bad_fmt = runner.invoke(
        app,
        ["lens", "diff", "imp-1", "imp-1", "--store", str(db), "--format", "xml"],
    )
    assert bad_fmt.exit_code == 2
