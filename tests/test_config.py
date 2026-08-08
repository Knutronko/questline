"""Config / profile resolution tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from questline.core.config import load_settings
from questline.core.errors import AuthoringError


def _write_toml(path: Path, body: str) -> Path:
    path.write_text(body.strip() + "\n", encoding="utf-8")
    return path


def test_loads_profile_from_toml(tmp_path: Path) -> None:
    cfg = _write_toml(
        tmp_path / "questline.toml",
        """
        [profile.editor]
        driver = "mock"
        device = "local"
        reporters = ["console"]
        wait.deadline = 20.0
        """,
    )
    settings = load_settings(config_path=cfg, profile="editor", project_root=tmp_path, environ={})
    assert settings.profile == "editor"
    assert settings.driver == "mock"
    assert settings.device == "local"
    assert settings.reporters == ["console"]
    assert settings.wait.deadline == 20.0
    assert settings.wait.probe == 2.0  # default preserved


def test_resolution_order_cli_over_env_over_profile(tmp_path: Path) -> None:
    cfg = _write_toml(
        tmp_path / "questline.toml",
        """
        [profile.ci]
        driver = "from-profile"
        wait.deadline = 10.0
        """,
    )
    env = {
        "QUESTLINE_DRIVER": "from-env",
        "QUESTLINE_WAIT_DEADLINE": "40",
    }
    settings = load_settings(
        config_path=cfg,
        profile="ci",
        project_root=tmp_path,
        environ=env,
        cli_overrides={"driver": "from-cli"},
    )
    assert settings.driver == "from-cli"
    assert settings.wait.deadline == 40.0
    assert settings.wait.probe == 2.0  # env partial wait must not wipe other fields


def test_env_profile_selection(tmp_path: Path) -> None:
    cfg = _write_toml(
        tmp_path / "questline.toml",
        """
        [profile.editor]
        driver = "mock"
        [profile.ci]
        driver = "ci-mock"
        """,
    )
    settings = load_settings(
        config_path=cfg,
        project_root=tmp_path,
        environ={"QUESTLINE_PROFILE": "ci"},
    )
    assert settings.profile == "ci"
    assert settings.driver == "ci-mock"


def test_missing_profile_names_fix(tmp_path: Path) -> None:
    cfg = _write_toml(
        tmp_path / "questline.toml",
        """
        [profile.editor]
        driver = "mock"
        """,
    )
    with pytest.raises(AuthoringError, match="Profile 'missing' not found"):
        load_settings(config_path=cfg, profile="missing", project_root=tmp_path, environ={})


def test_secrets_rejected_in_toml(tmp_path: Path) -> None:
    cfg = _write_toml(
        tmp_path / "questline.toml",
        """
        [profile.editor]
        api_key = "leaked"
        """,
    )
    with pytest.raises(AuthoringError, match="Secrets must be provided via environment"):
        load_settings(config_path=cfg, profile="editor", project_root=tmp_path, environ={})


def test_secrets_from_env_only(tmp_path: Path) -> None:
    cfg = _write_toml(
        tmp_path / "questline.toml",
        """
        [profile.editor]
        driver = "mock"
        """,
    )
    settings = load_settings(
        config_path=cfg,
        profile="editor",
        project_root=tmp_path,
        environ={"QUESTLINE_API_KEY": "sekrit", "QUESTLINE_GITHUB_TOKEN": "gh"},
    )
    assert settings.api_key == "sekrit"
    assert settings.github_token == "gh"


def test_missing_config_path_errors(tmp_path: Path) -> None:
    missing = tmp_path / "nope.toml"
    with pytest.raises(AuthoringError, match="Config file not found"):
        load_settings(config_path=missing, project_root=tmp_path, environ={})


def test_default_without_toml(tmp_path: Path) -> None:
    settings = load_settings(project_root=tmp_path, environ={})
    assert settings.profile == "default"
    assert settings.wait.deadline == 15.0
    assert settings.store_db == tmp_path / ".questline" / "store.db"


def test_invalid_wait_env(tmp_path: Path) -> None:
    with pytest.raises(AuthoringError, match="QUESTLINE_WAIT_PROBE"):
        load_settings(
            project_root=tmp_path,
            environ={"QUESTLINE_WAIT_PROBE": "nope"},
        )


def test_wait_policy_helper_and_store_dir(tmp_path: Path) -> None:
    settings = load_settings(
        project_root=tmp_path,
        environ={},
        cli_overrides={"store_dir": tmp_path / "custom-store"},
    )
    policy = settings.wait_policy()
    assert policy.deadline == 15.0
    assert settings.questline_dir == tmp_path / "custom-store"


def test_negative_wait_is_validation_error(tmp_path: Path) -> None:
    cfg = _write_toml(
        tmp_path / "questline.toml",
        """
        [profile.editor]
        wait.probe = -1
        """,
    )
    with pytest.raises(AuthoringError, match="wait.probe|Invalid configuration"):
        load_settings(config_path=cfg, profile="editor", project_root=tmp_path, environ={})


def test_log_json_and_reporters_env(tmp_path: Path) -> None:
    settings = load_settings(
        project_root=tmp_path,
        environ={
            "QUESTLINE_LOG_JSON": "true",
            "QUESTLINE_REPORTERS": "console, slack",
            "QUESTLINE_DEVICE": "phone",
        },
    )
    assert settings.log_json is True
    assert settings.reporters == ["console", "slack"]
    assert settings.device == "phone"


def test_invalid_bool_env(tmp_path: Path) -> None:
    with pytest.raises(AuthoringError, match="not a boolean"):
        load_settings(project_root=tmp_path, environ={"QUESTLINE_LOG_JSON": "maybe"})


def test_single_profile_auto_selected(tmp_path: Path) -> None:
    cfg = _write_toml(
        tmp_path / "questline.toml",
        """
        [profile.only]
        driver = "mock"
        """,
    )
    settings = load_settings(config_path=cfg, project_root=tmp_path, environ={})
    assert settings.profile == "only"


def test_invalid_toml(tmp_path: Path) -> None:
    cfg = tmp_path / "questline.toml"
    cfg.write_text("this = [bad", encoding="utf-8")
    with pytest.raises(AuthoringError, match="Invalid TOML"):
        load_settings(config_path=cfg, project_root=tmp_path, environ={})


def test_wait_not_a_table(tmp_path: Path) -> None:
    cfg = _write_toml(
        tmp_path / "questline.toml",
        """
        [profile.editor]
        wait = "nope"
        """,
    )
    with pytest.raises(AuthoringError, match="must be a table"):
        load_settings(config_path=cfg, profile="editor", project_root=tmp_path, environ={})


def test_cli_profile_override_and_wait_policy_obj(tmp_path: Path) -> None:
    from questline.core.waits import WaitPolicy

    cfg = _write_toml(
        tmp_path / "questline.toml",
        """
        [profile.editor]
        driver = "mock"
        [profile.ci]
        driver = "ci"
        """,
    )
    settings = load_settings(
        config_path=cfg,
        project_root=tmp_path,
        environ={},
        cli_overrides={
            "profile": "ci",
            "wait": WaitPolicy(probe=1.0, deadline=9.0, interval=0.1),
        },
    )
    assert settings.profile == "ci"
    assert settings.wait.deadline == 9.0


def test_android_local_settings_from_env(tmp_path: Path) -> None:
    settings = load_settings(
        project_root=tmp_path,
        environ={
            "QUESTLINE_DEVICE_SERIAL": "emulator-5554",
            "QUESTLINE_APK_PATH": "C:/game.apk",
            "QUESTLINE_APP_PACKAGE": "com.example",
            "QUESTLINE_INSTALL_APK": "false",
            "QUESTLINE_REVERSE_PORT": "13000",
            "QUESTLINE_EMULATOR_AVD": "Pixel_6",
        },
    )
    assert settings.device_serial == "emulator-5554"
    assert settings.apk_path == "C:/game.apk"
    assert settings.app_package == "com.example"
    assert settings.install_apk is False
    assert settings.reverse_port == 13000
    assert settings.emulator_avd == "Pixel_6"


def test_conventional_profile_preference(tmp_path: Path) -> None:
    cfg = _write_toml(
        tmp_path / "questline.toml",
        """
        [profile.zebra]
        driver = "z"
        [profile.editor]
        driver = "mock"
        """,
    )
    settings = load_settings(config_path=cfg, project_root=tmp_path, environ={})
    assert settings.profile == "editor"
