"""Seedable demo store for HUD CI / Playwright smoke."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from questline.core.events import (
    AiCallMade,
    EventBus,
    PerfSample,
    RunFinished,
    RunStarted,
    StepFinished,
    StepStarted,
    TestFinished,
    TestStarted,
)
from questline.core.store import RunStore


def seed_fixture_store(db_path: Path) -> RunStore:
    """Populate a store with two runs suitable for API + Playwright smoke."""
    store = RunStore(db_path)
    bus = EventBus()
    store.attach(bus)
    t0 = datetime(2026, 8, 10, 10, 0, 0, tzinfo=UTC)

    bus.publish(
        RunStarted(
            run_id="run-a",
            profile="android_local",
            timestamp=t0,
            tags={"driver": "questline", "device": "adb"},
        )
    )
    bus.publish(
        TestStarted(
            run_id="run-a",
            test_id="t-pass",
            nodeid="tests/demo.py::test_boot",
            timestamp=t0 + timedelta(seconds=1),
        )
    )
    bus.publish(
        StepStarted(
            run_id="run-a",
            test_id="t-pass",
            step_id="s1",
            name="wait_hello",
            timestamp=t0 + timedelta(seconds=2),
        )
    )
    bus.publish(
        StepFinished(
            run_id="run-a",
            test_id="t-pass",
            step_id="s1",
            name="wait_hello",
            status="passed",
            timestamp=t0 + timedelta(seconds=3),
        )
    )
    bus.publish(
        TestFinished(
            run_id="run-a",
            test_id="t-pass",
            nodeid="tests/demo.py::test_boot",
            status="passed",
            timestamp=t0 + timedelta(seconds=4),
        )
    )
    bus.publish(
        TestStarted(
            run_id="run-a",
            test_id="t-infra",
            nodeid="tests/demo.py::test_shop",
            timestamp=t0 + timedelta(seconds=5),
        )
    )
    bus.publish(
        StepStarted(
            run_id="run-a",
            test_id="t-infra",
            step_id="s2",
            name="open_shop",
            timestamp=t0 + timedelta(seconds=6),
        )
    )
    bus.publish(
        TestFinished(
            run_id="run-a",
            test_id="t-infra",
            nodeid="tests/demo.py::test_shop",
            status="failed",
            verdict="infra",
            error_type="SessionLostError",
            error_message="socket closed",
            timestamp=t0 + timedelta(seconds=7),
            tags={"health": "lost"},
        )
    )
    shot = store.save_artifact(
        b"fakepng",
        run_id="run-a",
        test_id="t-infra",
        name="fail.png",
        kind="screenshot",
        bus=bus,
    )
    assert shot.exists()
    bus.publish(
        RunFinished(run_id="run-a", status="failed", timestamp=t0 + timedelta(seconds=8))
    )

    bus.publish(
        AiCallMade(
            run_id="run-a",
            provider="mistral",
            model="mistral-small-latest",
            tokens_in=120,
            tokens_out=40,
            cost=0.000024,
            purpose="lens.implications",
            duration_ms=210.0,
            cached=False,
            outcome="ok",
            pricing_version="1",
            timestamp=t0 + timedelta(seconds=9),
        )
    )
    bus.publish(
        AiCallMade(
            run_id="run-a",
            provider="groq",
            model="llama-3.3-70b-versatile",
            tokens_in=0,
            tokens_out=0,
            cost=0.0,
            purpose="lens.implications",
            duration_ms=80.0,
            outcome="rate_limited",
            pricing_version="1",
            timestamp=t0 + timedelta(seconds=9, milliseconds=100),
        )
    )

    # Perf samples for HUD graphs / compare (phase-10).
    for i, fps in enumerate((58.0, 60.0, 55.0, 57.0)):
        bus.publish(
            PerfSample(
                run_id="run-a",
                test_id="t-pass",
                metric="fps",
                value=fps,
                timestamp=t0 + timedelta(seconds=2 + i),
            )
        )
    for i, mem in enumerate((210.0, 215.0, 220.0)):
        bus.publish(
            PerfSample(
                run_id="run-a",
                test_id="t-pass",
                metric="memory_pss_mb",
                value=mem,
                timestamp=t0 + timedelta(seconds=2 + i),
            )
        )

    t1 = t0 + timedelta(hours=1)
    bus.publish(
        RunStarted(
            run_id="run-b",
            profile="editor",
            timestamp=t1,
            tags={"driver": "mock"},
        )
    )
    bus.publish(
        TestStarted(
            run_id="run-b",
            test_id="t-shop-b",
            nodeid="tests/demo.py::test_shop",
            timestamp=t1 + timedelta(seconds=1),
        )
    )
    bus.publish(
        StepStarted(
            run_id="run-b",
            test_id="t-shop-b",
            step_id="s3",
            name="open_shop",
            timestamp=t1 + timedelta(seconds=2),
        )
    )
    bus.publish(
        StepFinished(
            run_id="run-b",
            test_id="t-shop-b",
            step_id="s3",
            name="open_shop",
            status="passed",
            timestamp=t1 + timedelta(seconds=3),
        )
    )
    bus.publish(
        TestFinished(
            run_id="run-b",
            test_id="t-shop-b",
            nodeid="tests/demo.py::test_shop",
            status="passed",
            timestamp=t1 + timedelta(seconds=4),
        )
    )
    bus.publish(
        RunFinished(run_id="run-b", status="passed", timestamp=t1 + timedelta(seconds=5))
    )

    for i, fps in enumerate((50.0, 52.0, 49.0, 51.0)):
        bus.publish(
            PerfSample(
                run_id="run-b",
                test_id="t-shop-b",
                metric="fps",
                value=fps,
                timestamp=t1 + timedelta(seconds=1 + i),
            )
        )
    for i, mem in enumerate((230.0, 240.0, 235.0)):
        bus.publish(
            PerfSample(
                run_id="run-b",
                test_id="t-shop-b",
                metric="memory_pss_mb",
                value=mem,
                timestamp=t1 + timedelta(seconds=1 + i),
            )
        )

    _seed_gamelens(store)
    store.detach()
    return store


def _entity(eid: str, system: str, fields: dict[str, object]) -> dict[str, object]:
    return {"id": eid, "system": system, "kind": "config", "fields": fields}


def _seed_gamelens(store: RunStore) -> None:
    """Snapshots + sessions + implications + one agent turn for HUD GameLens smoke."""
    snap_a = {
        "schema_version": 1,
        "meta": {"game_version": "1.0.0", "feature_id": None, "git_commit": None},
        "entities": {
            "economy": _entity(
                "economy",
                "economy",
                {"amber_per_tick": {"type": "number", "value": 1.5}},
            ),
            "unit_alpha": _entity(
                "unit_alpha",
                "creatures",
                {"dps": {"type": "number", "value": 10.0}},
            ),
        },
        "supplementary": [],
    }
    snap_b = {
        "schema_version": 1,
        "meta": {"game_version": "1.1.0", "feature_id": None, "git_commit": None},
        "entities": {
            "economy": _entity(
                "economy",
                "economy",
                {"amber_per_tick": {"type": "number", "value": 2.0}},
            ),
            "unit_alpha": _entity(
                "unit_alpha",
                "creatures",
                {"dps": {"type": "number", "value": 12.0}},
            ),
            "unit_beta": _entity(
                "unit_beta",
                "creatures",
                {"dps": {"type": "number", "value": 8.0}},
            ),
        },
        "supplementary": [],
    }
    store.save_balance_snapshot(
        snapshot_id="1.0.0",
        game_version="1.0.0",
        payload=json.dumps(snap_a, sort_keys=True),
    )
    store.save_balance_snapshot(
        snapshot_id="1.1.0",
        game_version="1.1.0",
        payload=json.dumps(snap_b, sort_keys=True),
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
            "started_at": "2026-09-09T10:00:00+00:00",
            "finished_at": "2026-09-09T10:05:00+00:00",
        },
        summary={
            "outcome": "lose",
            "deploy_count": 4,
            "leak_count": 3,
            "waves_started": 2,
        },
        events=[],
    )
    store.save_telemetry_session(
        session={
            "id": "sess-joined",
            "game_version": "1.1.0",
            "source": "import",
            "config_snapshot_id": "1.1.0",
            "policy_id": "rush",
            "seed": "2",
            "outcome": "lose",
            "started_at": "2026-09-09T11:00:00+00:00",
            "finished_at": "2026-09-09T11:04:00+00:00",
        },
        summary={
            "outcome": "lose",
            "deploy_count": 6,
            "leak_count": 1,
            "waves_started": 3,
        },
        events=[],
    )
    from questline.ai.port import ToolCall
    from questline.ai.providers.fake import FakeProvider
    from questline.ai.router import ProviderRouter
    from questline.lens.agent import run_balance_agent
    from questline.lens.browse import diff_from_store
    from questline.lens.report import collect_measured, implications_stub, persist_implications

    report = diff_from_store(store, "1.0.0", "1.1.0")
    measured, gaps = collect_measured(store, report)
    persist_implications(
        store, report, implications_stub(report, measured=measured, gaps=gaps)
    )
    fake = FakeProvider()
    fake.enqueue_tools(ToolCall(id="c1", name="collect_measured", arguments="{}"))
    fake.enqueue(
        json.dumps(
            {
                "priorities": [
                    "Look at measured leak_count on joined sessions; do not impute combat.damage.",
                    "snap-unset sessions stay unjoined until QUESTLINE_SNAPSHOT_ID is set.",
                ],
                "gaps": ["combat.damage", "snap-unset"],
            }
        )
    )
    router = ProviderRouter(
        [fake],
        budget_per_call_usd=10.0,
        budget_per_run_usd=10.0,
        store=store,
        run_id="ba-fixture",
    )
    run_balance_agent(
        store,
        snapshot_a="1.0.0",
        snapshot_b="1.1.0",
        question="What should I retune?",
        router=router,
        turn_id="ba-fixture",
    )


class ScriptedBalanceProvider:
    """Deterministic tool loop for HUD smoke / Playwright (no network)."""

    name = "fake"
    model = "fake-test"
    kind = "fake"

    def complete(self, req: Any) -> Any:
        from questline.ai.port import LlmResponse, TokenUsage, ToolCall

        usage = TokenUsage(tokens_in=10, tokens_out=20)
        saw_tools = any("TOOL RESULTS" in (m.content or "") for m in req.messages)
        if req.tools and not saw_tools:
            return LlmResponse(
                text="",
                tool_calls=(ToolCall(id="c1", name="collect_measured", arguments="{}"),),
                usage=usage,
                provider=self.name,
                model=self.model,
                duration_ms=1.0,
            )
        return LlmResponse(
            text=json.dumps(
                {
                    "priorities": [
                        "Look at measured leak_count; do not impute combat.damage.",
                        "snap-unset sessions stay unjoined.",
                    ],
                    "gaps": ["combat.damage", "snap-unset"],
                }
            ),
            usage=usage,
            provider=self.name,
            model=self.model,
            duration_ms=1.0,
        )
