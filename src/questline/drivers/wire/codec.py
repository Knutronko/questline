"""Serialize / deserialize Wire UI payloads to DriverPort types (ADR-0008)."""

from __future__ import annotations

import base64
from typing import Any

from questline.core.errors import AuthoringError
from questline.drivers.port import Element, HierarchyNode, HierarchySnapshot


def element_to_dict(el: Element) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": el.id,
        "name": el.name,
        "path": el.path,
        "text": el.text,
        "visible": el.visible,
        "enabled": el.enabled,
    }
    if el.component is not None:
        payload["component"] = el.component
    if el.bounds is not None:
        payload["bounds"] = list(el.bounds)
    if el.attrs:
        payload["attrs"] = dict(el.attrs)
    return payload


def element_from_dict(raw: Any) -> Element:
    if not isinstance(raw, dict):
        raise AuthoringError("wire element must be an object")
    eid = raw.get("id")
    if not isinstance(eid, str) or not eid:
        raise AuthoringError("wire element.id must be a non-empty string")
    bounds = _parse_bounds(raw.get("bounds"))
    attrs_raw = raw.get("attrs") or {}
    if not isinstance(attrs_raw, dict):
        raise AuthoringError("wire element.attrs must be an object")
    attrs = {str(k): str(v) for k, v in attrs_raw.items()}
    component = raw.get("component")
    return Element(
        id=eid,
        name=str(raw.get("name") or ""),
        path=str(raw.get("path") or ""),
        text=str(raw.get("text") or ""),
        visible=bool(raw.get("visible", True)),
        enabled=bool(raw.get("enabled", True)),
        component=str(component) if isinstance(component, str) else None,
        bounds=bounds,
        attrs=attrs,
    )


def hierarchy_from_dict(raw: Any) -> HierarchySnapshot:
    if not isinstance(raw, dict):
        raise AuthoringError("wire hierarchy result must be an object")
    roots_raw = raw.get("roots")
    if not isinstance(roots_raw, list):
        raise AuthoringError("wire hierarchy.roots must be an array")
    roots = tuple(_node_from_dict(n) for n in roots_raw)
    scene = raw.get("scene")
    return HierarchySnapshot(
        roots=roots,
        scene=scene if isinstance(scene, str) else None,
    )


def hierarchy_to_dict(
    snap: HierarchySnapshot,
    *,
    truncated: bool = False,
    node_count: int | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "roots": [_node_to_dict(n) for n in snap.roots],
        "scene": snap.scene,
        "truncated": truncated,
    }
    if node_count is not None:
        payload["node_count"] = node_count
    return payload


def png_from_result(raw: Any) -> bytes:
    """Decode screenshot result; never return empty bytes on success."""
    if not isinstance(raw, dict):
        raise AuthoringError("wire screenshot result must be an object")
    b64 = raw.get("png_base64")
    if not isinstance(b64, str):
        raise AuthoringError("wire screenshot missing png_base64")
    if not b64:
        raise AuthoringError("wire screenshot returned empty PNG payload")
    try:
        data = base64.b64decode(b64, validate=True)
    except Exception as exc:
        raise AuthoringError(f"wire screenshot base64 decode failed: {exc}") from exc
    if not data:
        raise AuthoringError("wire screenshot returned empty PNG payload")
    return data


def png_to_result(data: bytes) -> dict[str, str]:
    if not data:
        raise AuthoringError("screenshot bytes must be non-empty")
    return {"png_base64": base64.b64encode(data).decode("ascii")}


def _node_from_dict(raw: Any) -> HierarchyNode:
    if not isinstance(raw, dict):
        raise AuthoringError("wire hierarchy node must be an object")
    el_raw = raw.get("element")
    children_raw = raw.get("children") or []
    if not isinstance(children_raw, list):
        raise AuthoringError("wire hierarchy node.children must be an array")
    return HierarchyNode(
        element=element_from_dict(el_raw),
        children=tuple(_node_from_dict(c) for c in children_raw),
    )


def _node_to_dict(node: HierarchyNode) -> dict[str, Any]:
    return {
        "element": element_to_dict(node.element),
        "children": [_node_to_dict(c) for c in node.children],
    }


def _parse_bounds(raw: Any) -> tuple[float, float, float, float] | None:
    if raw is None:
        return None
    if not isinstance(raw, (list, tuple)) or len(raw) != 4:
        raise AuthoringError("wire element.bounds must be [x, y, w, h]")
    try:
        return (float(raw[0]), float(raw[1]), float(raw[2]), float(raw[3]))
    except (TypeError, ValueError) as exc:
        raise AuthoringError("wire element.bounds must be numeric") from exc
