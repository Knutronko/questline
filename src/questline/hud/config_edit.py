"""Profile / questline.toml edit helpers for the HUD (same pydantic path as CLI)."""

from __future__ import annotations

import tomllib
from difflib import unified_diff
from pathlib import Path
from typing import Any

from questline.core.config import Settings, load_settings
from questline.core.errors import AuthoringError

# Shown as env names only — never values in HUD responses.
_SECRET_ENV_NAMES = (
    "QUESTLINE_API_KEY",
    "QUESTLINE_SLACK_TOKEN",
    "QUESTLINE_SLACK_WEBHOOK",
    "QUESTLINE_GITHUB_TOKEN",
)

_SECRET_TOML_KEYS = frozenset(
    {
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
)


def list_profile_names(config_path: Path) -> list[str]:
    profiles = _raw_profiles(config_path)
    return sorted(profiles)


def get_profile_public(config_path: Path, name: str) -> dict[str, Any]:
    """Return profile table with secrets stripped; list env names for secrets."""
    profiles = _raw_profiles(config_path)
    if name not in profiles:
        available = ", ".join(sorted(profiles)) or "(none)"
        raise AuthoringError(
            f"Profile '{name}' not found in {config_path}. Available: {available}."
        )
    table = _strip_secrets(dict(profiles[name]))
    return {
        "name": name,
        "path": str(config_path),
        "fields": table,
        "secret_env_names": list(_SECRET_ENV_NAMES),
    }


def validate_profile_patch(
    config_path: Path,
    name: str,
    fields: dict[str, Any],
    *,
    project_root: Path | None = None,
) -> dict[str, Any]:
    """Validate *fields* as a profile using the same load_settings path as CLI."""
    _reject_secret_keys(fields)
    root = project_root or config_path.parent
    # Write to a temp overlay by merging into an in-memory TOML via load_settings
    # against a temporary file so ValidationError formatting matches CLI.
    import tempfile

    profiles = _raw_profiles(config_path) if config_path.is_file() else {}
    merged_profiles = dict(profiles)
    merged_profiles[name] = fields
    text = emit_profiles_toml(merged_profiles)
    with tempfile.NamedTemporaryFile(
        "w", suffix=".toml", delete=False, encoding="utf-8"
    ) as fh:
        fh.write(text)
        tmp = Path(fh.name)
    try:
        settings = load_settings(
            config_path=tmp,
            profile=name,
            project_root=root,
            environ={},  # ignore ambient env for editor validation parity
        )
        return {
            "ok": True,
            "errors": [],
            "settings_summary": _settings_public_summary(settings),
        }
    except AuthoringError as exc:
        return {"ok": False, "errors": [str(exc)], "settings_summary": None}
    finally:
        tmp.unlink(missing_ok=True)


def preview_and_save_profile(
    config_path: Path,
    name: str,
    fields: dict[str, Any],
    *,
    project_root: Path | None = None,
    apply: bool = False,
) -> dict[str, Any]:
    """Validate, show unified diff, optionally write questline.toml."""
    _reject_secret_keys(fields)
    validation = validate_profile_patch(
        config_path, name, fields, project_root=project_root
    )
    if not validation["ok"]:
        return {
            "ok": False,
            "errors": validation["errors"],
            "diff": "",
            "saved": False,
        }

    before = config_path.read_text(encoding="utf-8") if config_path.is_file() else ""
    profiles = _raw_profiles(config_path) if config_path.is_file() else {}
    profiles[name] = fields
    after = emit_profiles_toml(profiles)
    diff = "".join(
        unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=str(config_path),
            tofile=str(config_path),
        )
    )
    saved = False
    if apply:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(after, encoding="utf-8")
        saved = True
    return {
        "ok": True,
        "errors": [],
        "diff": diff,
        "saved": saved,
        "settings_summary": validation.get("settings_summary"),
    }


def emit_profiles_toml(profiles: dict[str, Any]) -> str:
    """Emit a minimal questline.toml from profile tables (no secret keys)."""
    lines = [
        "# Written by questline HUD profile editor. Secrets stay in env only.",
        "",
    ]
    for name in sorted(profiles):
        table = _strip_secrets(dict(profiles[name]))
        lines.append(f"[profile.{name}]")
        lines.extend(_emit_table(table, prefix=""))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _raw_profiles(config_path: Path) -> dict[str, Any]:
    if not config_path.is_file():
        return {}
    data = tomllib.loads(config_path.read_text(encoding="utf-8"))
    nested = data.get("profile")
    if not isinstance(nested, dict):
        return {}
    out: dict[str, Any] = {}
    for name, table in nested.items():
        if isinstance(table, dict):
            out[str(name)] = table
    return out


def _strip_secrets(table: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in table.items():
        lowered = key.lower()
        if (
            lowered in _SECRET_TOML_KEYS
            or lowered.endswith("_token")
            or lowered.endswith("_key")
        ):
            continue
        if isinstance(value, dict):
            out[key] = _strip_secrets(value)
        else:
            out[key] = value
    return out


def _reject_secret_keys(fields: dict[str, Any]) -> None:
    for key in fields:
        lowered = key.lower()
        if (
            lowered in _SECRET_TOML_KEYS
            or lowered.endswith("_token")
            or lowered.endswith("_key")
        ):
            raise AuthoringError(
                f"Secret field '{key}' must not appear in HUD/profile TOML. "
                f"Use environment variables (e.g. QUESTLINE_{key.upper()})."
            )
        value = fields[key]
        if isinstance(value, dict):
            _reject_secret_keys(value)


def _settings_public_summary(settings: Settings) -> dict[str, Any]:
    return {
        "profile": settings.profile,
        "driver": settings.driver,
        "device": settings.device,
        "reporters": list(settings.reporters),
        "target_host": settings.target_host,
        "target_port": settings.target_port,
        "target_platform": settings.target_platform,
        "device_serial": settings.device_serial,
        "perf_enabled": settings.perf.enabled,
        "secret_env_names": list(_SECRET_ENV_NAMES),
    }


def _emit_table(table: dict[str, Any], *, prefix: str) -> list[str]:
    lines: list[str] = []
    scalars: list[tuple[str, Any]] = []
    nested: list[tuple[str, dict[str, Any]]] = []
    for key, value in table.items():
        if isinstance(value, dict):
            nested.append((key, value))
        else:
            scalars.append((key, value))
    for key, value in scalars:
        dotted = f"{prefix}.{key}" if prefix else key
        lines.append(f"{dotted} = {_toml_literal(value)}")
    for key, value in nested:
        child_prefix = f"{prefix}.{key}" if prefix else key
        for ck, cv in value.items():
            if isinstance(cv, dict):
                lines.extend(_emit_table({ck: cv}, prefix=child_prefix))
            else:
                lines.append(f"{child_prefix}.{ck} = {_toml_literal(cv)}")
    return lines


def _toml_literal(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, str):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    if isinstance(value, list):
        return "[ " + ", ".join(_toml_literal(v) for v in value) + " ]"
    raise AuthoringError(f"Unsupported TOML value type: {type(value).__name__}")
