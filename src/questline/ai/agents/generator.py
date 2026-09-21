"""Spec → scenario test. Success is owned by the pytest collect/execute gate."""

from __future__ import annotations

import ast
import re
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from questline.ai.agents.gate import (
    classify_collect,
    classify_pytest,
    expected_from_spec,
    spec_matches,
)
from questline.ai.agents.kernel import AgentKernel, new_task_id
from questline.ai.agents.persist import persist_task
from questline.ai.agents.prompts import GENERATOR_PROMPT, GENERATOR_VERSION
from questline.ai.agents.schema import extract_json
from questline.ai.agents.task import AgentTask
from questline.ai.agents.tools import GENERATOR_TOOLS, ToolContext, clip
from questline.ai.prompts.store import compose_stable_prefix, load_prompt
from questline.core.store import RunStore

PURPOSE_TAG = "agent.generator"
GateMode = Literal["execute", "collect"]


def generated_pytest_path(out_dir: Path, task_id: str) -> Path:
    slug = task_id.removeprefix("gen-").replace("-", "")
    return out_dir / f"test_gen_{slug}.py"


def _existing_pytest(out_dir: Path) -> set[Path]:
    if not out_dir.is_dir():
        return set()
    return {p.resolve() for p in out_dir.glob("test_*.py") if p.is_file()}


def suite_layout(root: Path) -> dict[str, bool]:
    """What the generator may read under the HUD/CLI project root."""
    pages_dir = (root / "pages").is_dir()
    return {
        "has_pages": pages_dir or (root / "pages.py").is_file(),
        "has_locators": (root / "locators.yaml").is_file(),
        "has_suites": (root / "suites").is_dir(),
    }


def infer_gate_mode(root: Path) -> GateMode:
    layout = suite_layout(root)
    if layout["has_pages"] or layout["has_locators"]:
        return "collect"
    return "execute"


_HINTS_MAX = 2400
_DEFERRED_MARK = re.compile(r"\b(deferred|poco)\b", re.IGNORECASE)


def _page_source_files(root: Path) -> list[Path]:
    files: list[Path] = []
    single = root / "pages.py"
    if single.is_file():
        files.append(single)
    folder = root / "pages"
    if folder.is_dir():
        files.extend(sorted(p for p in folder.glob("*.py") if p.is_file()))
    return files


def _page_method_lines(root: Path) -> tuple[list[str], list[str]]:
    """Return (inventory lines, Page class names) from pages/ without executing them."""
    lines: list[str] = []
    classes: list[str] = []
    for path in _page_source_files(root):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeDecodeError):
            continue
        try:
            rel = path.relative_to(root).as_posix()
        except ValueError:
            rel = path.name
        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            methods: list[str] = []
            for item in node.body:
                if not isinstance(item, ast.FunctionDef) or item.name.startswith("_"):
                    continue
                own = ast.get_docstring(item) or ""
                first = own.strip().splitlines()[0][:72] if own.strip() else ""
                sig = _fn_sig(item)
                if _DEFERRED_MARK.search(own):
                    methods.append(f"{sig} (deferred — do not call)")
                elif first:
                    methods.append(f"{sig} — {first}")
                else:
                    methods.append(sig)
            if not methods:
                continue
            classes.append(node.name)
            lines.append(f"{rel} {node.name}: {'; '.join(methods)}")
    return lines, classes


def _fn_sig(item: ast.FunctionDef) -> str:
    args = [a.arg for a in item.args.args if a.arg not in {"self", "cls"}]
    if args:
        return f"{item.name}({', '.join(args)})"
    return f"{item.name}()"


def _locator_page_lines(root: Path) -> list[str]:
    path = root / "locators.yaml"
    if not path.is_file():
        return []
    try:
        import yaml

        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return []
    pages = data.get("pages") if isinstance(data, dict) else None
    if not isinstance(pages, dict):
        return []
    out: list[str] = []
    for name, locs in pages.items():
        if isinstance(locs, dict):
            out.append(f"{name}: {', '.join(str(k) for k in locs)}")
        else:
            out.append(str(name))
    return out[:24]


def _suite_import_example(root: Path) -> str:
    suites = root / "suites"
    if not suites.is_dir():
        return ""
    for path in sorted(suites.glob("test_*.py")):
        if path.name.startswith("test_gen_"):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        snippet = "\n".join(text.splitlines()[:28]).strip()
        if snippet:
            return snippet[:700]
    return ""


def _authoring_hints(root: Path) -> str:
    """Project inventory so the model does not invent imports or Page APIs."""
    methods, classes = _page_method_lines(root)
    locators = _locator_page_lines(root)
    example = _suite_import_example(root)
    import_list = ", ".join(classes[:8]) or "..."
    parts = [
        "HOOKS_FIRST: implement the spec with listed Page methods (hooks), not UI taps.",
        "Do not pytest.skip the test when PAGE_METHODS has a matching hook.",
        "Map spec intent to method names/docs: load/start combat or a level -> "
        "ensure_in_combat / load_level / similar; a 1-based 'level N' in the spec "
        "is level_index N-1 when that argument exists; amounts (amber, currency, "
        "hearts, wave) -> get_* / grant_*; ping -> ping.",
        "Deferred UI methods: do not call them. Call the hook equivalent instead. "
        "pytest.fail TODO only if NO listed non-deferred method matches.",
    ]
    if methods:
        parts.append("PAGE_METHODS:\n" + "\n".join(methods[:12]))
    parts.extend(
        [
        "questline_ctx is a pytest fixture, not a module. "
        "Never write `from questline_ctx import ...`.",
        "Copy this shape:",
        "from pages import " + import_list,
        "from questline.authoring import expect",
        "from questline.authoring.context import Context",
        "def test_from_spec(questline_ctx: Context) -> None:",
        f"    page = {classes[0]}(questline_ctx)" if classes else "    # Page(questline_ctx)",
        "    expect(page.get_amber()).equals(50).evaluate()  # if get_* exists; never to_equal",
        "Assert only with expect(x).equals(y).evaluate() or .differs / .is_true / .is_false.",
        "Never expect(x).to_equal, never assert x == y. Always call .evaluate().",
        "Import only Page classes you construct. Use only Page methods listed below.",
        "After write_file ok, reply JSON only.",
        ]
    )
    if locators:
        parts.append("LOCATOR_PAGES:\n" + "\n".join(locators))
    if example:
        parts.append("EXISTING_SUITE_IMPORTS:\n" + example)
    text = "\n".join(parts)
    return text[:_HINTS_MAX]


def run_generator(
    store: RunStore,
    *,
    spec: str,
    dest: Path,
    router: Any | None = None,
    project_root: Path | None = None,
    run_id: str | None = None,
    rebuild_test_id: str | None = None,
    max_turns: int = 8,
    task_id: str | None = None,
    run_pytest: Callable[..., dict[str, Any]] | None = None,
    gate_run: Callable[[str], dict[str, Any]] | None = None,
    gate_mode: GateMode | None = None,
) -> AgentTask:
    """Write a test from *spec*. Gate must collect (live) or execute (demo)."""
    root = Path(project_root).resolve() if project_root else Path.cwd().resolve()
    out_dir = Path(dest)
    if not out_dir.is_absolute():
        out_dir = root / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    expected = expected_from_spec(spec)
    mode: GateMode = gate_mode or infer_gate_mode(root)
    layout = suite_layout(root)
    history = _rebuild_history(store, rebuild_test_id) if rebuild_test_id else ""
    task = AgentTask(
        id=task_id or new_task_id("gen"),
        kind="generate",
        run_id=run_id,
        test_id=rebuild_test_id,
        status="running",
        prompt_version=GENERATOR_VERSION,
        purpose_tag=PURPOSE_TAG,
        created_at=datetime.now().astimezone().isoformat(),
        evidence=[{"kind": "spec", "text": spec[:2000], "expected": expected}],
    )
    persist_task(store, task)
    assigned = generated_pytest_path(out_dir, task.id)
    preexisting = _existing_pytest(out_dir)

    ctx = ToolContext(
        store=store,
        project_root=root,
        run_id=run_id,
        test_id=rebuild_test_id,
        run_pytest=run_pytest,
    )
    kernel = AgentKernel(
        store,
        router=router,
        ctx=ctx,
        max_turns=max_turns,
        read_only=False,
        purpose_tag=PURPOSE_TAG,
        max_tokens=4096,
        must_write=True,
    )
    has_pages = "yes" if layout["has_pages"] else "no"
    has_locators = "yes" if layout["has_locators"] else "no"
    try:
        write_to = assigned.relative_to(root).as_posix()
    except ValueError:
        write_to = assigned.as_posix()
    user = compose_stable_prefix(
        "MODE: GENERATE",
        f"OUTPUT_DIR: {out_dir}",
        f"WRITE_TEST_TO: {write_to}",
        f"EXPECTED_OUTCOME: {expected}",
        f"PROJECT_ROOT: {root}",
        f"HAS_PAGES: {has_pages}",
        f"HAS_LOCATORS: {has_locators}",
        "Write exactly one NEW pytest file at WRITE_TEST_TO.",
        "Do not edit or overwrite existing tests.",
        "If HAS_PAGES or HAS_LOCATORS is yes: never write MockDriver. "
        "PAGE_METHODS below is the inventory — write_file using it; do not list_dir first.",
        "If both are no: a self-contained MockDriver test is allowed.",
        "Unknown locators: TODO + pytest.fail, never a silent pass.",
        "Do not pytest.skip when listed Page hooks can implement the spec.",
        "Assert with expect(x).equals(y).evaluate() — not to_equal, not assert ==.",
        "Do not read Unity C# or ScriptableObjects.",
        "Reply JSON: verdict/cause/summary/evidence. Do not claim green; the gate owns that.",
        _authoring_hints(root) if layout["has_pages"] or layout["has_locators"] else "",
        f"REBUILD_HISTORY:\n{history}" if history else "REBUILD_HISTORY: (none)",
        f"SPEC:\n{spec}",
    )
    try:
        system = load_prompt(GENERATOR_PROMPT, GENERATOR_VERSION)
    except Exception:
        system = (
            "You generate Questline tests from a spec. Never invent green/red. "
            "JSON verdict/cause/evidence/summary."
        )
    kernel.run(task, system=system, user=user, tools=GENERATOR_TOOLS)

    claim = dict(task.agent_claim or {})
    written = _written_pytest_paths(
        task, out_dir, root, preexisting=preexisting, assigned=assigned
    )
    if not written:
        salvaged = _salvage_pytest_file(task, assigned)
        if salvaged is not None:
            written = [salvaged]
    collect_only = mode == "collect"
    runner = gate_run or (
        (
            lambda nid: _generate_run_pytest(
                nid, cwd=root, collect_only=collect_only
            )
        )
        if run_pytest is None
        else (lambda nid: run_pytest(nid))
    )
    if not written:
        rate = _looks_rate_limited(task)
        llm_fail = task.status == "error" or (task.summary or "").startswith(
            "LLMPort failed"
        )
        if rate:
            reason = "rate_limited"
            extra = (
                " Groq HTTP 429 (rate limit). Wait ~20s and Generate again, "
                "or start Ollama (llama3.2) as fallback."
            )
        elif llm_fail:
            reason = "llm_failed"
            extra = " Gate: LLM did not write a pytest file."
        else:
            reason = "no pytest file written"
            extra = " Gate: no generated test file to execute."
        task.gate = {
            "executed": False,
            "accepted": False,
            "expected": expected,
            "mode": mode,
            "reason": reason,
            "agent_claimed": claim.get("verdict"),
        }
        task.verdict = "inconclusive"
        if not llm_fail and not rate:
            task.status = "ok"
        task.summary = ((task.summary or "") + extra).strip()
        persist_task(store, task)
        return task

    mock_driver = _is_mockdriver(written[0])
    nodeid = _gate_nodeid(written[0], root)
    result = runner(str(written[0]))
    if mode == "collect":
        executed, green = classify_collect(result)
        accepted = executed
        fail_note = " Gate: generated test did not collect; agent claim ignored."
    else:
        executed, green = classify_pytest(result)
        accepted = spec_matches(expected, executed=executed, green=green)
        fail_note = (
            " Gate: generated test did not execute as specified; agent claim ignored."
        )
    task.gate = {
        "executed": executed,
        "green": green,
        "expected": expected,
        "accepted": accepted,
        "mode": mode,
        "nodeid": nodeid,
        "mock_driver": mock_driver,
        "returncode": result.get("returncode"),
        "agent_claimed": claim.get("verdict"),
        "stdout_tail": str(result.get("stdout") or "")[-500:],
    }
    if accepted:
        task.verdict = "passed" if green else "diagnosed"
        task.cause = task.cause if task.cause and task.cause != "unknown" else "test-bug"
        task.status = "ok"
        if mode == "collect":
            if mock_driver:
                task.summary = (
                    (task.summary or "")
                    + " Gate: collected MockDriver (Unity will not move). "
                    "Uncheck Demo and Generate again for a Wire test."
                ).strip()
            else:
                task.summary = (
                    (task.summary or "")
                    + " Gate: collected (not a live Unity/device run). Launch from HUD."
                ).strip()
    else:
        task.verdict = "inconclusive"
        task.status = "ok"
        task.summary = ((task.summary or "") + fail_note).strip()
    persist_task(store, task)
    return task


def _generate_run_pytest(
    nodeid: str, *, cwd: Path, collect_only: bool = False
) -> dict[str, Any]:
    """Pytest with questline.toml when present so generated authoring tests collect."""
    import subprocess
    import sys

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        nodeid,
        "--tb=line",
        "-p",
        "no:cov",
        "-o",
        "addopts=",
        "--rootdir",
        str(cwd),
    ]
    if collect_only:
        cmd.append("--collect-only")
    else:
        cmd.append("-q")
    cfg = cwd / "questline.toml"
    profile = _profile_for_gate(cfg) if cfg.is_file() else None
    if cfg.is_file() and profile:
        cmd.extend(["--questline-config", str(cfg), "--questline-profile", profile])
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=60.0,
        check=False,
    )
    return {
        "nodeid": nodeid,
        "returncode": proc.returncode,
        "green": proc.returncode == 0,
        "stdout": clip((proc.stdout or "")[-4000:]),
        "stderr": clip((proc.stderr or "")[-2000:]),
    }


def _gate_nodeid(path: Path, root: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(resolved)


def _is_mockdriver(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return False
    return "MockDriver" in text


def _profile_for_gate(cfg: Path) -> str | None:
    import tomllib

    try:
        data = tomllib.loads(cfg.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return None
    table = data.get("profile") or {}
    names = [k for k, v in table.items() if isinstance(v, dict)]
    for preferred in ("mock", "editor", "default"):
        if preferred in names:
            return preferred
    return names[0] if names else None


def _pytest_source_from_text(text: str) -> str | None:
    if not text or "def test_" not in text:
        return None
    fences = re.findall(
        r"```(?:python|py)\s*\n(.*?)```", text, flags=re.DOTALL | re.IGNORECASE
    )
    for body in reversed(fences):
        if "def test_" in body:
            return body.strip() + "\n"
    return None


def _salvage_pytest_file(task: AgentTask, assigned: Path) -> Path | None:
    """If the model dumped pytest in text instead of write_file, still land a new file."""
    chunks: list[str] = []
    for entry in task.tool_log:
        if entry.get("name") != "write_file":
            continue
        raw = (entry.get("arguments") or {}).get("content")
        if raw:
            chunks.append(str(raw))
    if task.summary:
        chunks.append(task.summary)
    claim = task.agent_claim or {}
    for key in ("summary", "patch"):
        val = claim.get(key)
        if isinstance(val, str):
            chunks.append(val)
    for item in task.evidence:
        if isinstance(item, dict) and item.get("kind") == "model_text":
            text = str(item.get("text") or "")
            chunks.append(text)
            blob = extract_json(text) or {}
            for key in ("summary", "patch"):
                val = blob.get(key)
                if isinstance(val, str):
                    chunks.append(val)
    source = None
    for chunk in reversed(chunks):
        source = _pytest_source_from_text(chunk)
        if source:
            break
        if "def test_" in chunk and "```" not in chunk:
            source = chunk.strip() + "\n"
            break
    if not source:
        return None
    assigned.parent.mkdir(parents=True, exist_ok=True)
    assigned.write_text(source, encoding="utf-8")
    return assigned


def _written_pytest_paths(
    task: AgentTask,
    out_dir: Path,
    root: Path,
    *,
    preexisting: set[Path],
    assigned: Path,
) -> list[Path]:
    """Only files this turn created. Never fall back to existing suite tests."""
    found: list[Path] = []
    seen: set[Path] = set()
    out_res = out_dir.resolve()
    assigned_res = assigned.resolve()
    for entry in task.tool_log:
        if entry.get("name") != "write_file" or not entry.get("ok"):
            continue
        raw = (entry.get("arguments") or {}).get("path")
        if not raw:
            continue
        for candidate in (
            Path(str(raw)),
            root / str(raw),
            out_dir / Path(str(raw)).name,
            assigned,
        ):
            try:
                resolved = candidate.resolve()
            except OSError:
                continue
            if resolved.suffix != ".py" or not resolved.is_file() or resolved in seen:
                continue
            try:
                resolved.relative_to(out_res)
            except ValueError:
                continue
            if resolved in preexisting and resolved != assigned_res:
                continue
            seen.add(resolved)
            found.append(resolved)
    if assigned_res.is_file() and assigned_res not in preexisting:
        return [assigned_res]
    return found


def _looks_rate_limited(task: AgentTask) -> bool:
    blob = f"{task.summary or ''} {task.pending or ''}".lower()
    return "429" in blob or "rate limited" in blob or "ratelimited" in blob


def _rebuild_history(store: RunStore, test_id: str) -> str:
    rows = store.list_agent_tasks(test_id=test_id, kind="generate", limit=5)
    if not rows:
        tests = store.get_test(test_id)
        if tests:
            return (
                f"store test {test_id} status={tests.get('status')} "
                f"error={tests.get('error_type')} {tests.get('error_message')}"
            )
        return f"no prior generate tasks for {test_id}"
    lines = []
    for row in rows:
        lines.append(
            f"{row.get('created_at')} verdict={row.get('verdict')} "
            f"status={row.get('status')} cause={row.get('cause')}"
        )
    return "\n".join(lines)
