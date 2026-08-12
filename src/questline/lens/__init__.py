"""GameLens: balance snapshot normalize, diff, and AI-report stub (FP-G1)."""

from __future__ import annotations

from questline.lens.diff import DiffReport, diff_snapshots
from questline.lens.manifest import BalanceManifest, load_manifest
from questline.lens.report import ImplicationsReport, implications_stub
from questline.lens.snapshot import (
    BalanceSnapshot,
    load_snapshot,
    normalize_pack,
    write_snapshot,
)

__all__ = [
    "BalanceManifest",
    "BalanceSnapshot",
    "DiffReport",
    "ImplicationsReport",
    "diff_snapshots",
    "implications_stub",
    "load_manifest",
    "load_snapshot",
    "normalize_pack",
    "write_snapshot",
]
