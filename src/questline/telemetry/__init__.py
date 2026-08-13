"""Gameplay telemetry ingest, summaries, and Wire drain helper (FP-G2)."""

from __future__ import annotations

from questline.telemetry.drain import DRAIN_HOOK, drain_telemetry
from questline.telemetry.ingest import ingest_spool_dict, ingest_spool_file
from questline.telemetry.schema import (
    FUTURE_EVENT_NAMES,
    THIN_EVENT_NAMES,
)
from questline.telemetry.spool import load_spool, validate_spool
from questline.telemetry.summary import compute_summary, diff_summaries

__all__ = [
    "DRAIN_HOOK",
    "FUTURE_EVENT_NAMES",
    "THIN_EVENT_NAMES",
    "compute_summary",
    "diff_summaries",
    "drain_telemetry",
    "ingest_spool_dict",
    "ingest_spool_file",
    "load_spool",
    "validate_spool",
]
