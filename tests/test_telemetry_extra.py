"""Extra telemetry coverage: validation errors, drain edges, CLI failures."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from questline.cli import app
from questline.core.errors import AuthoringError
from questline.core.store import RunStore
from questline.telemetry.drain import drain_telemetry
from questline.telemetry.ingest import ingest_spool_dict, parse_drain_payload
from questline.telemetry.render import render_compare, render_session_list
from questline.telemetry.spool import load_spool, validate_spool

runner = CliRunner()

_MIN = {
    "schema_version": 1,
    "session": {
        "id": "sess-x",
        "game_version": "1.0.0",
        "started_at": "2026-08-13T00:00:00+00:00",
        "source": "import",
    },
    "events": [{"t": 0.0, "name": "session.start", "payload": {}}],
}


def test_validate_spool_error_paths() -> None:
    with pytest.raises(AuthoringError, match="schema_version"):
        validate_spool({"schema_version": 2, "session": {}, "events": []})
    with pytest.raises(AuthoringError, match="session must be"):
        validate_spool({"schema_version": 1, "session": [], "events": []})
    with pytest.raises(AuthoringError, match="events must be"):
        validate_spool({"schema_version": 1, "session": {"id": "a"}, "events": {}})
    with pytest.raises(AuthoringError, match="session.id"):
        validate_spool(
            {
                "schema_version": 1,
                "session": {"game_version": "1", "started_at": "t", "source": "import"},
                "events": [],
            }
        )
    with pytest.raises(AuthoringError, match="source"):
        data = json.loads(json.dumps(_MIN))
        data["session"]["source"] = "ftp"
        validate_spool(data)
    with pytest.raises(AuthoringError, match="started_at"):
        data = json.loads(json.dumps(_MIN))
        del data["session"]["started_at"]
        validate_spool(data)
    with pytest.raises(AuthoringError, match="duplicate seq"):
        data = json.loads(json.dumps(_MIN))
        data["events"] = [
            {"seq": 1, "t": 0.0, "name": "session.start", "payload": {}},
            {"seq": 1, "t": 1.0, "name": "combat.leak", "payload": {}},
        ]
        validate_spool(data)
    with pytest.raises(AuthoringError, match="dropped_count"):
        data = json.loads(json.dumps(_MIN))
        data["session"]["dropped_count"] = -1
        validate_spool(data)


def test_validate_event_payload_errors() -> None:
    def _ev(name: str, payload: object, **extra: object) -> dict:
        data = json.loads(json.dumps(_MIN))
        event: dict = {"t": 1.0, "name": name, "payload": payload}
        event.update(extra)
        data["events"] = [event]
        return data

    with pytest.raises(AuthoringError, match="events\\[0\\] must be an object"):
        data = json.loads(json.dumps(_MIN))
        data["events"] = ["nope"]
        validate_spool(data)
    with pytest.raises(AuthoringError, match="name must be"):
        validate_spool(_ev("", {}))
    with pytest.raises(AuthoringError, match=".t must be"):
        data = json.loads(json.dumps(_MIN))
        data["events"] = [{"t": True, "name": "session.start", "payload": {}}]
        validate_spool(data)
    with pytest.raises(AuthoringError, match="payload must be"):
        data = json.loads(json.dumps(_MIN))
        data["events"] = [{"t": 0, "name": "session.start", "payload": []}]
        validate_spool(data)
    with pytest.raises(AuthoringError, match="seq must be"):
        validate_spool(_ev("session.start", {}, seq=0))
    with pytest.raises(AuthoringError, match="outcome is required"):
        validate_spool(_ev("session.end", {}))
    with pytest.raises(AuthoringError, match="label is required"):
        validate_spool(_ev("session.checkpoint", {}))
    with pytest.raises(AuthoringError, match="amount must be"):
        validate_spool(_ev("currency.earned", {"currency_id": "soft", "amount": 0}))
    with pytest.raises(AuthoringError, match="unit_id is required"):
        validate_spool(_ev("unit.deployed", {}))
    with pytest.raises(AuthoringError, match="wave_index"):
        validate_spool(_ev("wave.started", {"wave_index": True}))
    with pytest.raises(AuthoringError, match="skill_id is required"):
        validate_spool(_ev("skill.cast", {}))


def test_load_spool_errors(tmp_path: Path) -> None:
    missing = tmp_path / "nope.json"
    with pytest.raises(AuthoringError, match="cannot read"):
        load_spool(missing)
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(AuthoringError, match="not valid JSON"):
        load_spool(bad)
    arr = tmp_path / "arr.json"
    arr.write_text("[1]", encoding="utf-8")
    with pytest.raises(AuthoringError, match="JSON object"):
        load_spool(arr)


def test_optional_fields_and_auto_seq(tmp_path: Path) -> None:
    data = json.loads(json.dumps(_MIN))
    data["session"]["session_id"] = data["session"].pop("id")
    data["session"]["seed"] = 7
    data["session"]["dropped_count"] = None
    data["events"] = [{"t": 0.0, "name": "session.start"}]
    with RunStore(tmp_path / "s.db") as store:
        result = ingest_spool_dict(store, data)
        assert result["id"] == "sess-x"
        row = store.get_telemetry_session("sess-x")
        assert row is not None
        assert row["seed"] == "7"
        ev = store.list_telemetry_events("sess-x")
        assert ev[0]["seq"] == 1


def test_outcome_copied_from_session_end(tmp_path: Path) -> None:
    data = json.loads(json.dumps(_MIN))
    data["session"].pop("outcome", None)
    data["events"] = [
        {"seq": 1, "t": 0.0, "name": "session.start", "payload": {}},
        {"seq": 2, "t": 9.0, "name": "session.end", "payload": {"outcome": "win"}},
    ]
    with RunStore(tmp_path / "s.db") as store:
        result = ingest_spool_dict(store, data)
        assert result["summary"]["outcome"] == "win"
        assert store.get_telemetry_session("sess-x")["outcome"] == "win"


def test_replace_false_raises(tmp_path: Path) -> None:
    with RunStore(tmp_path / "s.db") as store:
        ingest_spool_dict(store, json.loads(json.dumps(_MIN)))
        with pytest.raises(ValueError, match="already exists"):
            ingest_spool_dict(store, json.loads(json.dumps(_MIN)), replace=False)


def test_list_filters_and_ambiguous_prefix(tmp_path: Path) -> None:
    a = json.loads(json.dumps(_MIN))
    b = json.loads(json.dumps(_MIN))
    b["session"]["id"] = "sess-y"
    b["session"]["game_version"] = "2.0.0"
    b["session"]["policy_id"] = "rush"
    b["session"]["config_snapshot_id"] = "snap"
    b["session"]["feature_id"] = "f1"
    b["session"]["seed"] = "9"
    with RunStore(tmp_path / "s.db") as store:
        ingest_spool_dict(store, a)
        ingest_spool_dict(store, b)
        assert len(store.list_telemetry_sessions(game_version="2.0.0")) == 1
        assert len(store.list_telemetry_sessions(policy_id="rush")) == 1
        assert len(store.list_telemetry_sessions(config_snapshot_id="snap")) == 1
        assert len(store.list_telemetry_sessions(feature_id="f1")) == 1
        assert len(store.list_telemetry_sessions(seed="9")) == 1
        assert store.get_telemetry_session("sess-") is None


def test_parse_drain_payload_coercion() -> None:
    assert parse_drain_payload(None)["events"] == []
    assert parse_drain_payload("")["session"] is None
    assert parse_drain_payload("not-json")["dropped_count"] == 0
    assert parse_drain_payload("[1]")["events"] == []
    assert parse_drain_payload(1)["events"] == []
    raw = '{"events": "x", "dropped_count": -3, "session": "nope"}'
    got = parse_drain_payload(raw)
    assert got["events"] == []
    assert got["dropped_count"] == 0
    assert got["session"] is None


def test_drain_skips_ingest_without_store() -> None:
    class Fake:
        def call_game_method(self, hook: object, *args: object) -> object:
            return {
                "session": {
                    "id": "z",
                    "game_version": "1.0.0",
                    "started_at": "2026-08-13T00:00:00+00:00",
                    "source": "wire",
                },
                "events": [],
                "dropped_count": 0,
            }

    out = drain_telemetry(Fake())
    assert "ingested" not in out
    assert out["session"]["id"] == "z"


def test_drain_empty_session() -> None:
    class Empty:
        def call_game_method(self, hook: object, *args: object) -> object:
            return {"events": [], "dropped_count": 0}

    assert drain_telemetry(Empty(), store=None)["session"] is None


def test_drain_no_game_version_does_not_ingest(tmp_path: Path) -> None:
    class Fake:
        def call_game_method(self, hook: object, *args: object) -> object:
            return {
                "session": {
                    "id": "z",
                    "started_at": "2026-08-13T00:00:00+00:00",
                    "source": "wire",
                },
                "events": [],
                "dropped_count": 2,
            }

    with RunStore(tmp_path / "s.db") as store:
        out = drain_telemetry(Fake(), store)
        assert "ingested" not in out
        assert store.get_telemetry_session("z") is None


def test_render_empty_and_long_ids() -> None:
    assert render_session_list([]) == "no telemetry sessions\n"
    text = render_session_list(
        [{"id": "this-id-is-way-too-long-for-the-column", "game_version": "1"}]
    )
    assert "+" in text
    cmp_text = render_compare("a", "b", {"outcome": {"a": "lose", "b": "win"}, "empty": {}})
    assert "lose -> win" in cmp_text


def test_cli_error_paths(tmp_path: Path) -> None:
    missing = runner.invoke(app, ["telemetry", "query", "--store", str(tmp_path / "no.db")])
    assert missing.exit_code == 1
    db = tmp_path / "store.db"
    with RunStore(db):
        pass
    unknown = runner.invoke(app, ["telemetry", "query", "nope", "--store", str(db)])
    assert unknown.exit_code == 1
    fmt = runner.invoke(
        app, ["telemetry", "query", "--format", "xml", "--store", str(db)]
    )
    assert fmt.exit_code == 2
    cmp_missing = runner.invoke(
        app, ["telemetry", "query", "--compare", "b", "--store", str(db)]
    )
    assert cmp_missing.exit_code == 2
    bad = tmp_path / "bad.json"
    bad.write_text("{}", encoding="utf-8")
    imp = runner.invoke(app, ["telemetry", "import", str(bad), "--store", str(db)])
    assert imp.exit_code == 2
    empty_list = runner.invoke(app, ["telemetry", "query", "--store", str(db)])
    assert empty_list.exit_code == 0
    assert "no telemetry sessions" in empty_list.output
    listed_json = runner.invoke(
        app, ["telemetry", "query", "--format", "json", "--store", str(db)]
    )
    assert listed_json.exit_code == 0
    assert json.loads(listed_json.output) == []
    good = tmp_path / "good.json"
    good.write_text(json.dumps(_MIN), encoding="utf-8")
    ok = runner.invoke(app, ["telemetry", "import", str(good), "--store", str(db)])
    assert ok.exit_code == 0, ok.output
    cmp_unknown_b = runner.invoke(
        app, ["telemetry", "query", "sess-x", "--compare", "nope", "--store", str(db)]
    )
    assert cmp_unknown_b.exit_code == 1
