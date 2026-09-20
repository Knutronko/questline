"""Allow-listed agent tools. Write tools are stripped in hermetic read-only mode."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from questline.ai.port import ImagePart
from questline.core.store import RunStore

MAX_TOOL_RESULT_CHARS = 8000
MAX_GREP_HITS = 40
MAX_FILE_CHARS = 12000

_SECRET_NAMES = frozenset({".env", "credentials.json", "id_rsa", "id_ed25519"})
_WRITE_SHELL = re.compile(
    r"(^|[;&|]\s*)("
    r"rm\s|del\s|rmdir\s|rd\s|ni\s|new-item\b|set-content\b|out-file\b|"
    r"move-item\b|remove-item\b|copy-item\b|tee\b|echo\s+.*>"
    r")|"
    r"(^|[;&|]\s*).*(>|>>)\s*\S",
    re.IGNORECASE,
)


@dataclass
class ToolContext:
    store: RunStore
    project_root: Path
    run_id: str | None = None
    test_id: str | None = None
    locators_path: Path | None = None
    quarantine_path: Path | None = None
    run_pytest: Callable[..., dict[str, Any]] | None = None
    pending_images: list[ImagePart] = field(default_factory=list)


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any]
    handler: Callable[[ToolContext, dict[str, Any]], dict[str, Any]]
    write: bool = False
    shell: bool = False

    def schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


def looks_like_write_command(command: str) -> bool:
    text = (command or "").strip()
    if not text:
        return False
    return _WRITE_SHELL.search(text) is not None


def jail_path(ctx: ToolContext, raw: str) -> Path | None:
    """Resolve *raw* under project_root or artifacts_dir. None = denied."""
    if not raw or not str(raw).strip():
        return None
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = ctx.project_root / candidate
    try:
        resolved = candidate.resolve()
    except OSError:
        return None
    roots = (ctx.project_root.resolve(), ctx.store.artifacts_dir.resolve())
    if not any(_is_relative_to(resolved, root) for root in roots):
        return None
    name = resolved.name.lower()
    if name in _SECRET_NAMES or name.endswith(".pem") or name.startswith(".env"):
        return None
    return resolved


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def clip(text: str, limit: int = MAX_TOOL_RESULT_CHARS) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 20] + "\n…[truncated]"


def parse_args(raw: str) -> dict[str, Any]:
    text = (raw or "").strip()
    if not text:
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _read_file(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    path = jail_path(ctx, str(args.get("path") or ""))
    if path is None:
        return {"tool": "read_file", "error": "path denied (jail or secret name)"}
    if not path.is_file():
        return {"tool": "read_file", "error": f"not a file: {path.name}"}
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return {"tool": "read_file", "error": str(exc)}
    return {"tool": "read_file", "path": path.name, "content": clip(text, MAX_FILE_CHARS)}


def _grep_scoped(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    pattern = str(args.get("pattern") or "")
    if not pattern:
        return {"tool": "grep_scoped", "error": "pattern required"}
    try:
        rx = re.compile(pattern)
    except re.error as exc:
        return {"tool": "grep_scoped", "error": f"bad pattern: {exc}"}
    scope = str(args.get("path") or ".")
    root = jail_path(ctx, scope) or ctx.project_root.resolve()
    hits: list[dict[str, str]] = []
    skip = {".git", ".venv", "node_modules", "__pycache__", ".questline"}
    try:
        if root.is_file():
            files = [root]
        else:
            files = [p for p in root.rglob("*") if p.is_file() and skip.isdisjoint(p.parts)]
        for path in files[:400]:
            if path.suffix.lower() not in {".py", ".yaml", ".yml", ".md", ".toml", ".json", ".txt"}:
                continue
            try:
                lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                continue
            for i, line in enumerate(lines, start=1):
                if rx.search(line):
                    rel = str(path.relative_to(ctx.project_root.resolve()))
                    hits.append({"path": rel, "line": str(i), "text": line.strip()[:200]})
                    if len(hits) >= MAX_GREP_HITS:
                        return {"tool": "grep_scoped", "hits": hits, "truncated": True}
    except OSError as exc:
        return {"tool": "grep_scoped", "error": str(exc)}
    return {"tool": "grep_scoped", "hits": hits, "truncated": False}


def _store_query(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    run_id = str(args.get("run_id") or ctx.run_id or "")
    if not run_id:
        return {"tool": "store_query", "error": "run_id required"}
    run = ctx.store.get_run(run_id)
    if run is None:
        return {"tool": "store_query", "error": f"unknown run {run_id}"}
    tests = ctx.store.list_tests(run_id)
    test_id = str(args.get("test_id") or ctx.test_id or "")
    payload: dict[str, Any] = {
        "tool": "store_query",
        "run": {
            "id": run.get("id"),
            "profile": run.get("profile"),
            "status": run.get("status"),
        },
        "tests": [
            {
                "id": t.get("id"),
                "nodeid": t.get("nodeid"),
                "status": t.get("status"),
                "verdict": t.get("verdict"),
                "error_type": t.get("error_type"),
                "error_message": t.get("error_message"),
            }
            for t in tests
        ],
    }
    if test_id:
        test = ctx.store.get_test(test_id)
        if test is not None:
            payload["test"] = {
                "id": test.get("id"),
                "nodeid": test.get("nodeid"),
                "status": test.get("status"),
                "verdict": test.get("verdict"),
                "error_type": test.get("error_type"),
                "error_message": test.get("error_message"),
            }
            payload["steps"] = [
                {"name": s.get("name"), "status": s.get("status"), "error": s.get("error_message")}
                for s in ctx.store.list_steps(test_id)
            ]
            payload["death_point"] = ctx.store.death_point(test_id)
            payload["artifacts"] = [
                {"path": a.get("path"), "kind": a.get("kind")}
                for a in ctx.store.list_artifacts(run_id=run_id, test_id=test_id)
            ]
    return payload


def _read_screenshot(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    arts = ctx.store.list_artifacts(run_id=ctx.run_id, test_id=ctx.test_id)
    shots = [a for a in arts if str(a.get("kind") or "") == "screenshot"]
    if not shots:
        named = str(args.get("path") or "")
        if named:
            path = jail_path(ctx, named)
            if path is None or not path.is_file():
                return {"tool": "read_screenshot", "error": "screenshot not found"}
            data = path.read_bytes()
            ctx.pending_images.append(ImagePart(media_type="image/png", data=data))
            return {"tool": "read_screenshot", "bytes": len(data), "attached": True}
        return {"tool": "read_screenshot", "error": "no screenshot artifact"}
    raw_path = str(shots[-1].get("path") or "")
    path = jail_path(ctx, raw_path)
    if path is None or not path.is_file():
        return {"tool": "read_screenshot", "error": "screenshot path denied"}
    data = path.read_bytes()
    ctx.pending_images.append(ImagePart(media_type="image/png", data=data))
    return {"tool": "read_screenshot", "bytes": len(data), "attached": True, "name": path.name}


def _hierarchy_snapshot(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    arts = ctx.store.list_artifacts(run_id=ctx.run_id, test_id=ctx.test_id)
    hier = [
        a
        for a in arts
        if "hierarch" in str(a.get("kind") or "").lower()
        or str(a.get("path") or "").endswith(("hierarchy.json", "hier.json"))
        or str(a.get("name") or "").endswith(("hierarchy.json", "hier.json"))
    ]
    named = str(args.get("path") or "")
    path: Path | None = None
    if named:
        path = jail_path(ctx, named)
    elif hier:
        path = jail_path(ctx, str(hier[-1].get("path") or ""))
    if path is None or not path.is_file():
        return {"tool": "hierarchy_snapshot", "error": "no hierarchy snapshot artifact"}
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        return {"tool": "hierarchy_snapshot", "error": str(exc)}
    return {"tool": "hierarchy_snapshot", "snapshot": data}


def _write_file(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    path = jail_path(ctx, str(args.get("path") or ""))
    if path is None:
        return {"tool": "write_file", "error": "path denied"}
    content = str(args.get("content") or "")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    except OSError as exc:
        return {"tool": "write_file", "error": str(exc)}
    return {"tool": "write_file", "ok": True, "path": path.name, "bytes": len(content.encode())}


def _run_shell(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    command = str(args.get("command") or "")
    if looks_like_write_command(command):
        return {"tool": "run_shell", "error": "write pattern blocked (hermetic read-only)"}
    return {"tool": "run_shell", "error": "run_shell is not enabled"}


def _run_test(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    nodeid = str(args.get("nodeid") or "")
    if not nodeid:
        return {"tool": "run_test", "error": "nodeid required"}
    fn = ctx.run_pytest
    if fn is None:
        result = default_run_pytest(nodeid, cwd=ctx.project_root)
    else:
        result = fn(nodeid)
    result["tool"] = "run_test"
    return result


def _propose_quarantine(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    from questline.authoring.quarantine import QuarantineLedger

    test_id = str(args.get("test_id") or ctx.test_id or "")
    reason = str(args.get("reason") or "agent proposal")
    owner = str(args.get("owner") or "agent")
    exit_criteria = str(args.get("exit_criteria") or "reproduced green twice")
    if not test_id:
        return {"tool": "propose_quarantine", "error": "test_id required"}
    path = ctx.quarantine_path or (ctx.project_root / "quarantine.yaml")
    ledger = QuarantineLedger.load(path)
    entry = ledger.add(
        test_id,
        reason=reason,
        owner=owner,
        exit_criteria=exit_criteria,
        issue=str(args["issue"]) if args.get("issue") else None,
    )
    ledger.save()
    return {"tool": "propose_quarantine", "ok": True, "test_id": entry.test_id}


def default_run_pytest(nodeid: str, *, cwd: Path, timeout_s: float = 60.0) -> dict[str, Any]:
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            nodeid,
            "--tb=line",
            "-q",
            "-p",
            "no:cov",
            "-o",
            "addopts=",
        ],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=timeout_s,
        check=False,
    )
    stdout = clip((proc.stdout or "")[-4000:])
    stderr = clip((proc.stderr or "")[-2000:])
    return {
        "nodeid": nodeid,
        "returncode": proc.returncode,
        "green": proc.returncode == 0,
        "stdout": stdout,
        "stderr": stderr,
    }


def schemas_for(specs: list[ToolSpec], *, read_only: bool) -> tuple[dict[str, Any], ...]:
    chosen = [s for s in specs if not (read_only and s.write)]
    return tuple(s.schema() for s in chosen)


READ_FILE = ToolSpec(
    name="read_file",
    description="Read a text file under the project or artifacts jail.",
    parameters={
        "type": "object",
        "properties": {"path": {"type": "string"}},
        "required": ["path"],
        "additionalProperties": False,
    },
    handler=_read_file,
)
GREP_SCOPED = ToolSpec(
    name="grep_scoped",
    description="Regex search under the project jail (source-like files only).",
    parameters={
        "type": "object",
        "properties": {
            "pattern": {"type": "string"},
            "path": {"type": "string"},
        },
        "required": ["pattern"],
        "additionalProperties": False,
    },
    handler=_grep_scoped,
)
STORE_QUERY = ToolSpec(
    name="store_query",
    description="Read run/test verdicts, steps, death-point, artifacts from the store.",
    parameters={
        "type": "object",
        "properties": {
            "run_id": {"type": "string"},
            "test_id": {"type": "string"},
        },
        "additionalProperties": False,
    },
    handler=_store_query,
)
READ_SCREENSHOT = ToolSpec(
    name="read_screenshot",
    description="Attach the latest screenshot artifact as a native image block.",
    parameters={
        "type": "object",
        "properties": {"path": {"type": "string"}},
        "additionalProperties": False,
    },
    handler=_read_screenshot,
)
HIERARCHY_SNAPSHOT = ToolSpec(
    name="hierarchy_snapshot",
    description="Read a persisted hierarchy snapshot JSON artifact.",
    parameters={
        "type": "object",
        "properties": {"path": {"type": "string"}},
        "additionalProperties": False,
    },
    handler=_hierarchy_snapshot,
)
WRITE_FILE = ToolSpec(
    name="write_file",
    description="Write a text file under the project jail (fix mode only).",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "content": {"type": "string"},
        },
        "required": ["path", "content"],
        "additionalProperties": False,
    },
    handler=_write_file,
    write=True,
)
RUN_SHELL = ToolSpec(
    name="run_shell",
    description="Not enabled. Present so hermetic tests can attempt a write.",
    parameters={
        "type": "object",
        "properties": {"command": {"type": "string"}},
        "required": ["command"],
        "additionalProperties": False,
    },
    handler=_run_shell,
    write=False,
    shell=True,
)
RUN_TEST = ToolSpec(
    name="run_test",
    description="Run one pytest nodeid. The anti-false-green gate re-runs independently.",
    parameters={
        "type": "object",
        "properties": {"nodeid": {"type": "string"}},
        "required": ["nodeid"],
        "additionalProperties": False,
    },
    handler=_run_test,
    write=True,
)
PROPOSE_QUARANTINE = ToolSpec(
    name="propose_quarantine",
    description="Add a quarantine ledger entry (never edit markers).",
    parameters={
        "type": "object",
        "properties": {
            "test_id": {"type": "string"},
            "reason": {"type": "string"},
            "owner": {"type": "string"},
            "exit_criteria": {"type": "string"},
            "issue": {"type": "string"},
        },
        "additionalProperties": False,
    },
    handler=_propose_quarantine,
    write=True,
)

READONLY_TOOLS = (STORE_QUERY, READ_FILE, GREP_SCOPED, READ_SCREENSHOT, HIERARCHY_SNAPSHOT)
FIX_TOOLS = READONLY_TOOLS + (WRITE_FILE, RUN_TEST, PROPOSE_QUARANTINE)
