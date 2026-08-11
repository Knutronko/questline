"""Config: PerfSettings opt-in via toml / env."""

from __future__ import annotations

from pathlib import Path

from questline.core.config import load_settings


def test_perf_defaults_disabled(tmp_path: Path) -> None:
    settings = load_settings(project_root=tmp_path, environ={})
    assert settings.perf.enabled is False
    assert settings.perf.interval_s == 1.0
    assert settings.perf.scope == "test"
    assert settings.perf.source == "auto"


def test_perf_profile_and_env(tmp_path: Path) -> None:
    cfg = tmp_path / "questline.toml"
    cfg.write_text(
        """
[profile.android_local]
driver = "questline"
device = "adb"
perf.enabled = true
perf.interval_s = 0.5
perf.scope = "run"
perf.source = "android"
perf.metrics = ["fps", "memory_pss_mb"]
""".strip()
        + "\n",
        encoding="utf-8",
    )
    settings = load_settings(
        config_path=cfg,
        profile="android_local",
        project_root=tmp_path,
        environ={"QUESTLINE_PERF_INTERVAL_S": "0.25"},
    )
    assert settings.perf.enabled is True
    assert settings.perf.interval_s == 0.25  # env wins
    assert settings.perf.scope == "run"
    assert settings.perf.source == "android"
    assert settings.perf.metrics == ["fps", "memory_pss_mb"]
