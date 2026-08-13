"""Ordered SQLite schema migrations for the run store.

Future modules add tables (features, feature_links, telemetry, eval_results, …)
by appending a migration here — never by rewriting the bootstrap script in place.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable, Sequence
from dataclasses import dataclass

MigrateFn = Callable[[sqlite3.Connection], None]


@dataclass(frozen=True, slots=True)
class Migration:
    version: int
    name: str
    apply: MigrateFn


def _migrate_001_initial_core(conn: sqlite3.Connection) -> None:
    """Create the phase-01 core tables (idempotent CREATE IF NOT EXISTS)."""
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS runs (
            id TEXT PRIMARY KEY,
            profile TEXT,
            started_at TEXT NOT NULL,
            finished_at TEXT,
            status TEXT,
            meta TEXT
        );

        CREATE TABLE IF NOT EXISTS tests (
            id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL REFERENCES runs(id),
            nodeid TEXT NOT NULL,
            started_at TEXT,
            finished_at TEXT,
            status TEXT,
            verdict TEXT,
            error_type TEXT,
            error_message TEXT
        );

        CREATE TABLE IF NOT EXISTS steps (
            id TEXT PRIMARY KEY,
            test_id TEXT NOT NULL REFERENCES tests(id),
            run_id TEXT NOT NULL,
            name TEXT NOT NULL,
            started_at TEXT NOT NULL,
            finished_at TEXT,
            status TEXT,
            error_message TEXT
        );

        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT,
            test_id TEXT,
            step_id TEXT,
            type TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            payload TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS perf_samples (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT,
            test_id TEXT,
            metric TEXT NOT NULL,
            value REAL NOT NULL,
            timestamp TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS ai_calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT,
            provider TEXT,
            model TEXT,
            tokens_in INTEGER,
            tokens_out INTEGER,
            cost REAL,
            purpose TEXT,
            duration_ms REAL,
            timestamp TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS quarantine (
            test_id TEXT PRIMARY KEY,
            reason TEXT NOT NULL,
            entered_at TEXT NOT NULL,
            owner TEXT,
            exit_criteria TEXT,
            linked_issue TEXT,
            left_at TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_tests_run ON tests(run_id);
        CREATE INDEX IF NOT EXISTS idx_steps_test ON steps(test_id);
        CREATE INDEX IF NOT EXISTS idx_events_run ON events(run_id);
        """
    )


def _migrate_002_tests_feature_id(conn: sqlite3.Connection) -> None:
    """Add nullable feature_id to tests (feature-pipeline tagging hook)."""
    cols = {row[1] for row in conn.execute("PRAGMA table_info(tests)").fetchall()}
    if "feature_id" not in cols:
        conn.execute("ALTER TABLE tests ADD COLUMN feature_id TEXT")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_tests_feature ON tests(feature_id)"
    )


def _migrate_003_balance_snapshots(conn: sqlite3.Connection) -> None:
    """GameLens FP-G1: balance snapshot index (artifact JSON on disk)."""
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS balance_snapshots (
            id TEXT PRIMARY KEY,
            game_version TEXT NOT NULL,
            git_commit TEXT,
            feature_id TEXT,
            artifact_path TEXT NOT NULL,
            created_at TEXT NOT NULL,
            meta TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_balance_snapshots_version
            ON balance_snapshots(game_version);
        CREATE INDEX IF NOT EXISTS idx_balance_snapshots_feature
            ON balance_snapshots(feature_id);
        CREATE INDEX IF NOT EXISTS idx_balance_snapshots_created
            ON balance_snapshots(created_at);
        """
    )


def _migrate_004_telemetry(conn: sqlite3.Connection) -> None:
    """FP-G2: gameplay telemetry sessions + events (measured truth)."""
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS telemetry_sessions (
            id TEXT PRIMARY KEY,
            game_version TEXT NOT NULL,
            git_commit TEXT,
            feature_id TEXT,
            config_snapshot_id TEXT,
            policy_id TEXT,
            seed TEXT,
            started_at TEXT NOT NULL,
            finished_at TEXT,
            outcome TEXT,
            source TEXT NOT NULL,
            run_id TEXT,
            artifact_path TEXT,
            summary TEXT,
            meta TEXT,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_tel_sessions_version
            ON telemetry_sessions(game_version);
        CREATE INDEX IF NOT EXISTS idx_tel_sessions_snapshot
            ON telemetry_sessions(config_snapshot_id);
        CREATE INDEX IF NOT EXISTS idx_tel_sessions_policy
            ON telemetry_sessions(policy_id);
        CREATE INDEX IF NOT EXISTS idx_tel_sessions_feature
            ON telemetry_sessions(feature_id);
        CREATE INDEX IF NOT EXISTS idx_tel_sessions_created
            ON telemetry_sessions(created_at);

        CREATE TABLE IF NOT EXISTS telemetry_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL REFERENCES telemetry_sessions(id),
            seq INTEGER NOT NULL,
            t REAL NOT NULL,
            name TEXT NOT NULL,
            payload TEXT NOT NULL,
            UNIQUE(session_id, seq)
        );
        CREATE INDEX IF NOT EXISTS idx_tel_events_session
            ON telemetry_events(session_id);
        CREATE INDEX IF NOT EXISTS idx_tel_events_name
            ON telemetry_events(name);
        """
    )


# Append-only: new modules add the next integer version here.
MIGRATIONS: tuple[Migration, ...] = (
    Migration(1, "initial_core_schema", _migrate_001_initial_core),
    Migration(2, "tests_feature_id", _migrate_002_tests_feature_id),
    Migration(3, "balance_snapshots", _migrate_003_balance_snapshots),
    Migration(4, "telemetry", _migrate_004_telemetry),
)

CURRENT_SCHEMA_VERSION: int = MIGRATIONS[-1].version


def ensure_schema_version_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )


def get_schema_version(conn: sqlite3.Connection) -> int:
    """Return the highest applied migration version, or 0 if none."""
    ensure_schema_version_table(conn)
    row = conn.execute("SELECT MAX(version) AS v FROM schema_version").fetchone()
    if row is None or row[0] is None:
        return 0
    return int(row[0])


def apply_migrations(
    conn: sqlite3.Connection,
    migrations: Sequence[Migration] = MIGRATIONS,
) -> list[int]:
    """Apply pending migrations in ascending version order.

    Returns the list of newly applied versions. Each migration runs in its own
    transaction together with the ``schema_version`` insert.
    """
    ensure_schema_version_table(conn)
    current = get_schema_version(conn)
    applied: list[int] = []

    for migration in sorted(migrations, key=lambda m: m.version):
        if migration.version <= current:
            continue
        if applied and migration.version != applied[-1] + 1:
            raise RuntimeError(
                f"Non-contiguous migration set: after {applied[-1]} came "
                f"{migration.version} ({migration.name})."
            )
        if not applied and current > 0 and migration.version != current + 1:
            raise RuntimeError(
                f"Migration gap: schema_version={current}, next is "
                f"{migration.version} ({migration.name})."
            )
        if not applied and current == 0 and migration.version != 1:
            # Fresh/legacy DBs must start at version 1.
            raise RuntimeError(
                f"First migration must be version 1, got {migration.version} ({migration.name})."
            )

        migration.apply(conn)
        conn.execute(
            "INSERT INTO schema_version (version, name) VALUES (?, ?)",
            (migration.version, migration.name),
        )
        current = migration.version
        applied.append(migration.version)

    return applied
