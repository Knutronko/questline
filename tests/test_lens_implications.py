"""GameLens implications via LLMPort — measured vs model reasoning."""

from __future__ import annotations

from pathlib import Path

from questline.ai.port import LlmRequest
from questline.ai.providers.fake import FakeProvider
from questline.ai.router import ProviderRouter
from questline.core.errors import ProviderError
from questline.core.store import RunStore
from questline.lens.diff import DiffReport, diff_snapshots
from questline.lens.report import build_implications, collect_measured, implications_stub
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
    finally:
        store.close()
