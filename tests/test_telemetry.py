"""Telemetry ingest, summary, drain helper, and CLI (FP-G2)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from questline.cli import app
from questline.core.errors import AuthoringError
from questline.core.migrations import CURRENT_SCHEMA_VERSION
from questline.core.store import RunStore
from questline.telemetry.drain import drain_telemetry
from questline.telemetry.ingest import ingest_spool_file
from questline.telemetry.schema import DRAIN_BATCH_SIZE, FUTURE_EVENT_NAMES, THIN_EVENT_NAMES
from questline.telemetry.spool import validate_spool
from questline.telemetry.summary import diff_summaries

FIXTURES = Path(__file__).parent / "fixtures" / "telemetry"
runner = CliRunner()


def test_catalog_disjoint() -> None:
    assert THIN_EVENT_NAMES.isdisjoint(FUTURE_EVENT_NAMES)
    assert "session.checkpoint" in THIN_EVENT_NAMES
    assert "combat.damage" in FUTURE_EVENT_NAMES


def test_ingest_summary_and_unknown_events(tmp_path: Path) -> None:
    db = tmp_path / "store.db"
    with RunStore(db) as store:
        result = ingest_spool_file(store, FIXTURES / "sess-a.json")
        assert result["id"] == "sess-a"
        assert result["event_count"] == 14
        summary = result["summary"]
        assert summary["deploy_count"] == 1
        assert summary["skill_casts"] == 1
        assert summary["repair_count"] == 1
        assert summary["leak_count"] == 1
        assert summary["time_to_first_leak"] == 42.5
        assert summary["waves_started"] == 2
        assert summary["waves_completed"] == 1
        assert summary["outcome"] == "lose"
        assert summary["currency_in"]["soft"] == 25
        assert summary["currency_out"]["soft"] == 130
        assert summary["currency_net"]["soft"] == -105
        assert "combat.damage" in summary["unknown_event_names"]
        assert "prep_end" in summary["checkpoint_labels"]
        assert store.count_telemetry_events("sess-a") == 14
        row = store.get_telemetry_session("sess-a")
        assert row is not None
        assert row["config_snapshot_id"] == "1.0.0"
        assert row["seed"] == "42"
        prefix = store.get_telemetry_session("sess-")
        assert prefix is not None and prefix["id"] == "sess-a"


def test_reimport_replaces_same_id(tmp_path: Path) -> None:
    db = tmp_path / "store.db"
    with RunStore(db) as store:
        ingest_spool_file(store, FIXTURES / "sess-a.json")
        ingest_spool_file(store, FIXTURES / "sess-a.json")
        assert store.count_telemetry_events("sess-a") == 14


def test_missing_game_version_rejected() -> None:
    data = {
        "schema_version": 1,
        "session": {
            "id": "x",
            "started_at": "2026-08-13T00:00:00+00:00",
            "source": "import",
        },
        "events": [],
    }
    with pytest.raises(AuthoringError, match="game_version"):
        validate_spool(data)


def test_bom_spool_imports(tmp_path: Path) -> None:
    src = (FIXTURES / "sess-b.json").read_bytes()
    bom = tmp_path / "bom.json"
    bom.write_bytes(b"\xef\xbb\xbf" + src)
    db = tmp_path / "store.db"
    with RunStore(db) as store:
        result = ingest_spool_file(store, bom)
        assert result["id"] == "sess-b"
        assert result["summary"]["leak_count"] == 0
        assert result["summary"]["unknown_event_names"] == []


def test_compare_summaries(tmp_path: Path) -> None:
    db = tmp_path / "store.db"
    with RunStore(db) as store:
        ingest_spool_file(store, FIXTURES / "sess-a.json")
        ingest_spool_file(store, FIXTURES / "sess-b.json")
        a = store.get_telemetry_session("sess-a")["summary"]
        b = store.get_telemetry_session("sess-b")["summary"]
        deltas = diff_summaries(a, b)
        assert deltas["leak_count"] == -1
        assert deltas["deploy_count"] == 0


def test_cli_import_query_compare(tmp_path: Path) -> None:
    db = tmp_path / "store.db"
    r1 = runner.invoke(
        app, ["telemetry", "import", str(FIXTURES / "sess-a.json"), "--store", str(db)]
    )
    assert r1.exit_code == 0, r1.output
    assert "id=sess-a" in r1.output
    r2 = runner.invoke(
        app, ["telemetry", "import", str(FIXTURES / "sess-b.json"), "--store", str(db)]
    )
    assert r2.exit_code == 0, r2.output

    listed = runner.invoke(app, ["telemetry", "query", "--store", str(db)])
    assert listed.exit_code == 0, listed.output
    assert "sess-a" in listed.output
    assert "sess-b" in listed.output

    detail = runner.invoke(app, ["telemetry", "query", "sess-a", "--store", str(db)])
    assert detail.exit_code == 0, detail.output
    assert "leak_count: 1" in detail.output
    assert "unknown_event_names" in detail.output

    js = runner.invoke(
        app, ["telemetry", "query", "sess-a", "--format", "json", "--store", str(db)]
    )
    assert js.exit_code == 0, js.output
    payload = json.loads(js.output)
    assert payload["id"] == "sess-a"
    assert payload["event_count"] == 14
    assert payload["events"][0]["name"] == "session.start"

    cmp_r = runner.invoke(
        app,
        ["telemetry", "query", "sess-a", "--compare", "sess-b", "--store", str(db)],
    )
    assert cmp_r.exit_code == 0, cmp_r.output
    assert "leak_count: -1" in cmp_r.output


def test_drain_helper_ingests(tmp_path: Path) -> None:
    spool = json.loads((FIXTURES / "sess-a.json").read_text(encoding="utf-8"))

    first = [
        {
            "seq": i + 1,
            "t": 0.0,
            "name": "session.checkpoint",
            "payload": {"label": "pad"},
        }
        for i in range(DRAIN_BATCH_SIZE)
    ]
    rest = []
    for i, ev in enumerate(spool["events"]):
        item = dict(ev)
        item["seq"] = DRAIN_BATCH_SIZE + i + 1
        rest.append(item)
    batches = [
        {"session": spool["session"], "dropped_count": 0, "events": first},
        {"session": spool["session"], "dropped_count": 0, "events": rest},
    ]

    class FakeDriver:
        def __init__(self) -> None:
            self.i = 0
            self.ended: str | None = None

        def call_game_method(self, hook: object, *args: object) -> object:
            name = getattr(hook, "name", "")
            if name == "EndTelemetrySession":
                self.ended = str(args[0]) if args else ""
                return "{}"
            batch = batches[self.i]
            self.i += 1
            return batch

    db = tmp_path / "store.db"
    with RunStore(db) as store:
        fake = FakeDriver()
        result = drain_telemetry(fake, store, end_outcome="lose", run_id="run-1")
        assert fake.ended == "lose"
        assert fake.i == 2
        assert result["ingested"]["event_count"] == DRAIN_BATCH_SIZE + 14
        row = store.get_telemetry_session("sess-a")
        assert row is not None
        assert row["run_id"] == "run-1"
        assert row["source"] == "wire"


def test_no_reference_game_names_in_core() -> None:
    root = Path(__file__).resolve().parents[1] / "src" / "questline"
    banned = (
        "ElJuegaso",
        "P1Debug",
        "Deploy.Dino",
        "Amber.Gain",
        "Fossil.Tick",
        "Dientes",
        "ieb-",
    )
    hits: list[str] = []
    for path in root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for token in banned:
            if token in text:
                hits.append(f"{path.relative_to(root)}: {token}")
    assert hits == []


def test_fresh_store_includes_telemetry_tables(tmp_path: Path) -> None:
    db = tmp_path / "t.db"
    with RunStore(db) as store:
        assert store.schema_version == CURRENT_SCHEMA_VERSION
        assert CURRENT_SCHEMA_VERSION >= 4
        assert store.list_telemetry_sessions() == []
