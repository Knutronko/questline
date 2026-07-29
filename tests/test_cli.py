"""CLI stub tests."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from questline import __version__
from questline.cli import app

runner = CliRunner()


def test_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert result.stdout.strip() == __version__


def test_doctor_prints_resolved_profile(tmp_path: Path) -> None:
    # Prefer the repo sample when present; otherwise write a local one.
    sample = Path(__file__).resolve().parents[1] / "examples" / "questline.toml"
    if sample.is_file():
        config = sample
        expected_profile = "editor"
    else:
        config = tmp_path / "questline.toml"
        config.write_text(
            '[profile.editor]\ndriver = "mock"\nwait.deadline = 20.0\n',
            encoding="utf-8",
        )
        expected_profile = "editor"

    result = runner.invoke(app, ["doctor", "--config", str(config), "--profile", expected_profile])
    assert result.exit_code == 0, result.stdout + result.stderr
    assert f"profile:     {expected_profile}" in result.stdout
    assert "driver:      mock" in result.stdout
    assert "wait:" in result.stdout
    assert "store_db:" in result.stdout


def test_doctor_bad_profile_exits_nonzero(tmp_path: Path) -> None:
    config = tmp_path / "questline.toml"
    config.write_text('[profile.editor]\ndriver = "mock"\n', encoding="utf-8")
    result = runner.invoke(app, ["doctor", "--config", str(config), "--profile", "nope"])
    assert result.exit_code == 2
    assert "Profile 'nope' not found" in result.stdout + result.stderr
