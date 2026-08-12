"""Typed balance snapshot diff (includes new/removed entities as first-class)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from questline.lens.snapshot import BalanceSnapshot

DiffKind = Literal[
    "changed",
    "added_entity",
    "removed_entity",
    "curve_changed",
    "series_changed",
]


@dataclass(frozen=True, slots=True)
class DiffEntry:
    kind: DiffKind
    system: str
    entity_id: str
    path: str | None = None
    before: Any = None
    after: Any = None
    delta: float | None = None
    pct: float | None = None
    entity: dict[str, Any] | None = None  # full block for added/removed

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "system": self.system,
            "entity_id": self.entity_id,
            "path": self.path,
            "before": self.before,
            "after": self.after,
            "delta": self.delta,
            "pct": self.pct,
            "entity": self.entity,
        }


@dataclass(frozen=True, slots=True)
class DiffReport:
    version_a: str
    version_b: str
    snapshot_id_a: str | None
    snapshot_id_b: str | None
    entries: tuple[DiffEntry, ...]
    feature_id: str | None = None

    def by_system(self) -> dict[str, list[DiffEntry]]:
        grouped: dict[str, list[DiffEntry]] = {}
        for entry in self.entries:
            grouped.setdefault(entry.system, []).append(entry)
        return grouped

    def to_dict(self) -> dict[str, Any]:
        return {
            "version_a": self.version_a,
            "version_b": self.version_b,
            "snapshot_id_a": self.snapshot_id_a,
            "snapshot_id_b": self.snapshot_id_b,
            "feature_id": self.feature_id,
            "entries": [e.to_dict() for e in self.entries],
            "by_system": {
                system: [e.to_dict() for e in items]
                for system, items in sorted(self.by_system().items())
            },
        }


def diff_snapshots(
    snap_a: BalanceSnapshot,
    snap_b: BalanceSnapshot,
    *,
    snapshot_id_a: str | None = None,
    snapshot_id_b: str | None = None,
) -> DiffReport:
    """Compute typed diffs from snap_a → snap_b (B is the newer / right side)."""
    entries: list[DiffEntry] = []
    ids_a = set(snap_a.entities)
    ids_b = set(snap_b.entities)

    for eid in sorted(ids_b - ids_a):
        entity = snap_b.entities[eid]
        entries.append(
            DiffEntry(
                kind="added_entity",
                system=str(entity.get("system") or "unknown"),
                entity_id=eid,
                entity=entity,
            )
        )

    for eid in sorted(ids_a - ids_b):
        entity = snap_a.entities[eid]
        entries.append(
            DiffEntry(
                kind="removed_entity",
                system=str(entity.get("system") or "unknown"),
                entity_id=eid,
                entity=entity,
            )
        )

    for eid in sorted(ids_a & ids_b):
        ea = snap_a.entities[eid]
        eb = snap_b.entities[eid]
        system = str(eb.get("system") or ea.get("system") or "unknown")
        fields_a = ea.get("fields") if isinstance(ea.get("fields"), dict) else {}
        fields_b = eb.get("fields") if isinstance(eb.get("fields"), dict) else {}
        entries.extend(_diff_fields(system, eid, fields_a, fields_b, prefix=""))

    feature_id = snap_b.meta.feature_id or snap_a.meta.feature_id
    return DiffReport(
        version_a=snap_a.meta.game_version,
        version_b=snap_b.meta.game_version,
        snapshot_id_a=snapshot_id_a,
        snapshot_id_b=snapshot_id_b,
        entries=tuple(entries),
        feature_id=feature_id,
    )


def _diff_fields(
    system: str,
    entity_id: str,
    a: dict[str, Any],
    b: dict[str, Any],
    *,
    prefix: str,
) -> list[DiffEntry]:
    out: list[DiffEntry] = []
    keys = sorted(set(a) | set(b))
    for key in keys:
        path = f"{prefix}.{key}" if prefix else key
        fa = a.get(key)
        fb = b.get(key)
        if fa is None and fb is not None:
            out.append(
                DiffEntry(
                    kind="changed",
                    system=system,
                    entity_id=entity_id,
                    path=path,
                    before=None,
                    after=_field_payload(fb),
                )
            )
            continue
        if fb is None and fa is not None:
            out.append(
                DiffEntry(
                    kind="changed",
                    system=system,
                    entity_id=entity_id,
                    path=path,
                    before=_field_payload(fa),
                    after=None,
                )
            )
            continue
        if not isinstance(fa, dict) or not isinstance(fb, dict):
            continue
        ta = fa.get("type")
        tb = fb.get("type")
        if ta == "object" and tb == "object":
            nested_a = fa.get("fields") if isinstance(fa.get("fields"), dict) else {}
            nested_b = fb.get("fields") if isinstance(fb.get("fields"), dict) else {}
            out.extend(
                _diff_fields(system, entity_id, nested_a, nested_b, prefix=path)
            )
            continue
        if ta == "curve" or tb == "curve":
            pa = fa.get("points")
            pb = fb.get("points")
            if pa != pb:
                out.append(
                    DiffEntry(
                        kind="curve_changed",
                        system=system,
                        entity_id=entity_id,
                        path=path,
                        before=pa,
                        after=pb,
                    )
                )
            continue
        if ta == "series" or tb == "series":
            va = fa.get("values")
            vb = fb.get("values")
            if va != vb:
                out.append(
                    DiffEntry(
                        kind="series_changed",
                        system=system,
                        entity_id=entity_id,
                        path=path,
                        before=va,
                        after=vb,
                    )
                )
            continue
        if ta == "number" and tb == "number":
            before = float(fa.get("value"))
            after = float(fb.get("value"))
            if before == after:
                continue
            delta = after - before
            pct = None if before == 0 else (delta / before) * 100.0
            out.append(
                DiffEntry(
                    kind="changed",
                    system=system,
                    entity_id=entity_id,
                    path=path,
                    before=before,
                    after=after,
                    delta=delta,
                    pct=pct,
                )
            )
            continue
        before_v = fa.get("value")
        after_v = fb.get("value")
        if before_v != after_v or ta != tb:
            out.append(
                DiffEntry(
                    kind="changed",
                    system=system,
                    entity_id=entity_id,
                    path=path,
                    before=before_v if ta == tb else _field_payload(fa),
                    after=after_v if ta == tb else _field_payload(fb),
                )
            )
    return out


def _field_payload(field: Any) -> Any:
    if not isinstance(field, dict):
        return field
    ftype = field.get("type")
    if ftype == "object":
        return {"type": "object", "fields": field.get("fields")}
    if ftype == "curve":
        return {"type": "curve", "points": field.get("points")}
    if ftype == "series":
        return {"type": "series", "values": field.get("values")}
    return field.get("value")
