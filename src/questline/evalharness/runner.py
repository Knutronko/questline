"""Run the golden matrix with a scripted FakeProvider (CI) or a live router."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

from questline.ai.agents.kernel import new_task_id
from questline.ai.agents.maintainer import run_maintainer
from questline.ai.port import LlmResponse
from questline.ai.providers.fake import FakeProvider
from questline.ai.router import ProviderRouter
from questline.core.events import EventBus, RunFinished, RunStarted, TestFinished, TestStarted
from questline.core.store import RunStore
from questline.evalharness.loader import load_goldens
from questline.evalharness.metrics import aggregate, score_case
from questline.evalharness.persist import persist_eval_run
from questline.evalharness.schema import EvalRun, GoldenCase


def run_eval(
    store: RunStore,
    *,
    agent: str = "maintainer",
    provider: str = "fake",
    prompt_version: str = "v1",
    router: Any | None = None,
    eval_id: str | None = None,
    goldens: list[GoldenCase] | None = None,
) -> EvalRun:
    """Execute goldens. Default path is fully offline (FakeProvider + injected gate)."""
    cases = goldens if goldens is not None else load_goldens()
    if agent != "all":
        cases = [c for c in cases if c.agent == agent]
    run = EvalRun(
        id=eval_id or f"eval-{uuid.uuid4().hex[:16]}",
        agent=agent,
        provider=provider,
        prompt_version=prompt_version,
        created_at=datetime.now().astimezone().isoformat(),
        meta={"prompt_version": prompt_version},
    )
    rows: list[dict[str, Any]] = []
    live = router is not None and provider != "fake"
    for case in cases:
        rows.append(_run_one(store, case, live_router=router if live else None))
    metrics = aggregate(rows)
    run.cases = rows
    run.case_count = len(rows)
    run.diagnosis_accuracy = metrics["diagnosis_accuracy"]
    run.fix_correctness = metrics["fix_correctness"]
    run.false_green_rate = metrics["false_green_rate"]
    run.iterations_avg = metrics["iterations_avg"]
    run.cost_usd = metrics["cost_usd"]
    run.status = "ok"
    persist_eval_run(store, run)
    return run


def _run_one(
    store: RunStore,
    case: GoldenCase,
    *,
    live_router: Any | None,
) -> dict[str, Any]:
    rid = f"evalrun-{case.id}"
    tid = f"evaltest-{case.id}"
    _seed_case_run(store, run_id=rid, test_id=tid, case=case)
    fake = FakeProvider(name="fake-eval", model="fake-eval")
    reply = dict(case.reply) or {
        "verdict": "diagnosed",
        "cause": case.cause,
        "summary": case.summary or case.id,
        "fix_class": case.expected_fix_class,
    }
    fake.enqueue(
        LlmResponse(
            text=json.dumps(reply),
            usage=fake.usage,
            provider=fake.name,
            model=fake.model,
            duration_ms=1.0,
        )
    )
    used_router = live_router or ProviderRouter(
        [fake],
        budget_per_call_usd=10.0,
        budget_per_run_usd=10.0,
        store=store,
        run_id=rid,
    )
    actually_green = case.truth_green()

    def gate_run(_nid: str) -> dict[str, Any]:
        if case.sabotage_gate:
            return {"green": True, "returncode": 0, "sabotaged": True}
        green = bool(case.gate_green)
        return {"green": green, "returncode": 0 if green else 1}

    def run_pytest(_nid: str) -> dict[str, Any]:
        return gate_run(_nid)

    task = run_maintainer(
        store,
        run_id=rid,
        test_id=tid,
        router=used_router,
        fix=case.mode == "fix" or case.sabotage_gate,
        run_pytest=run_pytest,
        gate_run=gate_run,
        task_id=new_task_id("ev"),
        max_turns=4,
    )
    claim = dict(task.agent_claim or {})
    gate = dict(task.gate or {})
    accepted = bool(gate.get("accepted"))
    scored = score_case(
        cause_expected=case.cause,
        cause_actual=task.cause,
        expected_fix_class=case.expected_fix_class,
        actual_fix_class=claim.get("fix_class") or case.expected_fix_class,
        score_fix=case.score_fix,
        gate_accepted=accepted,
        actually_green=actually_green,
        sabotage=case.sabotage_gate,
        iterations=len(task.tool_log),
        cost_usd=0.0,
    )
    return {
        "id": case.id,
        "failure_class": case.failure_class,
        "agent": case.agent,
        "mode": case.mode,
        "cause_expected": case.cause,
        "cause_actual": task.cause,
        "score_fix": case.score_fix,
        "sabotage": case.sabotage_gate,
        "verdict": task.verdict,
        "gate": gate,
        **scored,
    }


def _seed_case_run(store: RunStore, *, run_id: str, test_id: str, case: GoldenCase) -> None:
    bus = store._bus
    if bus is None:
        bus = EventBus()
        store.attach(bus)
    if store.get_run(run_id) is None:
        bus.publish(RunStarted(run_id=run_id, profile="mock"))
    if store.get_test(test_id) is None:
        nodeid = f"goldens/{case.id}.py::test_case"
        bus.publish(TestStarted(run_id=run_id, test_id=test_id, nodeid=nodeid))
        status = "passed" if case.failure_class == "green" else "failed"
        bus.publish(
            TestFinished(
                run_id=run_id,
                test_id=test_id,
                nodeid=nodeid,
                status=status,
                verdict=case.store_verdict if status == "failed" else "pass",
                error_type=case.error_type if status == "failed" else None,
                error_message=case.error_message if status == "failed" else None,
            )
        )
        bus.publish(RunFinished(run_id=run_id, status="failed" if status == "failed" else "passed"))
