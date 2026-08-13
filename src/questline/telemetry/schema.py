"""Thin telemetry catalog (FP-G2) and reserved later names (D12 / G2+)."""

from __future__ import annotations

SCHEMA_VERSION = 1
DRAIN_BATCH_SIZE = 500
RING_CAPACITY = 10_000

# Session envelope ``source`` values.
SOURCE_WIRE = "wire"
SOURCE_SPOOL = "spool"
SOURCE_IMPORT = "import"
SOURCES = frozenset({SOURCE_WIRE, SOURCE_SPOOL, SOURCE_IMPORT})

THIN_EVENT_NAMES = frozenset(
    {
        "session.start",
        "session.end",
        "session.checkpoint",
        "currency.earned",
        "currency.spent",
        "unit.deployed",
        "combat.leak",
        "wave.started",
        "wave.completed",
        "skill.cast",
        "repair.applied",
    }
)

# Reserved names for D12 / richer G2+. Core stores them if emitted (unknown-name
# policy) but does not roll them into the thin summary. Later phases must reuse
# these strings — do not invent a parallel vocabulary.
FUTURE_EVENT_NAMES = frozenset(
    {
        "combat.damage",
        "projectile.spawn",
        "projectile.hit",
        "projectile.dissipate",
        "creature.grown",
        "buff.picked",
        "buff.skipped",
        "unit.relocated",
        "session.revive",
        "enemy.spawn",
    }
)

# Companion hooks (Wire call_hook / InvokeHook).
HOOK_BEGIN_SESSION = "BeginTelemetrySession"
HOOK_END_SESSION = "EndTelemetrySession"
HOOK_SET_CONTEXT = "SetTelemetryContext"
HOOK_DRAIN = "DrainTelemetry"
HOOK_STATUS = "TelemetryStatus"
