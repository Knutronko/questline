"""GameLens: balance snapshot normalize, diff, and AI-report stub (FP-G1)."""

from __future__ import annotations

from questline.lens.diff import DiffReport, diff_snapshots
from questline.lens.manifest import BalanceManifest, load_manifest
from questline.lens.report import (
    ImplicationsReport,
    build_implications,
    implications_stub,
    persist_implications,
)
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
    "build_implications",
    "diff_snapshots",
    "implications_stub",
    "load_manifest",
    "persist_implications",
    "load_snapshot",
    "normalize_pack",
    "write_snapshot",
]
