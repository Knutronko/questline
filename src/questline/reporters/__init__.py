"""ReporterPort adapters — console, HTML, Slack, GitHub Issues (+ stubs)."""

from questline.reporters.port import ReporterPort, RunSummary, TestResultSummary
from questline.reporters.registry import build_reporters, finalize_all

__all__ = [
    "ReporterPort",
    "RunSummary",
    "TestResultSummary",
    "build_reporters",
    "finalize_all",
]
