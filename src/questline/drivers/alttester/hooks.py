"""Companion hooks manifest — re-exports shared types (backward compatible)."""

from __future__ import annotations

from questline.drivers.hooks import (
    HOOKS_ASSEMBLY,
    HOOKS_TYPE_NAME,
    INVOKE_METHOD,
    MANIFEST_METHOD,
    HookArgSpec,
    HookManifestEntry,
    decode_invoke_result,
    encode_invoke_args,
    parse_hooks_manifest,
)

__all__ = [
    "HOOKS_ASSEMBLY",
    "HOOKS_TYPE_NAME",
    "INVOKE_METHOD",
    "MANIFEST_METHOD",
    "HookArgSpec",
    "HookManifestEntry",
    "decode_invoke_result",
    "encode_invoke_args",
    "parse_hooks_manifest",
]
