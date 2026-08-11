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


class ResilienceSettings(BaseModel):
    """Health / recovery / watchdog knobs (phase-06)."""

    watchdog_timeout_s: float = 120.0
    circuit_breaker_losses: int = 3
    recovery_enabled: bool = True

    @field_validator("watchdog_timeout_s")
    @classmethod
    def _positive_timeout(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("watchdog_timeout_s must be > 0")
        return v

    @field_validator("circuit_breaker_losses")
    @classmethod
    def _positive_losses(cls, v: int) -> int:
        if v < 1:
            raise ValueError("circuit_breaker_losses must be >= 1")
        return v


class PerfSettings(BaseModel):
    """Opt-in PerfProbe knobs (phase-09). Off by default."""

    enabled: bool = False
    interval_s: float = 1.0
    scope: str = "test"  # test | run
    source: str = "auto"  # auto | android | companion
    metrics: list[str] = Field(default_factory=list)

    @field_validator("interval_s")
    @classmethod
    def _positive_interval(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("interval_s must be > 0")
        return v

    @field_validator("scope")
    @classmethod
    def _scope_ok(cls, v: str) -> str:
        lowered = v.strip().lower()
        if lowered not in {"test", "run"}:
            raise ValueError("perf.scope must be 'test' or 'run'")
        return lowered

    @field_validator("source")
    @classmethod
    def _source_ok(cls, v: str) -> str:
        lowered = v.strip().lower()
        if lowered not in {"auto", "android", "companion"}:
            raise ValueError("perf.source must be 'auto', 'android', or 'companion'")
        return lowered


class Settings(BaseModel):
    """Resolved runtime settings for one invocation."""

    model_config = {"arbitrary_types_allowed": True}

    profile: str = "default"
    driver: str | None = None
    device: str | None = None
    reporters: list[str] = Field(default_factory=list)
    wait: WaitSettings = Field(default_factory=WaitSettings)
    resilience: ResilienceSettings = Field(default_factory=ResilienceSettings)
    perf: PerfSettings = Field(default_factory=PerfSettings)
    log_json: bool = False
    project_root: Path = Field(default_factory=Path.cwd)
    store_dir: Path | None = None
    # ConnectionTarget fields for real drivers (phase-04 AltTester+).
    target_host: str = "127.0.0.1"
    target_port: int = 13000
    target_platform: str | None = None  # editor | standalone_exe | android
    target_app_name: str | None = None

    # Local adb / android_local (phase-05).
    device_serial: str | None = None
    apk_path: str | None = None
    app_package: str | None = None
    app_activity: str | None = None
    adb_path: str | None = None
    emulator_avd: str | None = None
    emulator_path: str | None = None
    install_apk: bool = True
    reverse_port: int | None = None  # defaults to target_port when android
    expected_app_version: str | None = None

    # Reporter non-secrets (toml / env OK).
    slack_channel: str | None = None
    github_repo: str | None = None  # owner/name
    github_issues_auto_close: bool = False
    github_issues_labels: list[str] = Field(
        default_factory=lambda: ["questline", "test-failure"]
    )

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
        "resilience": {
            "watchdog_timeout_s": 120.0,
            "circuit_breaker_losses": 3,
            "recovery_enabled": True,
        },
        "perf": {
            "enabled": False,
            "interval_s": 1.0,
            "scope": "test",
            "source": "auto",
            "metrics": [],
        },
        "log_json": False,
        "target_host": "127.0.0.1",
        "target_port": 13000,
        "target_platform": None,
        "target_app_name": None,
        "device_serial": None,
        "apk_path": None,
        "app_package": None,
        "app_activity": None,
        "adb_path": None,
        "emulator_avd": None,
        "emulator_path": None,
        "install_apk": True,
        "reverse_port": None,
        "expected_app_version": None,
        "slack_channel": None,
        "github_repo": None,
        "github_issues_auto_close": False,
        "github_issues_labels": ["questline", "test-failure"],
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
    # Normalize wait / resilience / perf sub-tables
    wait = table.get("wait")
    if wait is not None and not isinstance(wait, dict):
        raise AuthoringError(
            f"[profile.{name}].wait must be a table "
            f"(e.g. wait.probe = 2.0), got {type(wait).__name__}."
        )
    resilience = table.get("resilience")
    if resilience is not None and not isinstance(resilience, dict):
        raise AuthoringError(
            f"[profile.{name}].resilience must be a table "
            f"(e.g. resilience.watchdog_timeout_s = 120), got {type(resilience).__name__}."
        )
    perf = table.get("perf")
    if perf is not None and not isinstance(perf, dict):
        raise AuthoringError(
            f"[profile.{name}].perf must be a table "
            f"(e.g. perf.enabled = true), got {type(perf).__name__}."
        )
    return table


def _env_overrides(env: dict[str, str]) -> dict[str, Any]:
    mapping: dict[str, Any] = {}
    simple = {
        f"{_ENV_PREFIX}DRIVER": "driver",
        f"{_ENV_PREFIX}DEVICE": "device",
        f"{_ENV_PREFIX}TARGET_HOST": "target_host",
        f"{_ENV_PREFIX}ALT_HOST": "target_host",
        f"{_ENV_PREFIX}TARGET_PLATFORM": "target_platform",
        f"{_ENV_PREFIX}LIVE_PLATFORM": "target_platform",
        f"{_ENV_PREFIX}TARGET_APP_NAME": "target_app_name",
        f"{_ENV_PREFIX}ALT_APP_NAME": "target_app_name",
        f"{_ENV_PREFIX}DEVICE_SERIAL": "device_serial",
        f"{_ENV_PREFIX}APK_PATH": "apk_path",
        f"{_ENV_PREFIX}APP_PACKAGE": "app_package",
        f"{_ENV_PREFIX}APP_ACTIVITY": "app_activity",
        f"{_ENV_PREFIX}ADB_PATH": "adb_path",
        f"{_ENV_PREFIX}EMULATOR_AVD": "emulator_avd",
        f"{_ENV_PREFIX}EMULATOR_PATH": "emulator_path",
        f"{_ENV_PREFIX}EXPECTED_APP_VERSION": "expected_app_version",
    }
    for env_key, field_name in simple.items():
        if env_key in env and env[env_key] != "":
            mapping[field_name] = env[env_key]

    for env_key in (f"{_ENV_PREFIX}TARGET_PORT", f"{_ENV_PREFIX}ALT_PORT"):
        if env_key in env and env[env_key] != "":
            try:
                mapping["target_port"] = int(env[env_key])
            except ValueError as exc:
                raise AuthoringError(
                    f"Environment variable {env_key}={env[env_key]!r} is not an int port."
                ) from exc
            break

    if f"{_ENV_PREFIX}REPORTERS" in env:
        raw = env[f"{_ENV_PREFIX}REPORTERS"].strip()
        mapping["reporters"] = [p.strip() for p in raw.split(",") if p.strip()] if raw else []

    if f"{_ENV_PREFIX}SLACK_CHANNEL" in env and env[f"{_ENV_PREFIX}SLACK_CHANNEL"]:
        mapping["slack_channel"] = env[f"{_ENV_PREFIX}SLACK_CHANNEL"]

    if f"{_ENV_PREFIX}GITHUB_REPO" in env and env[f"{_ENV_PREFIX}GITHUB_REPO"]:
        mapping["github_repo"] = env[f"{_ENV_PREFIX}GITHUB_REPO"]

    if f"{_ENV_PREFIX}GITHUB_ISSUES_AUTO_CLOSE" in env:
        mapping["github_issues_auto_close"] = _parse_bool(
            env[f"{_ENV_PREFIX}GITHUB_ISSUES_AUTO_CLOSE"],
            f"{_ENV_PREFIX}GITHUB_ISSUES_AUTO_CLOSE",
        )

    if f"{_ENV_PREFIX}GITHUB_ISSUES_LABELS" in env:
        raw_labels = env[f"{_ENV_PREFIX}GITHUB_ISSUES_LABELS"].strip()
        mapping["github_issues_labels"] = (
            [p.strip() for p in raw_labels.split(",") if p.strip()] if raw_labels else []
        )

    if f"{_ENV_PREFIX}LOG_JSON" in env:
        mapping["log_json"] = _parse_bool(env[f"{_ENV_PREFIX}LOG_JSON"], f"{_ENV_PREFIX}LOG_JSON")

    if f"{_ENV_PREFIX}INSTALL_APK" in env:
        mapping["install_apk"] = _parse_bool(
            env[f"{_ENV_PREFIX}INSTALL_APK"], f"{_ENV_PREFIX}INSTALL_APK"
        )

    for env_key, field_name in (
        (f"{_ENV_PREFIX}REVERSE_PORT", "reverse_port"),
    ):
        if env_key in env and env[env_key] != "":
            try:
                mapping[field_name] = int(env[env_key])
            except ValueError as exc:
                raise AuthoringError(
                    f"Environment variable {env_key}={env[env_key]!r} is not an int port."
                ) from exc

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

    resilience: dict[str, Any] = {}
    wto = f"{_ENV_PREFIX}WATCHDOG_TIMEOUT_S"
    if wto in env and env[wto] != "":
        try:
            resilience["watchdog_timeout_s"] = float(env[wto])
        except ValueError as exc:
            raise AuthoringError(
                f"Environment variable {wto}={env[wto]!r} is not a number."
            ) from exc
    cbl = f"{_ENV_PREFIX}CIRCUIT_BREAKER_LOSSES"
    if cbl in env and env[cbl] != "":
        try:
            resilience["circuit_breaker_losses"] = int(env[cbl])
        except ValueError as exc:
            raise AuthoringError(
                f"Environment variable {cbl}={env[cbl]!r} is not an int."
            ) from exc
    if f"{_ENV_PREFIX}RECOVERY_ENABLED" in env:
        resilience["recovery_enabled"] = _parse_bool(
            env[f"{_ENV_PREFIX}RECOVERY_ENABLED"],
            f"{_ENV_PREFIX}RECOVERY_ENABLED",
        )
    if resilience:
        mapping["resilience"] = resilience

    perf: dict[str, Any] = {}
    if f"{_ENV_PREFIX}PERF_ENABLED" in env:
        perf["enabled"] = _parse_bool(
            env[f"{_ENV_PREFIX}PERF_ENABLED"],
            f"{_ENV_PREFIX}PERF_ENABLED",
        )
    p_int = f"{_ENV_PREFIX}PERF_INTERVAL_S"
    if p_int in env and env[p_int] != "":
        try:
            perf["interval_s"] = float(env[p_int])
        except ValueError as exc:
            raise AuthoringError(
                f"Environment variable {p_int}={env[p_int]!r} is not a number."
            ) from exc
    if f"{_ENV_PREFIX}PERF_SCOPE" in env and env[f"{_ENV_PREFIX}PERF_SCOPE"]:
        perf["scope"] = env[f"{_ENV_PREFIX}PERF_SCOPE"]
    if f"{_ENV_PREFIX}PERF_SOURCE" in env and env[f"{_ENV_PREFIX}PERF_SOURCE"]:
        perf["source"] = env[f"{_ENV_PREFIX}PERF_SOURCE"]
    if f"{_ENV_PREFIX}PERF_METRICS" in env:
        raw_m = env[f"{_ENV_PREFIX}PERF_METRICS"].strip()
        perf["metrics"] = [p.strip() for p in raw_m.split(",") if p.strip()] if raw_m else []
    if perf:
        mapping["perf"] = perf
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
