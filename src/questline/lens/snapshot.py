"""Normalize raw balance dumps into a stable balance_snapshot.json shape."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from questline.core.errors import AuthoringError
from questline.lens.manifest import BalanceManifest, ManifestEntry, load_manifest

SNAPSHOT_SCHEMA_VERSION = 1
_FIELD_TYPES = frozenset({"number", "string", "bool", "curve", "series", "object", "null"})


@dataclass(frozen=True, slots=True)
class SnapshotMeta:
    game_version: str
    git_commit: str | None = None
    feature_id: str | None = None
    captured_at: str | None = None
    manifest_path: str | None = None


@dataclass(frozen=True, slots=True)
class BalanceSnapshot:
    schema_version: int
    meta: SnapshotMeta
    entities: dict[str, dict[str, Any]]
    supplementary: tuple[dict[str, Any], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "meta": {
                "game_version": self.meta.game_version,
                "git_commit": self.meta.git_commit,
                "feature_id": self.meta.feature_id,
                "captured_at": self.meta.captured_at,
                "manifest_path": self.meta.manifest_path,
            },
            "entities": self.entities,
            "supplementary": list(self.supplementary),
        }


def write_snapshot(snapshot: BalanceSnapshot, path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(snapshot.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def load_snapshot(path: Path) -> BalanceSnapshot:
    path = Path(path)
    if not path.is_file():
        raise AuthoringError(f"snapshot not found: {path}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise AuthoringError(f"snapshot is not valid JSON: {path}: {exc}") from exc
    return parse_snapshot(raw, source=str(path))


def parse_snapshot(raw: Any, *, source: str = "<memory>") -> BalanceSnapshot:
    if not isinstance(raw, dict):
        raise AuthoringError(f"snapshot root must be an object ({source})")
    version = raw.get("schema_version", SNAPSHOT_SCHEMA_VERSION)
    if version != SNAPSHOT_SCHEMA_VERSION:
        raise AuthoringError(
            f"unsupported snapshot schema_version={version!r} "
            f"(expected {SNAPSHOT_SCHEMA_VERSION}) in {source}"
        )
    meta_raw = raw.get("meta")
    if not isinstance(meta_raw, dict):
        raise AuthoringError(f"snapshot.meta must be an object ({source})")
    game_version = meta_raw.get("game_version")
    if not isinstance(game_version, str) or not game_version.strip():
        raise AuthoringError(f"snapshot.meta.game_version is required ({source})")
    entities_raw = raw.get("entities")
    if not isinstance(entities_raw, dict):
        raise AuthoringError(f"snapshot.entities must be an object ({source})")
    entities: dict[str, dict[str, Any]] = {}
    for eid, entity in entities_raw.items():
        if not isinstance(eid, str) or not isinstance(entity, dict):
            raise AuthoringError(f"snapshot.entities[{eid!r}] invalid ({source})")
        entities[eid] = _normalize_entity(eid, entity, source=source)
    supp = raw.get("supplementary") or []
    if not isinstance(supp, list):
        raise AuthoringError(f"snapshot.supplementary must be a list ({source})")
    return BalanceSnapshot(
        schema_version=int(version),
        meta=SnapshotMeta(
            game_version=game_version.strip(),
            git_commit=_opt_str(meta_raw.get("git_commit")),
            feature_id=_opt_str(meta_raw.get("feature_id")),
            captured_at=_opt_str(meta_raw.get("captured_at")),
            manifest_path=_opt_str(meta_raw.get("manifest_path")),
        ),
        entities=entities,
        supplementary=tuple(s for s in supp if isinstance(s, dict)),
    )


def normalize_pack(
    pack_dir: Path,
    *,
    game_version: str,
    git_commit: str | None = None,
    feature_id: str | None = None,
    manifest_name: str = "manifest.json",
) -> BalanceSnapshot:
    """Build a normalized snapshot from a fixture/export pack directory.

    Expected layout::

        pack/
          manifest.json
          raw/<source_file>   # JSON dumps referenced by entry.source_file
          # optional files for supplementary paths (relative to pack or absolute)
    """
    pack_dir = Path(pack_dir)
    if not pack_dir.is_dir():
        raise AuthoringError(f"snapshot pack directory not found: {pack_dir}")
    manifest_path = pack_dir / manifest_name
    manifest = load_manifest(manifest_path)
    entities: dict[str, dict[str, Any]] = {}
    for entry in manifest.entries:
        raw_obj = _load_entry_raw(pack_dir, entry)
        entities[entry.id] = {
            "id": entry.id,
            "system": entry.system,
            "kind": entry.kind,
            "fields": normalize_fields(raw_obj),
        }
    supplementary = _collect_supplementary(pack_dir, manifest)
    return BalanceSnapshot(
        schema_version=SNAPSHOT_SCHEMA_VERSION,
        meta=SnapshotMeta(
            game_version=game_version.strip(),
            git_commit=git_commit,
            feature_id=feature_id,
            captured_at=datetime.now(timezone.utc).isoformat(),
            manifest_path=str(manifest_path),
        ),
        entities=entities,
        supplementary=tuple(supplementary),
    )


def normalize_fields(raw: Any) -> dict[str, Any]:
    """Convert an arbitrary JSON-ish object into typed field map."""
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise AuthoringError(
            f"entity raw dump must be a JSON object, got {type(raw).__name__}"
        )
    # Allow already-normalized {"fields": {...}} or {"type","value"} leaves.
    if "fields" in raw and isinstance(raw["fields"], dict) and _looks_normalized(
        raw["fields"]
    ):
        return {k: _coerce_field(v) for k, v in raw["fields"].items()}
    if _looks_normalized(raw):
        return {k: _coerce_field(v) for k, v in raw.items()}
    return {k: _infer_field(v) for k, v in raw.items() if not str(k).startswith("_")}


def _looks_normalized(obj: dict[str, Any]) -> bool:
    if not obj:
        return False
    sample = next(iter(obj.values()))
    return isinstance(sample, dict) and "type" in sample


def _coerce_field(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or "type" not in value:
        raise AuthoringError(f"normalized field missing type: {value!r}")
    ftype = value["type"]
    if ftype not in _FIELD_TYPES:
        raise AuthoringError(f"unknown field type: {ftype!r}")
    if ftype == "object":
        nested = value.get("fields")
        if not isinstance(nested, dict):
            raise AuthoringError("object field requires fields map")
        return {"type": "object", "fields": {k: _coerce_field(v) for k, v in nested.items()}}
    if ftype == "null":
        return {"type": "null", "value": None}
    if ftype in {"curve", "series"}:
        key = "points" if ftype == "curve" else "values"
        if key not in value:
            raise AuthoringError(f"{ftype} field requires {key}")
        return {"type": ftype, key: value[key]}
    if "value" not in value:
        raise AuthoringError(f"{ftype} field requires value")
    return {"type": ftype, "value": value["value"]}


def _infer_field(value: Any) -> dict[str, Any]:
    if value is None:
        return {"type": "null", "value": None}
    if isinstance(value, bool):
        return {"type": "bool", "value": value}
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return {"type": "number", "value": float(value)}
    if isinstance(value, str):
        return {"type": "string", "value": value}
    if isinstance(value, list):
        if _is_curve(value):
            return {"type": "curve", "points": _as_curve_points(value)}
        if all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in value):
            return {"type": "series", "values": [float(x) for x in value]}
        # Mixed / nested lists → JSON string for stable compare (not numerically diffed).
        return {"type": "string", "value": json.dumps(value, sort_keys=True)}
    if isinstance(value, dict):
        # Unity AnimationCurve-ish: {keys:[{time,value},...]}
        if "keys" in value and isinstance(value["keys"], list) and _is_curve_keys(
            value["keys"]
        ):
            return {
                "type": "curve",
                "points": [
                    [float(k["time"]), float(k["value"])]
                    for k in value["keys"]
                    if isinstance(k, dict)
                ],
            }
        return {
            "type": "object",
            "fields": {
                k: _infer_field(v)
                for k, v in value.items()
                if not str(k).startswith("_")
            },
        }
    return {"type": "string", "value": str(value)}


def _is_curve(value: list[Any]) -> bool:
    if not value:
        return False
    for point in value:
        if isinstance(point, (list, tuple)) and len(point) >= 2:
            if not all(isinstance(point[i], (int, float)) for i in (0, 1)):
                return False
            continue
        if isinstance(point, dict) and "time" in point and "value" in point:
            continue
        return False
    return True


def _is_curve_keys(keys: list[Any]) -> bool:
    if not keys:
        return False
    return all(
        isinstance(k, dict) and "time" in k and "value" in k for k in keys
    )


def _as_curve_points(value: list[Any]) -> list[list[float]]:
    points: list[list[float]] = []
    for point in value:
        if isinstance(point, dict):
            points.append([float(point["time"]), float(point["value"])])
        else:
            points.append([float(point[0]), float(point[1])])
    return points


def _load_entry_raw(pack_dir: Path, entry: ManifestEntry) -> Any:
    if not entry.source_file:
        raise AuthoringError(
            f"manifest entry {entry.id!r} has no source_file; "
            "cannot import without Unity export (use companion exporter or add "
            "source_file pointing at a JSON dump)"
        )
    path = Path(entry.source_file)
    if not path.is_absolute():
        # Prefer pack root, then pack/raw/
        candidates = [pack_dir / path, pack_dir / "raw" / path]
        path = next((c for c in candidates if c.is_file()), candidates[0])
    if not path.is_file():
        raise AuthoringError(
            f"missing source_file for entry {entry.id!r}: {entry.source_file} "
            f"(resolved {path})"
        )
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise AuthoringError(
            f"invalid JSON for entry {entry.id!r} at {path}: {exc}"
        ) from exc


def _collect_supplementary(
    pack_dir: Path, manifest: BalanceManifest
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for ref in manifest.supplementary:
        path = Path(ref.path)
        if not path.is_absolute():
            path = pack_dir / path
        item: dict[str, Any] = {"kind": ref.kind, "path": ref.path, "present": path.is_file()}
        if path.is_file():
            data = path.read_bytes()
            item["sha256"] = hashlib.sha256(data).hexdigest()
            item["size_bytes"] = len(data)
        out.append(item)
    return out


def _normalize_entity(eid: str, entity: dict[str, Any], *, source: str) -> dict[str, Any]:
    system = entity.get("system")
    if not isinstance(system, str) or not system.strip():
        raise AuthoringError(f"entity {eid!r} missing system ({source})")
    fields_raw = entity.get("fields", entity)
    if not isinstance(fields_raw, dict):
        raise AuthoringError(f"entity {eid!r} fields must be an object ({source})")
    # If entity already has id/system/kind wrapper, take fields only.
    if "fields" in entity and isinstance(entity["fields"], dict):
        fields = normalize_fields(entity)
    else:
        fields = normalize_fields(fields_raw)
    return {
        "id": entity.get("id", eid),
        "system": system.strip(),
        "kind": str(entity.get("kind") or "config"),
        "fields": fields,
    }


def _opt_str(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        return text or None
    return str(value)
