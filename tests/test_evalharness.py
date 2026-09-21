"""Phase-13 eval harness: goldens, metrics, sabotage flag, compare, exporters."""

from __future__ import annotations

from pathlib import Path

from questline.core.store import RunStore
from questline.evalharness.compare import compare_eval_runs
from questline.evalharness.exporters import to_deepeval, to_langfuse
from questline.evalharness.loader import load_goldens
from questline.evalharness.runner import run_eval


def test_goldens_cover_four_classes() -> None:
    cases = load_goldens()
    assert len(cases) >= 10
    classes = {c.failure_class for c in cases}
    assert {"locator", "assertion", "infra", "timing"} <= classes
    assert any(c.sabotage_gate for c in cases)
    assert any(c.failure_class == "green" for c in cases)


def test_eval_offline_flags_sabotaged_gate(tmp_path: Path) -> None:
    store = RunStore(tmp_path / "store.db", artifacts_dir=tmp_path / "arts")
    run = run_eval(store, agent="maintainer", provider="fake", prompt_version="v1")
    assert run.case_count >= 10
    assert run.diagnosis_accuracy == 1.0
    sabotaged = [c for c in run.cases if c.get("sabotage")]
    assert sabotaged
    assert all(c.get("false_green") for c in sabotaged)
    assert (run.false_green_rate or 0) > 0
    row = store.get_eval_result(run.id)
    assert row is not None
    listed = store.list_eval_results()
    assert any(r["id"] == run.id for r in listed)
    store.close()


def test_compare_and_exporters(tmp_path: Path) -> None:
    store = RunStore(tmp_path / "store.db", artifacts_dir=tmp_path / "arts")
    a = run_eval(store, provider="fake", eval_id="eval-left")
    b = run_eval(store, provider="fake-b", eval_id="eval-right")
    report = compare_eval_runs(a.to_dict(), b.to_dict())
    assert "delta_b_minus_a" in report
    assert "diagnosis_accuracy" in report["delta_b_minus_a"]
    dee = to_deepeval(a.to_dict())
    assert dee["format"] == "deepeval-stub"
    assert dee["test_cases"]
    lang = to_langfuse(a.to_dict())
    assert lang["format"] == "langfuse-stub"
    assert lang["traces"]
    store.close()
