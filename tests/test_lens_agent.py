"""FP-G4 GameLens balance agent — fake LLM tool loop."""

from __future__ import annotations

import json
from pathlib import Path

from questline.ai.port import ToolCall
from questline.ai.providers.fake import FakeProvider
from questline.ai.router import ProviderRouter
from questline.core.store import RunStore
from questline.lens.agent import run_balance_agent
from questline.lens.diff import diff_snapshots
from questline.lens.report import collect_measured
from questline.lens.snapshot import BalanceSnapshot, SnapshotMeta


def _snap(version: str, tick: float, extra: bool = False) -> BalanceSnapshot:
    entities: dict = {
        "economy": {
            "id": "economy",
            "system": "economy",
            "kind": "config",
            "fields": {"amber_per_tick": {"type": "number", "value": tick}},
        }
    }
    if extra:
        entities["unit_beta"] = {
            "id": "unit_beta",
            "system": "creatures",
            "kind": "config",
            "fields": {"dps": {"type": "number", "value": 8.0}},
        }
    return BalanceSnapshot(
        schema_version=1,
        meta=SnapshotMeta(game_version=version),
        entities=entities,
    )


def _store_with_pair(tmp_path: Path) -> RunStore:
    store = RunStore(tmp_path / "s.db")
    a = _snap("1.0.0", 1.5)
    b = _snap("1.1.0", 2.0, extra=True)
    store.save_balance_snapshot(
        snapshot_id="1.0.0", game_version="1.0.0", payload=json.dumps(a.to_dict())
    )
    store.save_balance_snapshot(
        snapshot_id="1.1.0", game_version="1.1.0", payload=json.dumps(b.to_dict())
    )
    store.save_telemetry_session(
        session={
            "id": "sess-unset",
            "game_version": "1.1.0",
            "source": "import",
            "config_snapshot_id": "snap-unset",
            "policy_id": "balanced",
            "seed": "1",
            "outcome": "lose",
            "started_at": "2026-09-09T00:00:00+00:00",
        },
        summary={"outcome": "lose", "leak_count": 2, "deploy_count": 4},
        events=[],
    )
    store.save_telemetry_session(
        session={
            "id": "sess-ok",
            "game_version": "1.1.0",
            "source": "import",
            "config_snapshot_id": "1.1.0",
            "policy_id": "rush",
            "seed": "2",
            "outcome": "lose",
            "started_at": "2026-09-09T01:00:00+00:00",
        },
        summary={"outcome": "lose", "leak_count": 1, "deploy_count": 6},
        events=[],
    )
    return store


def test_agent_fake_loop_keeps_gaps_and_measured(tmp_path: Path) -> None:
    store = _store_with_pair(tmp_path)
    try:
        fake = FakeProvider()
        fake.enqueue_tools(ToolCall(id="1", name="collect_measured", arguments="{}"))
        fake.enqueue(
            json.dumps(
                {
                    "priorities": [
                        "Look at measured leak_count=1 on joined sessions.",
                        "Do not impute combat.damage.",
                    ],
                    "gaps": ["combat.damage"],
                }
            )
        )
        router = ProviderRouter(
            [fake],
            budget_per_call_usd=10.0,
            budget_per_run_usd=10.0,
            store=store,
            run_id="ba-test",
        )
        turn = run_balance_agent(
            store,
            snapshot_a="1.0.0",
            snapshot_b="1.1.0",
            question="What should I retune?",
            router=router,
            turn_id="ba-test",
        )
        assert turn.status == "ok"
        assert turn.framing == "model reasoning"
        assert turn.priorities
        gap_text = " ".join(turn.gaps)
        assert "snap-unset" in gap_text
        assert "combat.damage" in gap_text
        measured = turn.citations["measured"]
        assert measured["session_count"] >= 1
        assert measured["unjoined_count"] >= 1
        # Store owns numbers — leak_count lives in measured summaries, not invented.
        joined = measured["sessions"]
        assert any(s.get("summary", {}).get("leak_count") == 1 for s in joined)
        row = store.get_lens_agent_turn("ba-test")
        assert row is not None
        assert Path(row["artifact_path"]).is_file()
        assert fake.requests[0].tools
        assert any(c["name"] == "collect_measured" for c in turn.tool_log)
    finally:
        store.close()


def test_agent_unknown_tool_is_rejected(tmp_path: Path) -> None:
    store = _store_with_pair(tmp_path)
    try:
        fake = FakeProvider()
        fake.enqueue_tools(ToolCall(id="1", name="write_so", arguments="{}"))
        fake.enqueue('{"priorities": ["Human reviews measured leaks."], "gaps": []}')
        router = ProviderRouter(
            [fake],
            budget_per_call_usd=10.0,
            budget_per_run_usd=10.0,
            store=store,
            run_id="ba-deny",
        )
        turn = run_balance_agent(
            store,
            snapshot_a="1.0.0",
            snapshot_b="1.1.0",
            router=router,
            turn_id="ba-deny",
        )
        assert turn.status == "ok"
        assert turn.tool_log[0]["ok"] is False
        assert "write_so" in json.dumps(turn.tool_log)
        assert any("combat.damage" in g for g in turn.gaps)
    finally:
        store.close()


def test_agent_kill_at_turn_n_persists_tool_log(tmp_path: Path) -> None:
    store = _store_with_pair(tmp_path)
    try:
        fake = FakeProvider()
        fake.enqueue_tools(ToolCall(id="1", name="list_snapshots", arguments="{}"))
        router = ProviderRouter(
            [fake],
            budget_per_call_usd=10.0,
            budget_per_run_usd=10.0,
            store=store,
            run_id="ba-kill",
        )
        turn = run_balance_agent(
            store,
            snapshot_a="1.0.0",
            snapshot_b="1.1.0",
            router=router,
            turn_id="ba-kill",
            max_turns=1,
        )
        assert turn.status == "truncated"
        assert turn.tool_log
        assert store.get_lens_agent_turn("ba-kill") is not None
        assert Path(turn.artifact_path or "").is_file()
    finally:
        store.close()


def test_agent_skipped_without_provider_still_lists_gaps(tmp_path: Path) -> None:
    store = _store_with_pair(tmp_path)
    try:
        turn = run_balance_agent(
            store, snapshot_a="1.0.0", snapshot_b="1.1.0", router=None
        )
        assert turn.status == "skipped"
        assert turn.pending == "no-provider"
        assert any("combat.damage" in g for g in turn.gaps)
        report = diff_snapshots(_snap("1.0.0", 1.5), _snap("1.1.0", 2.0, extra=True))
        # Same gap policy as G1 collect_measured.
        _, gaps = collect_measured(store, report)
        assert any("combat.damage" in g for g in gaps)
    finally:
        store.close()


def test_agent_tools_and_bullet_reply(tmp_path: Path) -> None:
    store = _store_with_pair(tmp_path)
    try:
        fake = FakeProvider()
        fake.enqueue_tools(
            ToolCall(id="1", name="list_snapshots", arguments="{}"),
            ToolCall(id="2", name="diff_snapshots", arguments="{}"),
            ToolCall(
                id="3",
                name="get_implications",
                arguments='{"snapshot_a":"1.0.0","snapshot_b":"1.1.0"}',
            ),
            ToolCall(
                id="4",
                name="list_session_summaries",
                arguments='{"config_snapshot_id":"snap-unset","limit":5}',
            ),
        )
        fake.enqueue(
            "- Look at measured leak_count on joined sessions.\n"
            "- combat.damage is a gap; do not impute.\n"
        )
        router = ProviderRouter(
            [fake],
            budget_per_call_usd=10.0,
            budget_per_run_usd=10.0,
            store=store,
            run_id="ba-tools",
        )
        turn = run_balance_agent(
            store,
            snapshot_a="1.0.0",
            snapshot_b="1.1.0",
            router=router,
            turn_id="ba-tools",
        )
        names = [c["name"] for c in turn.tool_log]
        assert names == [
            "list_snapshots",
            "diff_snapshots",
            "get_implications",
            "list_session_summaries",
        ]
        assert all(c["ok"] for c in turn.tool_log)
        assert turn.status == "ok"
        assert any("leak_count" in p for p in turn.priorities)
        assert any("combat.damage" in g for g in turn.gaps)
    finally:
        store.close()


def test_agent_llm_error_keeps_store_gaps(tmp_path: Path) -> None:
    store = _store_with_pair(tmp_path)
    try:
        fake = FakeProvider()
        fake.enqueue(RuntimeError("boom"))
        router = ProviderRouter(
            [fake],
            budget_per_call_usd=10.0,
            budget_per_run_usd=10.0,
            store=store,
            run_id="ba-err",
        )
        turn = run_balance_agent(
            store,
            snapshot_a="1.0.0",
            snapshot_b="1.1.0",
            router=router,
            turn_id="ba-err",
        )
        assert turn.status == "error"
        assert "boom" in turn.summary
        assert any("combat.damage" in g for g in turn.gaps)
    finally:
        store.close()


def test_agent_unknown_snapshot_pair(tmp_path: Path) -> None:
    store = RunStore(tmp_path / "empty.db")
    try:
        turn = run_balance_agent(
            store, snapshot_a="missing-a", snapshot_b="missing-b", router=None
        )
        assert turn.status == "skipped"
        assert any("unknown snapshot" in g for g in turn.gaps)
    finally:
        store.close()
