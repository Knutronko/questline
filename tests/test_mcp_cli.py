"""CLI coverage for `questline mcp`."""

from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from questline.cli import app

runner = CliRunner()
_ANSI = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")


def test_mcp_help() -> None:
    result = runner.invoke(
        app,
        ["mcp", "--help"],
        env={"NO_COLOR": "1", "TERM": "dumb", "COLUMNS": "120"},
    )
    assert result.exit_code == 0
    plain = _ANSI.sub("", (result.stdout or "") + (result.stderr or ""))
    for token in ("--allow-write", "--allow-fix", "--store", "--config"):
        assert token in plain, f"missing {token!r} in help:\n{plain}"


def test_mcp_missing_extra_message(tmp_path: Path) -> None:
    cfg = tmp_path / "questline.toml"
    cfg.write_text('[profile.mock]\ndriver = "mock"\n', encoding="utf-8")

    def boom() -> None:
        raise ImportError("mcp extra missing")

    with patch("questline.cli._load_run_stdio", boom):
        result = runner.invoke(
            app,
            ["mcp", "--config", str(cfg), "--profile", "mock"],
        )
    assert result.exit_code == 1
    text = (result.stdout or "") + (result.stderr or "")
    assert "questline[mcp]" in text


def test_mcp_stdio_not_polluted_and_flags(tmp_path: Path) -> None:
    cfg = tmp_path / "questline.toml"
    cfg.write_text('[profile.mock]\ndriver = "mock"\n', encoding="utf-8")
    seen: dict[str, object] = {}

    def fake_run(ctx: object) -> None:
        seen["ctx"] = ctx

    with patch("questline.cli._load_run_stdio", lambda: fake_run):
        result = runner.invoke(
            app,
            [
                "mcp",
                "--config",
                str(cfg),
                "--profile",
                "mock",
                "--store",
                str(tmp_path / "store.db"),
                "--allow-write",
            ],
        )
    assert result.exit_code == 0, result.stdout + result.stderr
    assert (result.stdout or "").strip() == ""
    assert "stdio" in (result.stderr or "")
    ctx = seen["ctx"]
    assert getattr(ctx, "allow_write") is True
    assert getattr(ctx, "allow_fix") is False


def test_doctor_mentions_mcp_extra(tmp_path: Path) -> None:
    cfg = tmp_path / "questline.toml"
    cfg.write_text('[profile.mock]\ndriver = "mock"\n', encoding="utf-8")
    result = runner.invoke(app, ["doctor", "--config", str(cfg), "--profile", "mock"])
    assert result.exit_code == 0, result.stdout
    assert "mcp extra:" in result.stdout
