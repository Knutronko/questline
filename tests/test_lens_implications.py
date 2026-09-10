"""GameLens implications via LLMPort — measured vs model reasoning."""

from __future__ import annotations

import json
from pathlib import Path

from questline.ai.port import LlmRequest
from questline.ai.providers.fake import FakeProvider
from questline.ai.router import ProviderRouter
from questline.core.errors import ProviderError
from questline.core.store import RunStore
from questline.lens.diff import DiffReport, diff_snapshots
from questline.lens.report import (
    build_implications,
    collect_measured,
    implications_stub,
    persist_implications,
)
from questline.lens.snapshot import normalize_pack

FIXTURES = Path(__file__).parent / "fixtures" / "lens"


def test_implications_live_labels_reasoning_and_gaps(tmp_path: Path) -> None:
    a = normalize_pack(FIXTURES / "pack-a", game_version="1.0.0")
    b = normalize_pack(FIXTURES / "pack-b", game_version="1.1.0")
    report = diff_snapshots(a, b, snapshot_id_a="snap-unset", snapshot_id_b="1.1.0")
    store = RunStore(tmp_path / "s.db")
    try:
        store.save_telemetry_session(
            session={
                "id": "sess-1",
                "game_version": "1.1.0",
                "source": "import",
                "config_snapshot_id": "1.1.0",
                "policy_id": "balanced",
                "seed": "1",
                "outcome": "lose",
                "started_at": "2026-09-09T00:00:00+00:00",
            },
            summary={
                "outcome": "lose",
                "deploy_count": 4,
                "leak_count": 2,
                "waves_started": 3,
            },
            events=[],
        )
        fake = FakeProvider()
        fake.enqueue(
            "Model reasoning: measured leak_count=2 on snapshot 1.1.0. "
            "combat.damage is missing. snap-unset cannot join."
        )
        router = ProviderRouter(
            [fake],
            budget_per_call_usd=10.0,
            budget_per_run_usd=10.0,
            store=store,
            run_id="lens",
        )
        impl = build_implications(report, store=store, router=router)
        assert impl.status == "ok"
        assert impl.framing == "model reasoning"
        assert impl.pending is None
        assert "combat.damage" in " ".join(impl.gaps)
        assert any("snap-unset" in g for g in impl.gaps)
        assert impl.measured["session_count"] >= 1
        req = fake.last_request
        assert isinstance(req, LlmRequest)
        assert "MEASURED" in req.messages[0].content
        assert "GAPS" in req.messages[0].content
        # Must not invent a green/red in the stub path either.
        stub = implications_stub(report, measured=impl.measured, gaps=impl.gaps)
        assert stub.status == "skipped"
        assert "pass/fail" not in stub.summary.lower()
    finally:
        store.close()


def test_collect_measured_without_store() -> None:
    report = DiffReport(
        version_a="a",
        version_b="b",
        snapshot_id_a="x",
        snapshot_id_b="y",
        entries=(),
    )
    measured, gaps = collect_measured(None, report)
    assert measured["session_count"] == 0
    assert any("no run store" in g for g in gaps)


def test_implications_llm_error(tmp_path: Path) -> None:
    fake = FakeProvider()
    fake.enqueue(ProviderError("boom"))
    store = RunStore(tmp_path / "s.db")
    try:
        report = DiffReport(
            version_a="a",
            version_b="b",
            snapshot_id_a=None,
            snapshot_id_b=None,
            entries=(),
        )
        router = ProviderRouter(
            [fake],
            budget_per_call_usd=10.0,
            budget_per_run_usd=10.0,
            store=store,
            run_id="lens",
        )
        impl = build_implications(report, store=store, router=router)
        assert impl.status == "error"
        assert impl.framing == "model reasoning"
        assert "ProviderError" in impl.summary or "boom" in impl.summary
    finally:
        store.close()


def test_collect_measured_missing_snapshot(tmp_path: Path) -> None:
    store = RunStore(tmp_path / "s.db")
    try:
        report = DiffReport(
            version_a="a",
            version_b="b",
            snapshot_id_a="no-such",
            snapshot_id_b="also-missing",
            entries=(),
        )
        measured, gaps = collect_measured(store, report)
        assert measured["session_count"] == 0
        assert any("no telemetry_sessions" in g for g in gaps)
        assert any("combat.damage" in g for g in gaps)
        assert measured["unjoined_count"] == 0
    finally:
        store.close()


def _save_session(
    store: RunStore,
    *,
    sid: str,
    game_version: str,
    snapshot: str | None,
    policy_id: str = "balanced",
    seed: str = "1",
    outcome: str = "lose",
    leak_count: int = 2,
) -> None:
    store.save_telemetry_session(
        session={
            "id": sid,
            "game_version": game_version,
            "source": "import",
            "config_snapshot_id": snapshot,
            "policy_id": policy_id,
            "seed": seed,
            "outcome": outcome,
            "started_at": "2026-09-09T00:00:00+00:00",
        },
        summary={"outcome": outcome, "leak_count": leak_count, "deploy_count": 4},
        events=[],
    )


def test_collect_measured_snap_unset_is_unjoined_not_silent(tmp_path: Path) -> None:
    store = RunStore(tmp_path / "s.db")
    try:
        report = DiffReport(
            version_a="1.0.0",
            version_b="1.1.0",
            snapshot_id_a="1.0.0",
            snapshot_id_b="1.1.0",
            entries=(),
        )
        _save_session(
            store,
            sid="g3-unset",
            game_version="1.1.0",
            snapshot="snap-unset",
            policy_id="rush",
            seed="44",
        )
        _save_session(
            store,
            sid="joined-b",
            game_version="1.1.0",
            snapshot="1.1.0",
            policy_id="balanced",
        )
        _save_session(
            store,
            sid="other-ver",
            game_version="9.9.9",
            snapshot="snap-unset",
            policy_id="cheapest",
        )
        measured, gaps = collect_measured(store, report)
        joined_ids = {s["id"] for s in measured["sessions"]}
        unjoined_ids = {s["id"] for s in measured["unjoined"]}
        assert joined_ids == {"joined-b"}
        assert unjoined_ids == {"g3-unset"}
        assert "g3-unset" not in joined_ids
        assert "other-ver" not in joined_ids
        assert "other-ver" not in unjoined_ids
        assert measured["session_count"] == 1
        assert measured["unjoined_count"] == 1
        gap_text = " ".join(gaps)
        assert "snap-unset" in gap_text
        assert "combat.damage" in gap_text
        assert "outside this diff" in gap_text
        policies = {row["policy_id"]: row for row in measured["unjoined_by_policy"]}
        assert policies["rush"]["session_count"] == 1
        assert policies["rush"]["outcomes"] == {"lose": 1}
        assert "44" in policies["rush"]["seeds"]
    finally:
        store.close()


def test_collect_measured_null_snapshot_is_unjoined(tmp_path: Path) -> None:
    store = RunStore(tmp_path / "s.db")
    try:
        report = DiffReport(
            version_a="1.0.0",
            version_b="1.0.0",
            snapshot_id_a="1.0.0",
            snapshot_id_b="1.0.0",
            entries=(),
        )
        _save_session(store, sid="null-snap", game_version="1.0.0", snapshot=None)
        measured, gaps = collect_measured(store, report)
        assert measured["session_count"] == 0
        assert measured["unjoined_count"] == 1
        assert measured["unjoined"][0]["id"] == "null-snap"
        assert any("snap-unset" in g for g in gaps)
    finally:
        store.close()


def test_persist_implications_writes_json_md_and_store(tmp_path: Path) -> None:
    store = RunStore(tmp_path / "s.db", artifacts_dir=tmp_path / "artifacts")
    try:
        a = normalize_pack(FIXTURES / "pack-a", game_version="1.0.0")
        b = normalize_pack(FIXTURES / "pack-b", game_version="1.1.0")
        report = diff_snapshots(a, b, snapshot_id_a="1.0.0", snapshot_id_b="1.1.0")
        _save_session(
            store,
            sid="g3-unset",
            game_version="1.1.0",
            snapshot="snap-unset",
        )
        fake = FakeProvider()
        fake.enqueue(
            "Priorities: look at leaks (measured leak_count=4). "
            "snap-unset cannot join. combat.damage is missing."
        )
        router = ProviderRouter(
            [fake],
            budget_per_call_usd=10.0,
            budget_per_run_usd=10.0,
            store=store,
            run_id="lens",
        )
        impl = persist_implications(
            store,
            report,
            build_implications(report, store=store, router=router),
        )
        assert impl.status == "ok"
        assert impl.artifact_path is not None
        json_path = Path(impl.artifact_path)
        md_path = json_path.with_suffix(".md")
        assert json_path.is_file()
        assert md_path.is_file()
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        assert payload["framing"] == "model reasoning"
        assert payload["measured"]["unjoined_count"] == 1
        assert payload["measured"]["session_count"] == 0
        assert "combat.damage" in " ".join(payload["gaps"])
        md = md_path.read_text(encoding="utf-8")
        assert "Model reasoning" in md
        assert "Gaps" in md
        row = store.get_lens_implications("1.0.0__1.1.0")
        assert row is not None
        assert row["status"] == "ok"
        assert row["prompt_version"] == "v1"
        assert row["artifact_path"] == str(json_path)
        listed = store.list_lens_implications(snapshot_id_a="1.0.0")
        assert len(listed) == 1
    finally:
        store.close()
