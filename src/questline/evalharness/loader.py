"""Load goldens/*.yaml from the packaged eval harness."""

from __future__ import annotations

from importlib.resources import files
from typing import Any

import yaml

from questline.evalharness.schema import FAILURE_CLASSES, GoldenCase


def load_goldens() -> list[GoldenCase]:
    root = files("questline.evalharness.goldens")
    cases: list[GoldenCase] = []
    names = sorted(p.name for p in root.iterdir() if p.name.endswith((".yaml", ".yml")))
    for name in names:
        raw = root.joinpath(name).read_text(encoding="utf-8")
        data = yaml.safe_load(raw) or {}
        if not isinstance(data, dict):
            continue
        cases.append(_parse_case(data, source=name))
    cases.sort(key=lambda c: c.id)
    return cases


def _parse_case(data: dict[str, Any], *, source: str) -> GoldenCase:
    failure = str(data.get("failure_class") or "").strip().lower()
    if failure not in FAILURE_CLASSES:
        raise ValueError(f"{source}: unknown failure_class {failure!r}")
    reply = data.get("reply") if isinstance(data.get("reply"), dict) else {}
    actually = data.get("actually_green")
    return GoldenCase(
        id=str(data.get("id") or source),
        failure_class=failure,
        cause=str(data.get("cause") or "unknown"),
        expected_fix_class=str(data.get("expected_fix_class") or "none"),
        agent=str(data.get("agent") or "maintainer"),
        mode=str(data.get("mode") or "diagnose"),
        score_fix=bool(data.get("score_fix")),
        error_type=str(data.get("error_type") or "AssertionError"),
        error_message=str(data.get("error_message") or "golden"),
        store_verdict=str(data.get("store_verdict") or "test"),
        summary=str(data.get("summary") or ""),
        reply=dict(reply),
        sabotage_gate=bool(data.get("sabotage_gate")),
        gate_green=bool(data.get("gate_green")),
        actually_green=None if actually is None else bool(actually),
        setup=str(data.get("setup") or ""),
    )
