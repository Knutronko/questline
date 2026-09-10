"""GameLens implications — LLMPort *model reasoning* over *measured* telemetry."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from questline.core.store import RunStore
from questline.lens.diff import DiffReport
from questline.telemetry.schema import FUTURE_EVENT_NAMES

PROMPT_NAME = "lens_implications"
PROMPT_VERSION = "v1"

_UNSET_SNAPSHOT_IDS = frozenset({"snap-unset", "unset"})

_SUMMARY_KEYS = (
    "outcome",
    "duration_s",
    "deploy_count",
    "skill_casts",
    "repair_count",
    "leak_count",
    "time_to_first_leak",
    "waves_started",
    "waves_completed",
    "checkpoint_labels",
    "currency_net",
    "event_counts",
)


@dataclass(frozen=True, slots=True)
class ImplicationsReport:
    """Labeled *model reasoning* (never a pass/fail verdict)."""

    status: str
    framing: str
    summary: str
    pending: str | None = None
    diff_entry_count: int = 0
    measured: dict[str, Any] = field(default_factory=dict)
    gaps: tuple[str, ...] = ()
    purpose_tag: str = "lens.implications"
    prompt_version: str = PROMPT_VERSION
    artifact_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "framing": self.framing,
            "summary": self.summary,
            "pending": self.pending,
            "diff_entry_count": self.diff_entry_count,
            "measured": self.measured,
            "gaps": list(self.gaps),
            "purpose_tag": self.purpose_tag,
            "prompt_version": self.prompt_version,
            "artifact_path": self.artifact_path,
        }

    def with_artifact(self, path: Path | str) -> ImplicationsReport:
        return ImplicationsReport(
            status=self.status,
            framing=self.framing,
            summary=self.summary,
            pending=self.pending,
            diff_entry_count=self.diff_entry_count,
            measured=self.measured,
            gaps=self.gaps,
            purpose_tag=self.purpose_tag,
            prompt_version=self.prompt_version,
            artifact_path=str(path),
        )


def implications_stub(
    report: DiffReport,
    *,
    measured: dict[str, Any] | None = None,
    gaps: tuple[str, ...] | None = None,
) -> ImplicationsReport:
    """No LLM provider configured — still surface measured facts and gaps."""
    meas = measured or {}
    gap_t = gaps if gaps is not None else ()
    extra = ""
    if gap_t:
        extra = " Gaps: " + "; ".join(gap_t)
    return ImplicationsReport(
        status="skipped",
        framing="model reasoning",
        summary=(
            "No LLM provider configured (see docs/ai-setup.md). "
            f"Diff has {len(report.entries)} typed entries "
            f"({report.version_a} -> {report.version_b}). "
            "Numbers below are measured; missing KPIs are not imputed."
            + extra
        ),
        pending="no-provider",
        diff_entry_count=len(report.entries),
        measured=meas,
        gaps=gap_t,
    )


def collect_measured(
    store: RunStore | None,
    report: DiffReport,
    *,
    limit_per_snapshot: int = 100,
) -> tuple[dict[str, Any], tuple[str, ...]]:
    """Pull telemetry_sessions.summary for snapshot ids. Never impute missing KPIs.

    Joined ``sessions`` require an exact ``config_snapshot_id`` match to snapshot
    A/B. ``snap-unset`` / missing ids never join silently: they land in
    ``unjoined`` when ``game_version`` matches, otherwise a count-only gap.
    """
    gaps: list[str] = []
    sessions_out: list[dict[str, Any]] = []
    unjoined_out: list[dict[str, Any]] = []
    fetch_limit = max(int(limit_per_snapshot), 1)

    if store is None:
        gaps.append("no run store attached; measured telemetry unavailable")
        _append_future_kpi_gaps(gaps)
        return _measured_payload(report, sessions_out, unjoined_out), tuple(gaps)

    snap_ids = [s for s in (report.snapshot_id_a, report.snapshot_id_b) if s]
    versions = [v for v in (report.version_a, report.version_b) if v]
    real_snap_ids: list[str] = []
    for snap_id in snap_ids:
        if _is_unset_snapshot(snap_id):
            gaps.append(
                f"config_snapshot_id={snap_id}; sessions cannot join to a GameLens snapshot"
            )
            continue
        real_snap_ids.append(snap_id)

    seen: set[str] = set()
    for snap_id in real_snap_ids:
        found = store.list_telemetry_sessions(
            config_snapshot_id=snap_id, limit=fetch_limit
        )
        if not found:
            gaps.append(f"no telemetry_sessions for config_snapshot_id={snap_id}")
            continue
        for row in found:
            rid = str(row.get("id") or "")
            if rid and rid in seen:
                continue
            if rid:
                seen.add(rid)
            sessions_out.append(_session_measured(row))

    for ver in versions:
        for row in store.list_telemetry_sessions(game_version=ver, limit=fetch_limit):
            rid = str(row.get("id") or "")
            if rid and rid in seen:
                continue
            if not _is_unset_snapshot(row.get("config_snapshot_id")):
                continue
            if rid:
                seen.add(rid)
            unjoined_out.append(_session_measured(row))

    if unjoined_out:
        gaps.append(
            "config_snapshot_id=snap-unset; sessions cannot join to a GameLens snapshot"
        )

    outside = _count_unset_outside_versions(store, versions, seen, limit=fetch_limit)
    if outside:
        gaps.append(
            f"{outside} telemetry_sessions have config_snapshot_id=snap-unset "
            "with game_version outside this diff; not joined"
        )

    if not sessions_out and not unjoined_out:
        gaps.append("no measured telemetry_sessions.summary available for this diff")

    _append_future_kpi_gaps(gaps)

    return _measured_payload(report, sessions_out, unjoined_out), tuple(dict.fromkeys(gaps))


def persist_implications(
    store: RunStore,
    report: DiffReport,
    implications: ImplicationsReport,
    *,
    prompt_version: str = PROMPT_VERSION,
) -> ImplicationsReport:
    """Write implications.json + .md under artifacts/lens/<pair>/ and index the store."""
    pair_id = implications_pair_id(report)
    dest_dir = store.artifacts_dir / "lens" / pair_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    json_path = dest_dir / "implications.json"
    md_path = dest_dir / "implications.md"
    labeled = implications.with_artifact(json_path)
    payload = labeled.to_dict()
    payload["snapshot_id_a"] = report.snapshot_id_a
    payload["snapshot_id_b"] = report.snapshot_id_b
    payload["version_a"] = report.version_a
    payload["version_b"] = report.version_b
    json_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    md_path.write_text(
        render_implications_markdown(labeled, report),
        encoding="utf-8",
    )
    measured = labeled.measured if isinstance(labeled.measured, dict) else {}
    store.save_lens_implications(
        pair_id=pair_id,
        snapshot_id_a=report.snapshot_id_a,
        snapshot_id_b=report.snapshot_id_b,
        version_a=report.version_a,
        version_b=report.version_b,
        status=labeled.status,
        framing=labeled.framing,
        prompt_version=prompt_version,
        artifact_path=str(json_path),
        meta={
            "session_count": measured.get("session_count", 0),
            "unjoined_count": measured.get("unjoined_count", 0),
            "gap_count": len(labeled.gaps),
            "pending": labeled.pending,
            "md_path": str(md_path),
        },
    )
    return labeled


def implications_pair_id(report: DiffReport) -> str:
    left = report.snapshot_id_a or report.version_a or "a"
    right = report.snapshot_id_b or report.version_b or "b"
    return f"{_safe_path_token(left)}__{_safe_path_token(right)}"


def render_implications_markdown(
    implications: ImplicationsReport,
    report: DiffReport,
) -> str:
    lines = [
        f"# GameLens implications ({report.version_a} -> {report.version_b})",
        "",
        f"- framing: {implications.framing}",
        f"- status: {implications.status}",
        f"- prompt: {PROMPT_NAME}.{implications.prompt_version}",
        f"- snapshots: {report.snapshot_id_a or '?'} -> {report.snapshot_id_b or '?'}",
        f"- diff_entry_count: {implications.diff_entry_count}",
    ]
    if implications.pending:
        lines.append(f"- pending: {implications.pending}")
    if implications.artifact_path:
        lines.append(f"- artifact: {implications.artifact_path}")
    lines.append("")
    lines.append("## Gaps")
    lines.append("")
    if implications.gaps:
        for gap in implications.gaps:
            lines.append(f"- {gap}")
    else:
        lines.append("- (none)")
    lines.append("")
    lines.append("## Model reasoning")
    lines.append("")
    lines.append(implications.summary.strip() or "(empty)")
    lines.append("")
    lines.append("## Measured (telemetry_sessions.summary; not model output)")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(implications.measured, indent=2, sort_keys=True, default=str))
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def build_implications(
    report: DiffReport,
    *,
    store: RunStore | None = None,
    router: Any | None = None,
) -> ImplicationsReport:
    """Live LLMPort when *router* is set; otherwise the no-provider stub."""
    measured, gaps = collect_measured(store, report)
    if router is None:
        return implications_stub(report, measured=measured, gaps=gaps)
    from questline.ai.port import LlmMessage, LlmRequest
    from questline.ai.prompts.store import compose_stable_prefix, load_prompt

    system = load_prompt(PROMPT_NAME, PROMPT_VERSION)
    user = compose_stable_prefix(
        "DIFF (typed, config truth):",
        json.dumps(report.to_dict(), sort_keys=True, default=str),
        "MEASURED (telemetry_sessions.summary only):",
        json.dumps(measured, sort_keys=True, default=str),
        "GAPS (do not fill):",
        json.dumps(list(gaps), sort_keys=True),
    )
    try:
        resp = router.complete(
            LlmRequest(
                system=system,
                messages=(LlmMessage(role="user", content=user),),
                max_tokens=512,
                temperature=0.0,
                purpose_tag="lens.implications",
                model_class="fast",
            )
        )
    except Exception as exc:
        return ImplicationsReport(
            status="error",
            framing="model reasoning",
            summary=f"LLMPort failed ({type(exc).__name__}: {exc}). Measured facts unchanged.",
            pending=None,
            diff_entry_count=len(report.entries),
            measured=measured,
            gaps=gaps,
        )
    return ImplicationsReport(
        status="ok",
        framing="model reasoning",
        summary=resp.text,
        pending=None,
        diff_entry_count=len(report.entries),
        measured=measured,
        gaps=gaps,
    )


def _is_unset_snapshot(value: Any) -> bool:
    if value is None:
        return True
    text = str(value).strip()
    if not text:
        return True
    return text.lower() in _UNSET_SNAPSHOT_IDS


def _safe_path_token(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._@+-]+", "_", value.strip())
    return cleaned or "unset"


def _append_future_kpi_gaps(gaps: list[str]) -> None:
    names = ", ".join(sorted(FUTURE_EVENT_NAMES))
    gaps.append(
        "KPIs not in telemetry_sessions.summary "
        f"(reserved FUTURE_EVENT_NAMES; not imputed): {names}"
    )


def _group_by_policy(sessions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = {}
    for session in sessions:
        key = str(session.get("policy_id") or "")
        buckets.setdefault(key, []).append(session)
    grouped: list[dict[str, Any]] = []
    for key in sorted(buckets):
        rows = buckets[key]
        outcomes: dict[str, int] = {}
        seeds: list[str] = []
        for row in rows:
            outcome = str(row.get("outcome") or "unknown")
            outcomes[outcome] = outcomes.get(outcome, 0) + 1
            seed = row.get("seed")
            if seed is not None and str(seed) != "":
                seeds.append(str(seed))
        grouped.append(
            {
                "policy_id": key or None,
                "session_count": len(rows),
                "outcomes": outcomes,
                "seeds": sorted(set(seeds)),
            }
        )
    return grouped


def _measured_payload(
    report: DiffReport,
    sessions: list[dict[str, Any]],
    unjoined: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "sessions": sessions,
        "session_count": len(sessions),
        "unjoined": unjoined,
        "unjoined_count": len(unjoined),
        "by_policy": _group_by_policy(sessions),
        "unjoined_by_policy": _group_by_policy(unjoined),
        "snapshot_id_a": report.snapshot_id_a,
        "snapshot_id_b": report.snapshot_id_b,
        "version_a": report.version_a,
        "version_b": report.version_b,
    }


def _count_unset_outside_versions(
    store: RunStore,
    versions: list[str],
    already: set[str],
    *,
    limit: int,
) -> int:
    versions_set = set(versions)
    extra = 0
    seen = set(already)
    for label in ("snap-unset", "unset"):
        for row in store.list_telemetry_sessions(
            config_snapshot_id=label, limit=limit
        ):
            rid = str(row.get("id") or "")
            if rid and rid in seen:
                continue
            if rid:
                seen.add(rid)
            if row.get("game_version") not in versions_set:
                extra += 1
    return extra


def _session_measured(row: dict[str, Any]) -> dict[str, Any]:
    summary = row.get("summary") if isinstance(row.get("summary"), dict) else {}
    thin = {k: summary.get(k) for k in _SUMMARY_KEYS if k in summary}
    return {
        "id": row.get("id"),
        "game_version": row.get("game_version"),
        "config_snapshot_id": row.get("config_snapshot_id"),
        "policy_id": row.get("policy_id"),
        "seed": row.get("seed"),
        "outcome": row.get("outcome") or thin.get("outcome"),
        "summary": thin,
    }
