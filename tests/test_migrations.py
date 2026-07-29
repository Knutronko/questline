"""Schema migration tests — old stores must upgrade cleanly on open."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from questline.core.events import EventBus, RunStarted
from questline.core.migrations import (
    CURRENT_SCHEMA_VERSION,
    Migration,
    _migrate_001_initial_core,
    apply_migrations,
    get_schema_version,
)
from questline.core.store import RunStore

# Pre-migration layout: core tables, no schema_version (legacy phase-01 DB).
_LEGACY_SCHEMA = """
CREATE TABLE runs (
    id TEXT PRIMARY KEY,
    profile TEXT,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT,
    meta TEXT
);
CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT,
    test_id TEXT,
    step_id TEXT,
    type TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    payload TEXT NOT NULL
);
"""


def _make_legacy_db(path: Path) -> None:
    conn = sqlite3.connect(str(path))
    conn.executescript(_LEGACY_SCHEMA)
    conn.execute(
        "INSERT INTO runs (id, profile, started_at, status, meta) VALUES (?, ?, ?, ?, ?)",
        ("legacy-run", "editor", "2026-07-01T00:00:00+00:00", "passed", "{}"),
    )
    conn.execute(
        "INSERT INTO events (run_id, type, timestamp, payload) VALUES (?, ?, ?, ?)",
        ("legacy-run", "RunStarted", "2026-07-01T00:00:00+00:00", "{}"),
    )
    conn.commit()
    conn.close()


def test_fresh_store_is_at_current_schema_version(tmp_path: Path) -> None:
    with RunStore(tmp_path / "fresh.db") as store:
        assert store.schema_version == CURRENT_SCHEMA_VERSION
        assert CURRENT_SCHEMA_VERSION >= 2


def test_v1_store_upgrades_to_feature_id_column(tmp_path: Path) -> None:
    """A schema_version=1 DB gains tests.feature_id via migration 2."""
    db_path = tmp_path / "v1.db"
    conn = sqlite3.connect(str(db_path))
    conn.isolation_level = None

    apply_migrations(conn, (Migration(1, "initial_core_schema", _migrate_001_initial_core),))
    assert get_schema_version(conn) == 1
    cols = {r[1] for r in conn.execute("PRAGMA table_info(tests)").fetchall()}
    assert "feature_id" not in cols
    conn.close()

    with RunStore(db_path) as store:
        assert store.schema_version == CURRENT_SCHEMA_VERSION
        probe = sqlite3.connect(str(db_path))
        cols = {r[1] for r in probe.execute("PRAGMA table_info(tests)").fetchall()}
        probe.close()
        assert "feature_id" in cols


def test_legacy_store_upgrades_cleanly_preserving_data(tmp_path: Path) -> None:
    """Old store (tables, no schema_version) upgrades on open; data survives."""
    db_path = tmp_path / "legacy.db"
    _make_legacy_db(db_path)

    # Prove it really has no schema_version yet.
    probe = sqlite3.connect(str(db_path))
    names = {
        r[0] for r in probe.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    }
    assert "schema_version" not in names
    assert "runs" in names
    probe.close()

    with RunStore(db_path) as store:
        assert store.schema_version == CURRENT_SCHEMA_VERSION
        run = store.get_run("legacy-run")
        assert run is not None
        assert run["profile"] == "editor"
        assert run["status"] == "passed"
        assert store.count_events("legacy-run") == 1

        # Store remains writable after upgrade.
        bus = EventBus()
        store.attach(bus)
        bus.publish(RunStarted(run_id="post-upgrade", profile="ci"))
        assert store.get_run("post-upgrade") is not None

    # Re-open is a no-op for migrations (idempotent).
    with RunStore(db_path) as store:
        assert store.schema_version == CURRENT_SCHEMA_VERSION
        assert store.get_run("legacy-run") is not None
        assert store.get_run("post-upgrade") is not None


def test_ordered_migrations_apply_sequentially(tmp_path: Path) -> None:
    db_path = tmp_path / "seq.db"
    conn = sqlite3.connect(str(db_path))
    conn.isolation_level = None

    def m1(c: sqlite3.Connection) -> None:
        c.execute("CREATE TABLE IF NOT EXISTS t1 (id INTEGER PRIMARY KEY)")

    def m2(c: sqlite3.Connection) -> None:
        c.execute("ALTER TABLE t1 ADD COLUMN note TEXT")

    migrations = (
        Migration(1, "create_t1", m1),
        Migration(2, "add_note", m2),
    )
    applied = apply_migrations(conn, migrations)
    assert applied == [1, 2]
    assert get_schema_version(conn) == 2

    # Second pass applies nothing.
    assert apply_migrations(conn, migrations) == []
    assert get_schema_version(conn) == 2

    cols = {r[1] for r in conn.execute("PRAGMA table_info(t1)").fetchall()}
    assert "note" in cols
    conn.close()


def test_migration_gap_raises(tmp_path: Path) -> None:
    db_path = tmp_path / "gap.db"
    conn = sqlite3.connect(str(db_path))
    conn.isolation_level = None
    apply_migrations(conn, (Migration(1, "one", lambda c: None),))

    with pytest.raises(RuntimeError, match="Migration gap"):
        apply_migrations(conn, (Migration(3, "three", lambda c: None),))
    conn.close()
