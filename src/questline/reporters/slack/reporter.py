"""SlackReporter — start post + finish update/thread + failure replies."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from questline.core.config import Settings
from questline.core.errors import AuthoringError
from questline.core.events import Event, RunStarted
from questline.reporters.allowlist import render_template
from questline.reporters.port import RunSummary, TestResultSummary
from questline.reporters.slack.transport import HttpSlackTransport, SlackTransport

logger = logging.getLogger("questline.reporters.slack")

_TEMPLATES = Path(__file__).resolve().parent / "templates"


class SlackReporter:
    """Posts run lifecycle to Slack via webhook or bot token.

    Secrets: ``QUESTLINE_SLACK_TOKEN`` / ``QUESTLINE_SLACK_WEBHOOK`` (never toml).
    Channel (non-secret): ``slack_channel`` in profile or ``QUESTLINE_SLACK_CHANNEL``.
    """

    def __init__(
        self,
        *,
        settings: Settings,
        transport: SlackTransport | None = None,
        templates_dir: Path | None = None,
    ) -> None:
        self.settings = settings
        self.channel = getattr(settings, "slack_channel", None)
        self._templates = Path(templates_dir) if templates_dir else _TEMPLATES
        self._start_ts: str | None = None
        self._channel: str | None = self.channel
        self._use_webhook = False
        if transport is None:
            if settings.slack_webhook and not settings.slack_token:
                self._use_webhook = True
            elif not settings.slack_webhook and not settings.slack_token:
                raise AuthoringError(
                    "SlackReporter requires QUESTLINE_SLACK_WEBHOOK or "
                    "QUESTLINE_SLACK_TOKEN. Secrets must be set via environment "
                    "variables, never questline.toml."
                )
            self.transport = HttpSlackTransport(
                token=settings.slack_token,
                webhook_url=settings.slack_webhook,
            )
        else:
            # Prefer bot-style APIs when a transport is injected (CI fakes).
            self.transport = transport
            if settings.slack_webhook and not settings.slack_token:
                self._use_webhook = True

    def on_event(self, event: Event) -> None:
        if not isinstance(event, RunStarted):
            return
        text = render_template(
            self._load("start.txt"),
            {
                "run_id": event.run_id,
                "profile": event.profile or self.settings.profile,
                "driver": self.settings.driver,
                "device": self.settings.device,
            },
        )
        if self._use_webhook:
            self.transport.post_webhook(text=text)
            return
        result = self.transport.post_message(text=text, channel=self.channel)
        self._start_ts = str(result.get("ts") or "")
        self._channel = str(result.get("channel") or self.channel or "")

    def finalize(self, run_summary: RunSummary) -> None:
        text = render_template(
            self._load("finish.txt"),
            {
                "run_id": run_summary.run_id,
                "profile": run_summary.profile,
                "status": run_summary.status,
                "duration_s": (
                    f"{run_summary.duration_s:.2f}"
                    if run_summary.duration_s is not None
                    else ""
                ),
                "driver": run_summary.driver or self.settings.driver,
                "device": run_summary.device or self.settings.device,
                "passed": run_summary.passed,
                "failed": run_summary.failed,
                "skipped": run_summary.skipped,
                "total": run_summary.total,
                "infra_failures": run_summary.infra_failures,
                "test_failures": run_summary.test_failures,
                "authoring_failures": run_summary.authoring_failures,
            },
        )
        if self._use_webhook:
            self.transport.post_webhook(text=text)
            for failure in run_summary.failed_tests():
                self.transport.post_webhook(
                    text=render_template(
                        self._load("failure.txt"),
                        _failure_ctx(failure, run_summary.run_id),
                    )
                )
            return

        if self._start_ts and self._channel:
            self.transport.update_message(
                channel=self._channel, ts=self._start_ts, text=text
            )
        else:
            result = self.transport.post_message(text=text, channel=self.channel)
            self._start_ts = str(result.get("ts") or "")
            self._channel = str(result.get("channel") or self.channel or "")

        for failure in run_summary.failed_tests():
            if not self._start_ts or not self._channel:
                break
            self.transport.post_reply(
                channel=self._channel,
                thread_ts=self._start_ts,
                text=render_template(
                    self._load("failure.txt"),
                    _failure_ctx(failure, run_summary.run_id),
                ),
            )

    def _load(self, name: str) -> str:
        return (self._templates / name).read_text(encoding="utf-8")


def _failure_ctx(failure: TestResultSummary, run_id: str) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "nodeid": failure.nodeid,
        "test_id": failure.test_id,
        "verdict": failure.verdict,
        "error_type": failure.error_type,
        "error_message": failure.error_message,
        "death_step_name": failure.death_step_name,
    }
