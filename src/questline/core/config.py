"""Config / profile loading with layered resolution (architecture §2.1)."""

from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError, field_validator

from questline.core.errors import AuthoringError
from questline.core.waits import WaitPolicy

_ENV_PREFIX = "QUESTLINE_"


class WaitSettings(BaseModel):
    probe: float = 2.0
    deadline: float = 15.0
    interval: float = 0.5

    @field_validator("probe", "deadline", "interval")
    @classmethod
    def _positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("wait timings must be > 0")
        return v

    def to_policy(self) -> WaitPolicy:
        return WaitPolicy(probe=self.probe, deadline=self.deadline, interval=self.interval)


class Settings(BaseModel):
    """Resolved runtime settings for one invocation."""

    model_config = {"arbitrary_types_allowed": True}

    profile: str = "default"
    driver: str | None = None
    device: str | None = None
    reporters: list[str] = Field(default_factory=list)
    wait: WaitSettings = Field(default_factory=WaitSettings)
    log_json: bool = False
    project_root: Path = Field(default_factory=Path.cwd)
    store_dir: Path | None = None

    # Optional secret values — populated only from env, never toml.
    api_key: str | None = None
    slack_token: str | None = None
    slack_webhook: str | None = None
    github_token: str | None = None

    @property
    def questline_dir(self) -> Path:
        return self.store_dir if self.store_dir is not None else self.project_root / ".questline"

    @property
    def store_db(self) -> Path:
        return self.questline_dir / "store.db"

    @property
    def artifacts_dir(self) -> Path:
        return self.questline_dir / "artifacts"

    @property
    def ledger_path(self) -> Path:
        return self.questline_dir / "ledger.jsonl"

    def wait_policy(self) -> WaitPolicy:
        return self.wait.to_policy()


def load_settings(
    *,
    config_path: Path | None = None,
    profile: str | None = None,
    cli_overrides: dict[str, Any] | None = None,
    environ: dict[str, str] | None = None,
    project_root: Path | None = None,
) -> Settings:
    """Load settings with resolution: CLI > env (`QUESTLINE_*`) > profile > defaults.

    Raises AuthoringError with an actionable message on missing/invalid config.
    """
    env = environ if environ is not None else dict(os.environ)
    root = (project_root or Path.cwd()).resolve()
    path = config_path if config_path is not None else root / "questline.toml"

    raw_profiles: dict[str, Any] = {}
    if path.is_file():
        try:
            raw_profiles = _parse_profiles(path)
        except tomllib.TOMLDecodeError as exc:
            raise AuthoringError(
                f"Invalid TOML in {path}: {exc}. Fix the syntax and retry."
            ) from exc
        _reject_secrets_in_toml(path, raw_profiles)
    elif config_path is not None:
        raise AuthoringError(
            f"Config file not found: {path}. "
            "Create questline.toml or pass an existing --config path."
        )

    profile_name = _resolve_profile_name(profile, cli_overrides, env, raw_profiles)
    profile_data = _profile_table(raw_profiles, profile_name, path if path.is_file() else None)

    merged = _defaults()
    merged = _deep_merge(merged, profile_data)
    merged = _deep_merge(merged, _env_overrides(env))
    if cli_overrides:
        cleaned = {k: v for k, v in cli_overrides.items() if v is not None}
        # Allow CLI to pass wait as WaitSettings-compatible dict or flat keys.
        if "wait" in cleaned and isinstance(cleaned["wait"], WaitPolicy):
            wp = cleaned.pop("wait")
            cleaned["wait"] = {
                "probe": wp.probe,
                "deadline": wp.deadline,
                "interval": wp.interval,
            }
        merged = _deep_merge(merged, cleaned)

    merged["profile"] = profile_name
    merged["project_root"] = root
    merged = _deep_merge(merged, _secret_env_values(env))

    try:
        return Settings.model_validate(merged)
    except ValidationError as exc:
        raise AuthoringError(_format_validation_error(exc, path)) from exc


def _defaults() -> dict[str, Any]:
    return {
        "profile": "default",
        "driver": None,
        "device": None,
        "reporters": [],
        "wait": {"probe": 2.0, "deadline": 15.0, "interval": 0.5},
        "log_json": False,
    }


def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    """Merge *overlay* onto *base*; nested dicts (e.g. wait) merge field-by-field."""
    out = dict(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def _parse_profiles(path: Path) -> dict[str, Any]:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    profiles: dict[str, Any] = {}
    nested = data.get("profile")
    if isinstance(nested, dict):
        for name, table in nested.items():
            if isinstance(table, dict):
                profiles[name] = table
    # Also accept flat keys like [profile.editor] already nested by tomllib.
    return profiles


def _reject_secrets_in_toml(path: Path, profiles: dict[str, Any]) -> None:
    secret_field_names = {
        "api_key",
        "slack_token",
        "slack_webhook",
        "github_token",
        "openai_api_key",
        "mistral_api_key",
        "password",
        "secret",
        "token",
    }
    for name, table in profiles.items():
        for key in table:
            lowered = key.lower()
            if (
                lowered in secret_field_names
                or lowered.endswith("_token")
                or lowered.endswith("_key")
            ):
                raise AuthoringError(
                    f"Secret field '{key}' found in [profile.{name}] of {path}. "
                    f"Secrets must be provided via environment variables "
                    f"(e.g. QUESTLINE_{key.upper()}), never in questline.toml."
                )


def _resolve_profile_name(
    explicit: str | None,
    cli_overrides: dict[str, Any] | None,
    env: dict[str, str],
    profiles: dict[str, Any],
) -> str:
    if explicit:
        return explicit
    if cli_overrides and cli_overrides.get("profile"):
        return str(cli_overrides["profile"])
    if env.get(f"{_ENV_PREFIX}PROFILE"):
        return env[f"{_ENV_PREFIX}PROFILE"]
    if "default" in profiles:
        return "default"
    if len(profiles) == 1:
        return next(iter(profiles))
    if profiles:
        # Prefer a conventional name if present, else first sorted for stability.
        for candidate in ("editor", "ci", "local"):
            if candidate in profiles:
                return candidate
        return sorted(profiles)[0]
    return "default"


def _profile_table(
    profiles: dict[str, Any],
    name: str,
    path: Path | None,
) -> dict[str, Any]:
    if name == "default" and name not in profiles:
        return {}
    if name not in profiles:
        available = ", ".join(sorted(profiles)) or "(none)"
        location = str(path) if path else "questline.toml"
        raise AuthoringError(
            f"Profile '{name}' not found in {location}. "
            f"Available profiles: {available}. "
            f"Fix the name or add a [profile.{name}] table."
        )
    table = dict(profiles[name])
    # Normalize wait sub-table
    wait = table.get("wait")
    if wait is not None and not isinstance(wait, dict):
        raise AuthoringError(
            f"[profile.{name}].wait must be a table "
            f"(e.g. wait.probe = 2.0), got {type(wait).__name__}."
        )
    return table


def _env_overrides(env: dict[str, str]) -> dict[str, Any]:
    mapping: dict[str, Any] = {}
    simple = {
        f"{_ENV_PREFIX}DRIVER": "driver",
        f"{_ENV_PREFIX}DEVICE": "device",
    }
    for env_key, field_name in simple.items():
        if env_key in env and env[env_key] != "":
            mapping[field_name] = env[env_key]

    if f"{_ENV_PREFIX}REPORTERS" in env:
        raw = env[f"{_ENV_PREFIX}REPORTERS"].strip()
        mapping["reporters"] = [p.strip() for p in raw.split(",") if p.strip()] if raw else []

    if f"{_ENV_PREFIX}LOG_JSON" in env:
        mapping["log_json"] = _parse_bool(env[f"{_ENV_PREFIX}LOG_JSON"], f"{_ENV_PREFIX}LOG_JSON")

    wait: dict[str, float] = {}
    for suffix, key in (
        ("WAIT_PROBE", "probe"),
        ("WAIT_DEADLINE", "deadline"),
        ("WAIT_INTERVAL", "interval"),
    ):
        env_key = f"{_ENV_PREFIX}{suffix}"
        if env_key in env and env[env_key] != "":
            try:
                wait[key] = float(env[env_key])
            except ValueError as exc:
                raise AuthoringError(
                    f"Environment variable {env_key}={env[env_key]!r} is not a number. "
                    f"Set it to a positive float (seconds)."
                ) from exc
    if wait:
        mapping["wait"] = wait
    return mapping


def _secret_env_values(env: dict[str, str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    pairs = (
        ("QUESTLINE_API_KEY", "api_key"),
        ("QUESTLINE_SLACK_TOKEN", "slack_token"),
        ("QUESTLINE_SLACK_WEBHOOK", "slack_webhook"),
        ("QUESTLINE_GITHUB_TOKEN", "github_token"),
    )
    for env_key, field_name in pairs:
        if env_key in env and env[env_key]:
            out[field_name] = env[env_key]
    return out


def _parse_bool(raw: str, name: str) -> bool:
    lowered = raw.strip().lower()
    if lowered in {"1", "true", "yes", "on"}:
        return True
    if lowered in {"0", "false", "no", "off"}:
        return False
    raise AuthoringError(f"Environment variable {name}={raw!r} is not a boolean. Use true/false.")


def _format_validation_error(exc: ValidationError, path: Path) -> str:
    parts: list[str] = [f"Invalid configuration while loading {path}:"]
    for err in exc.errors():
        loc = ".".join(str(x) for x in err["loc"]) or "(root)"
        parts.append(f"  - {loc}: {err['msg']}")
    parts.append("Fix the named keys in questline.toml, CLI flags, or QUESTLINE_* env vars.")
    return "\n".join(parts)
