"""Companion hooks manifest (feature-pipeline hook for future feature-scan)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from questline.core.errors import AuthoringError, InfraError

# Stable type / method names for CallStaticMethod against com.questline.companion.
HOOKS_TYPE_NAME = "Questline.Companion.QuestlineHooks"
HOOKS_ASSEMBLY = "Questline.Companion"
MANIFEST_METHOD = "GetManifestJson"
INVOKE_METHOD = "InvokeHook"


@dataclass(frozen=True, slots=True)
class HookArgSpec:
    """One typed argument declared on a registered hook."""

    name: str
    type: str  # C# / logical type label, e.g. "int", "string", "bool"


@dataclass(frozen=True, slots=True)
class HookManifestEntry:
    """One row in the companion hooks registry dump."""

    name: str
    args: tuple[HookArgSpec, ...]
    causes_soft_reload: bool = False
    feature: str | None = None


def parse_hooks_manifest(raw: str | dict[str, Any] | list[Any]) -> list[HookManifestEntry]:
    """Parse the companion registry dump into typed entries.

    Accepted shapes (JSON string or already-decoded):
    - ``{"hooks": [ ... ]}`` (preferred)
    - a bare list of hook objects
    """
    data: Any = raw
    if isinstance(raw, str):
        try:
            data = json.loads(raw) if raw.strip() else {"hooks": []}
        except json.JSONDecodeError as exc:
            raise InfraError(f"hooks manifest is not valid JSON: {exc}") from exc

    if isinstance(data, list):
        hooks_raw = data
    elif isinstance(data, dict):
        hooks_raw = data.get("hooks", data.get("Hooks"))
        if hooks_raw is None:
            raise AuthoringError("hooks manifest JSON must contain a 'hooks' array")
    else:
        raise AuthoringError(
            f"hooks manifest must be a JSON object or array, got {type(data).__name__}"
        )

    if not isinstance(hooks_raw, list):
        raise AuthoringError("hooks manifest 'hooks' must be an array")

    entries: list[HookManifestEntry] = []
    for i, item in enumerate(hooks_raw):
        if not isinstance(item, dict):
            raise AuthoringError(f"hooks[{i}] must be an object")
        name = item.get("name") or item.get("Name")
        if not name or not isinstance(name, str):
            raise AuthoringError(f"hooks[{i}].name must be a non-empty string")
        args_raw = item.get("args") or item.get("Args") or []
        if not isinstance(args_raw, list):
            raise AuthoringError(f"hooks[{i}].args must be an array")
        args: list[HookArgSpec] = []
        for j, arg in enumerate(args_raw):
            if not isinstance(arg, dict):
                raise AuthoringError(f"hooks[{i}].args[{j}] must be an object")
            aname = arg.get("name") or arg.get("Name")
            atype = arg.get("type") or arg.get("Type")
            if not aname or not isinstance(aname, str):
                raise AuthoringError(f"hooks[{i}].args[{j}].name must be a non-empty string")
            if not atype or not isinstance(atype, str):
                raise AuthoringError(f"hooks[{i}].args[{j}].type must be a non-empty string")
            args.append(HookArgSpec(name=aname, type=atype))
        causes = item.get("causesSoftReload", item.get("causes_soft_reload", False))
        if not isinstance(causes, bool):
            raise AuthoringError(f"hooks[{i}].causesSoftReload must be a boolean")
        feature = item.get("feature", item.get("Feature"))
        if feature is not None and not isinstance(feature, str):
            raise AuthoringError(f"hooks[{i}].feature must be a string when present")
        entries.append(
            HookManifestEntry(
                name=name,
                args=tuple(args),
                causes_soft_reload=causes,
                feature=feature,
            )
        )
    return entries


def encode_invoke_args(args: tuple[Any, ...]) -> str:
    """Serialize call_game_method args for QuestlineHooks.InvokeHook."""
    return json.dumps(list(args), separators=(",", ":"))


def decode_invoke_result(raw: Any) -> Any:
    """Decode InvokeHook return value (JSON string or passthrough)."""
    if raw is None:
        return None
    if not isinstance(raw, str):
        return raw
    text = raw.strip()
    if text == "":
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return raw
