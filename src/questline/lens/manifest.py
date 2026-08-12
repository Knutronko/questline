"""Balance export manifest — game declares WHICH SOs are balance data (QL-5)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from questline.core.errors import AuthoringError

MANIFEST_SCHEMA_VERSION = 1
_ALLOWED_SUPPLEMENTARY = frozenset({"markdown", "csv", "json", "text"})


@dataclass(frozen=True, slots=True)
class ManifestEntry:
    id: str
    system: str
    asset_path: str | None = None
    source_file: str | None = None
    kind: str = "config"


@dataclass(frozen=True, slots=True)
class SupplementaryRef:
    kind: str
    path: str


@dataclass(frozen=True, slots=True)
class BalanceManifest:
    schema_version: int
    entries: tuple[ManifestEntry, ...]
    supplementary: tuple[SupplementaryRef, ...] = ()
    meta: dict[str, Any] = field(default_factory=dict)

    def entry_by_id(self, entry_id: str) -> ManifestEntry | None:
        for entry in self.entries:
            if entry.id == entry_id:
                return entry
        return None


def load_manifest(path: Path) -> BalanceManifest:
    """Load and validate a GameLens manifest JSON file."""
    path = Path(path)
    if not path.is_file():
        raise AuthoringError(f"manifest not found: {path}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise AuthoringError(f"manifest is not valid JSON: {path}: {exc}") from exc
    return parse_manifest(raw, source=str(path))


def parse_manifest(raw: Any, *, source: str = "<memory>") -> BalanceManifest:
    if not isinstance(raw, dict):
        raise AuthoringError(f"manifest root must be an object ({source})")
    version = raw.get("schema_version", MANIFEST_SCHEMA_VERSION)
    if version != MANIFEST_SCHEMA_VERSION:
        raise AuthoringError(
            f"unsupported manifest schema_version={version!r} "
            f"(expected {MANIFEST_SCHEMA_VERSION}) in {source}"
        )
    entries_raw = raw.get("entries")
    if not isinstance(entries_raw, list) or not entries_raw:
        raise AuthoringError(f"manifest.entries must be a non-empty list ({source})")

    seen: set[str] = set()
    entries: list[ManifestEntry] = []
    for i, item in enumerate(entries_raw):
        if not isinstance(item, dict):
            raise AuthoringError(f"manifest.entries[{i}] must be an object ({source})")
        entry_id = item.get("id")
        system = item.get("system")
        if not isinstance(entry_id, str) or not entry_id.strip():
            raise AuthoringError(f"manifest.entries[{i}].id is required ({source})")
        if not isinstance(system, str) or not system.strip():
            raise AuthoringError(
                f"manifest.entries[{i}].system is required ({source})"
            )
        entry_id = entry_id.strip()
        if entry_id in seen:
            raise AuthoringError(f"duplicate manifest entry id: {entry_id!r} ({source})")
        seen.add(entry_id)
        asset_path = item.get("asset_path")
        source_file = item.get("source_file")
        if asset_path is not None and not isinstance(asset_path, str):
            raise AuthoringError(
                f"manifest.entries[{i}].asset_path must be a string ({source})"
            )
        if source_file is not None and not isinstance(source_file, str):
            raise AuthoringError(
                f"manifest.entries[{i}].source_file must be a string ({source})"
            )
        if not asset_path and not source_file:
            raise AuthoringError(
                f"manifest.entries[{i}] needs asset_path and/or source_file ({source})"
            )
        kind = item.get("kind", "config")
        if not isinstance(kind, str) or not kind.strip():
            raise AuthoringError(f"manifest.entries[{i}].kind invalid ({source})")
        entries.append(
            ManifestEntry(
                id=entry_id,
                system=system.strip(),
                asset_path=asset_path.strip() if isinstance(asset_path, str) else None,
                source_file=source_file.strip() if isinstance(source_file, str) else None,
                kind=kind.strip(),
            )
        )

    supplementary: list[SupplementaryRef] = []
    supp_raw = raw.get("supplementary") or []
    if not isinstance(supp_raw, list):
        raise AuthoringError(f"manifest.supplementary must be a list ({source})")
    for i, item in enumerate(supp_raw):
        if not isinstance(item, dict):
            raise AuthoringError(
                f"manifest.supplementary[{i}] must be an object ({source})"
            )
        kind = item.get("kind")
        path = item.get("path")
        if kind not in _ALLOWED_SUPPLEMENTARY:
            raise AuthoringError(
                f"manifest.supplementary[{i}].kind must be one of "
                f"{sorted(_ALLOWED_SUPPLEMENTARY)} ({source})"
            )
        if not isinstance(path, str) or not path.strip():
            raise AuthoringError(
                f"manifest.supplementary[{i}].path is required ({source})"
            )
        supplementary.append(SupplementaryRef(kind=str(kind), path=path.strip()))

    meta = raw.get("meta") or {}
    if not isinstance(meta, dict):
        raise AuthoringError(f"manifest.meta must be an object ({source})")

    return BalanceManifest(
        schema_version=int(version),
        entries=tuple(entries),
        supplementary=tuple(supplementary),
        meta=dict(meta),
    )
