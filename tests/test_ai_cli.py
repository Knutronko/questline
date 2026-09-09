"""CLI: doctor AI section, ai costs, ai complete with fake provider."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from questline.cli import app
from questline.core.events import AiCallMade, EventBus, RunStarted
from questline.core.store import RunStore

runner = CliRunner()


def _fake_toml(path: Path) -> Path:
    path.write_text(
        """
[profile.fake_ai]
driver = "mock"
ai.candidates = ["fake"]
ai.budget_per_call_usd = 10
ai.budget_per_run_usd = 10
[profile.fake_ai.ai.providers.fake]
kind = "fake"
model = "fake-test"
""",
        encoding="utf-8",
    )
    return path


def test_doctor_lists_fake_provider(tmp_path: Path) -> None:
    cfg = _fake_toml(tmp_path / "questline.toml")
    result = runner.invoke(
        app,
        ["doctor", "--config", str(cfg), "--profile", "fake_ai", "--no-ping"],
    )
    assert result.exit_code == 0, result.stdout + result.stderr
    assert "ai:" in result.stdout
    assert "fake" in result.stdout
    assert "ai ping:     skipped" in result.stdout


def test_doctor_ping_fake(tmp_path: Path) -> None:
    cfg = _fake_toml(tmp_path / "questline.toml")
    result = runner.invoke(
        app,
        ["doctor", "--config", str(cfg), "--profile", "fake_ai"],
    )
    assert result.exit_code == 0, result.stdout + result.stderr
    assert "OK" in result.stdout
    assert "fake" in result.stdout


def test_ai_complete_fake(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = _fake_toml(tmp_path / "questline.toml")
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(
        app,
        [
            "ai",
            "complete",
            "--config",
            str(cfg),
            "--profile",
            "fake_ai",
            "--run",
            "smoke",
            "Reply with the single word pong.",
        ],
    )
    assert result.exit_code == 0, result.stdout + result.stderr
    assert "provider: fake" in result.stdout
    costs = runner.invoke(
        app,
        ["ai", "costs", "--config", str(cfg), "--profile", "fake_ai", "--run", "smoke"],
    )
    assert costs.exit_code == 0, costs.stdout + costs.stderr
    assert "fake" in costs.stdout
    assert "total_usd:" in costs.stdout


def test_ai_costs_from_store(tmp_path: Path) -> None:
    store = RunStore(tmp_path / "store.db")
    bus = EventBus()
    store.attach(bus)
    try:
        bus.publish(RunStarted(run_id="r1", profile="mock"))
        bus.publish(
            AiCallMade(
                run_id="r1",
                provider="ollama",
                model="llama3.2",
                tokens_in=10,
                tokens_out=2,
                cost=0.0,
                purpose="cli.complete",
                duration_ms=5.0,
                outcome="ok",
                pricing_version="1",
            )
        )
    finally:
        store.close()
    result = runner.invoke(app, ["ai", "costs", "--store", str(tmp_path / "store.db")])
    assert result.exit_code == 0, result.stdout + result.stderr
    assert "ollama" in result.stdout
    assert "0.000000" in result.stdout
