"""CLI coverage for `questline hud` (import / help / missing extra)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from questline.cli import app

runner = CliRunner()


def test_hud_help() -> None:
    result = runner.invoke(app, ["hud", "--help"])
    assert result.exit_code == 0
    assert "--port" in result.stdout
    assert "--open" in result.stdout
    assert "--host" in result.stdout


def test_hud_serve_invoked(tmp_path: Path) -> None:
    config = tmp_path / "questline.toml"
    config.write_text('[profile.editor]\ndriver = "mock"\n', encoding="utf-8")
    called: dict[str, object] = {}

    def fake_serve(**kwargs: object) -> None:
        called.update(kwargs)

    with patch("questline.hud.server.serve", fake_serve):
        result = runner.invoke(
            app,
            [
                "hud",
                "--config",
                str(config),
                "--profile",
                "editor",
                "--port",
                "8999",
                "--store",
                str(tmp_path / "store.db"),
            ],
        )
    assert result.exit_code == 0, result.stdout + result.stderr
    assert called.get("port") == 8999
    assert called.get("host") == "127.0.0.1"
