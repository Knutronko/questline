"""GameLens implications — LLMPort *model reasoning* over *measured* telemetry."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from questline.core.store import RunStore
from questline.lens.diff import DiffReport
from questline.telemetry.schema import FUTURE_EVENT_NAMES

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
        }


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
    limit_per_snapshot: int = 20,
) -> tuple[dict[str, Any], tuple[str, ...]]:
    """Pull telemetry_sessions.summary for snapshot ids. Never impute missing KPIs."""
    gaps: list[str] = []
    sessions_out: list[dict[str, Any]] = []
    if store is None:
        gaps.append("no run store attached; measured telemetry unavailable")
        gaps.append(
            "KPI combat.damage is not in telemetry_sessions.summary "
            "(reserved FUTURE_EVENT_NAMES; not imputed)"
        )
        return {"sessions": [], "session_count": 0}, tuple(gaps)

    snap_ids = [s for s in (report.snapshot_id_a, report.snapshot_id_b) if s]
    versions = [v for v in (report.version_a, report.version_b) if v]

    for snap_id in snap_ids:
        if snap_id in {"snap-unset", "unset"}:
            gaps.append(
                f"config_snapshot_id={snap_id}; sessions cannot join to a GameLens snapshot"
            )
            continue
        found = store.list_telemetry_sessions(
            config_snapshot_id=snap_id, limit=limit_per_snapshot
        )
        if not found:
            gaps.append(f"no telemetry_sessions for config_snapshot_id={snap_id}")
            continue
        sessions_out.extend(_session_measured(row) for row in found)

    if not sessions_out:
        for ver in versions:
            found = store.list_telemetry_sessions(game_version=ver, limit=limit_per_snapshot)
            if found:
                sessions_out.extend(_session_measured(row) for row in found)
                gaps.append(
                    f"joined telemetry by game_version={ver} "
                    "(no matching config_snapshot_id)"
                )

    if not sessions_out:
        gaps.append("no measured telemetry_sessions.summary available for this diff")

    # Thin summary never includes D12/G2+ reserved names.
    if "combat.damage" in FUTURE_EVENT_NAMES:
        gaps.append(
            "KPI combat.damage is not in telemetry_sessions.summary "
            "(reserved FUTURE_EVENT_NAMES; not imputed)"
        )

    measured = {
        "sessions": sessions_out,
        "session_count": len(sessions_out),
        "snapshot_id_a": report.snapshot_id_a,
        "snapshot_id_b": report.snapshot_id_b,
        "version_a": report.version_a,
        "version_b": report.version_b,
    }
    return measured, tuple(dict.fromkeys(gaps))


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

    system = load_prompt("lens_implications", "v1")
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
