"""Locator self-healing — suggest locators.yaml only; never write."""

from __future__ import annotations

from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from questline.ai.agents.kernel import AgentKernel, new_task_id
from questline.ai.agents.persist import persist_task
from questline.ai.agents.prompts import HEALER_PROMPT, HEALER_VERSION
from questline.ai.agents.task import AgentTask
from questline.ai.agents.tools import HIERARCHY_SNAPSHOT, READ_FILE, STORE_QUERY, ToolContext
from questline.ai.prompts.store import compose_stable_prefix, load_prompt
from questline.core.store import RunStore
from questline.drivers.locators import Locator, LocatorRegistry, load_locators

PURPOSE_TAG = "agent.healer"


def flatten_hierarchy(snapshot: Any, *, parent: str = "") -> list[dict[str, str]]:
    nodes: list[dict[str, str]] = []
    if isinstance(snapshot, dict) and "roots" in snapshot:
        items = snapshot.get("roots") or []
    elif isinstance(snapshot, list):
        items = snapshot
    else:
        items = [snapshot] if snapshot else []
    for item in items:
        if not isinstance(item, dict):
            continue
        el = item.get("element") if isinstance(item.get("element"), dict) else item
        eid = str(el.get("id") or "")
        name = str(el.get("name") or "")
        path = str(el.get("path") or "")
        text = str(el.get("text") or "")
        nodes.append({"id": eid, "name": name, "path": path, "text": text, "parent": parent})
        kids = item.get("children") or []
        if kids:
            nodes.extend(flatten_hierarchy(kids, parent=eid or path))
    return nodes


def rank_candidates(
    expected: str,
    nodes: list[dict[str, str]],
    *,
    by: str = "id",
) -> list[dict[str, Any]]:
    needle = (expected or "").strip().lower()
    ranked: list[dict[str, Any]] = []
    for node in nodes:
        semantic = max(
            _ratio(needle, node["id"].lower()),
            _ratio(needle, node["name"].lower()),
            _ratio(needle, node["text"].lower()),
            _ratio(needle, node["path"].lower()),
        )
        structural = _ratio(needle, (node["parent"] + "/" + node["id"]).lower())
        score = 0.7 * semantic + 0.3 * structural
        ranked.append(
            {
                "id": node["id"],
                "name": node["name"],
                "path": node["path"],
                "text": node["text"],
                "score": round(score, 4),
                "by": by,
                "value": _value_for(by, node),
            }
        )
    ranked.sort(key=lambda r: r["score"], reverse=True)
    return ranked[:8]


def suggested_yaml_diff(
    *,
    page: str,
    name: str,
    old: Locator | None,
    new_by: str,
    new_value: str,
) -> str:
    old_by = old.by.value if old is not None else "?"
    old_val = old.value if old is not None else "?"
    return (
        f"--- locators.yaml\n+++ locators.yaml (suggested; not applied)\n"
        f"@@ {page}.{name} @@\n"
        f"-  by: {old_by}\n-  value: {old_val}\n"
        f"+  by: {new_by}\n+  value: {new_value}\n"
    )


def run_healer(
    store: RunStore,
    *,
    run_id: str,
    test_id: str | None = None,
    router: Any | None = None,
    project_root: Path | None = None,
    locators_path: Path | None = None,
    max_turns: int = 4,
    task_id: str | None = None,
) -> AgentTask:
    root = Path(project_root).resolve() if project_root else Path.cwd().resolve()
    yaml_path = Path(locators_path) if locators_path else (root / "locators.yaml")
    target_id = test_id
    if target_id is None:
        target_id = _first_element_not_found(store, run_id)
    if target_id is None:
        raise KeyError(f"no ElementNotFound test in run {run_id}")
    test = store.get_test(target_id)
    if test is None:
        raise KeyError(f"unknown test {target_id}")

    registry = _safe_locators(yaml_path)
    expected_value, page, loc_name, old_loc = _expected_from_test(test, registry)
    snapshot = _load_hierarchy(store, run_id, target_id)
    nodes = flatten_hierarchy(snapshot)
    ranked = rank_candidates(expected_value, nodes, by=(old_loc.by.value if old_loc else "id"))
    top = ranked[0] if ranked else None
    diff = ""
    if top is not None:
        diff = suggested_yaml_diff(
            page=page or "Unknown",
            name=loc_name or "element",
            old=old_loc,
            new_by=str(top.get("by") or "id"),
            new_value=str(top.get("value") or top.get("id") or ""),
        )
    suggestion = {
        "expected": expected_value,
        "candidates": ranked,
        "yaml_diff": diff,
        "confidence": top["score"] if top else 0.0,
        "writes": False,
    }

    task = AgentTask(
        id=task_id or new_task_id("heal"),
        kind="heal",
        run_id=run_id,
        test_id=target_id,
        status="running",
        prompt_version=HEALER_VERSION,
        purpose_tag=PURPOSE_TAG,
        created_at=datetime.now().astimezone().isoformat(),
        suggestion=suggestion,
        evidence=[{"kind": "locator", "expected": expected_value}],
        verdict="diagnosed" if top else "inconclusive",
        cause="test-bug" if top else "unknown",
        summary=diff or "No hierarchy candidates.",
    )
    persist_task(store, task)

    ctx = ToolContext(
        store=store,
        project_root=root,
        run_id=run_id,
        test_id=target_id,
        locators_path=yaml_path,
    )
    kernel = AgentKernel(
        store,
        router=router,
        ctx=ctx,
        max_turns=max_turns,
        read_only=True,
        purpose_tag=PURPOSE_TAG,
    )
    user = compose_stable_prefix(
        "Suggest a locators.yaml diff. Never write files.",
        f"EXPECTED: {expected_value}",
        f"RANKED CANDIDATES:\n{ranked[:5]!r}",
        f"SUGGESTED DIFF:\n{diff or '(none)'}",
        "Reply JSON verdict/cause/summary/suggestion. Keep writes=false.",
    )
    try:
        system = load_prompt(HEALER_PROMPT, HEALER_VERSION)
    except Exception:
        system = "Locator healer. Suggest yaml only. Never write."
    kernel.run(task, system=system, user=user, tools=(STORE_QUERY, READ_FILE, HIERARCHY_SNAPSHOT))
    # Ranking is store/code-owned — model must not invent a write.
    task.suggestion = suggestion
    if task.verdict == "fixed":
        task.verdict = "diagnosed"
    persist_task(store, task)
    return task


def _ratio(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def _value_for(by: str, node: dict[str, str]) -> str:
    if by == "name":
        return node["name"] or node["id"]
    if by == "path":
        return node["path"] or node["id"]
    if by == "text":
        return node["text"] or node["id"]
    return node["id"] or node["name"]


def _first_element_not_found(store: RunStore, run_id: str) -> str | None:
    for test in store.list_tests(run_id):
        err = str(test.get("error_type") or "")
        if "ElementNotFound" in err:
            return str(test.get("id"))
    return None


def _safe_locators(path: Path) -> LocatorRegistry | None:
    if not path.is_file():
        return None
    try:
        return load_locators(path)
    except Exception:
        return None


def _expected_from_test(
    test: dict[str, Any], registry: LocatorRegistry | None
) -> tuple[str, str | None, str | None, Locator | None]:
    msg = str(test.get("error_message") or "")
    expected = msg
    for prefix in ("not found:", "ElementNotFound:", "missing:"):
        if prefix.lower() in msg.lower():
            expected = msg.split(":", 1)[-1].strip()
            break
    expected = expected.replace("id=", "").replace("name=", "").strip()
    if registry is not None:
        for page in registry.pages():
            for name, loc in registry.locators_for(page).items():
                if loc.value in msg or loc.value == expected:
                    return loc.value, page, name, loc
    return expected, None, None, None


def _load_hierarchy(store: RunStore, run_id: str, test_id: str) -> Any:
    arts = store.list_artifacts(run_id=run_id, test_id=test_id)
    arts += store.list_artifacts(run_id=run_id)
    for art in reversed(arts):
        name = str(art.get("name") or "")
        kind = str(art.get("kind") or "")
        path_s = str(art.get("path") or "")
        if (
            "hierarch" in kind.lower()
            or name.endswith(("hierarchy.json", "hier.json"))
            or path_s.endswith(("hierarchy.json", "hier.json"))
        ):
            path = Path(str(art.get("path") or ""))
            if path.is_file():
                import json

                try:
                    return json.loads(path.read_text(encoding="utf-8-sig"))
                except (OSError, ValueError):
                    continue
    return {"roots": []}
