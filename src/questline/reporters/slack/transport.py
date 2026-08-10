"""Slack HTTP transport — real (stdlib) + fake for CI."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class SlackTransport(Protocol):
    def post_message(self, *, text: str, channel: str | None = None) -> dict[str, Any]: ...

    def update_message(
        self, *, channel: str, ts: str, text: str
    ) -> dict[str, Any]: ...

    def post_reply(
        self, *, channel: str, thread_ts: str, text: str
    ) -> dict[str, Any]: ...

    def post_webhook(self, *, text: str) -> dict[str, Any]: ...


@dataclass
class FakeSlackTransport:
    """In-memory Slack API for unit tests (no network)."""

    messages: list[dict[str, Any]] = field(default_factory=list)
    updates: list[dict[str, Any]] = field(default_factory=list)
    replies: list[dict[str, Any]] = field(default_factory=list)
    webhooks: list[dict[str, Any]] = field(default_factory=list)
    _counter: int = 0

    def post_message(self, *, text: str, channel: str | None = None) -> dict[str, Any]:
        self._counter += 1
        ts = f"1000.{self._counter:04d}"
        ch = channel or "C_FAKE"
        row = {"ok": True, "channel": ch, "ts": ts, "text": text}
        self.messages.append(row)
        return row

    def update_message(self, *, channel: str, ts: str, text: str) -> dict[str, Any]:
        row = {"ok": True, "channel": channel, "ts": ts, "text": text}
        self.updates.append(row)
        return row

    def post_reply(self, *, channel: str, thread_ts: str, text: str) -> dict[str, Any]:
        self._counter += 1
        ts = f"1000.{self._counter:04d}"
        row = {
            "ok": True,
            "channel": channel,
            "ts": ts,
            "thread_ts": thread_ts,
            "text": text,
        }
        self.replies.append(row)
        return row

    def post_webhook(self, *, text: str) -> dict[str, Any]:
        row = {"ok": True, "text": text}
        self.webhooks.append(row)
        return row


class HttpSlackTransport:
    """Bot-token + Incoming Webhook via urllib (no slack-sdk required)."""

    def __init__(
        self,
        *,
        token: str | None = None,
        webhook_url: str | None = None,
        timeout_s: float = 30.0,
    ) -> None:
        self.token = token
        self.webhook_url = webhook_url
        self.timeout_s = timeout_s

    def post_message(self, *, text: str, channel: str | None = None) -> dict[str, Any]:
        return self._api(
            "chat.postMessage",
            {"text": text, "channel": channel},
        )

    def update_message(self, *, channel: str, ts: str, text: str) -> dict[str, Any]:
        return self._api(
            "chat.update",
            {"channel": channel, "ts": ts, "text": text},
        )

    def post_reply(self, *, channel: str, thread_ts: str, text: str) -> dict[str, Any]:
        return self._api(
            "chat.postMessage",
            {"text": text, "channel": channel, "thread_ts": thread_ts},
        )

    def post_webhook(self, *, text: str) -> dict[str, Any]:
        if not self.webhook_url:
            raise RuntimeError(
                "QUESTLINE_SLACK_WEBHOOK is not set; cannot post via webhook."
            )
        return self._json_post(self.webhook_url, {"text": text}, auth=False)

    def _api(self, method: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.token:
            raise RuntimeError(
                "QUESTLINE_SLACK_TOKEN is not set; cannot use Slack Web API. "
                "Set QUESTLINE_SLACK_TOKEN or QUESTLINE_SLACK_WEBHOOK."
            )
        url = f"https://slack.com/api/{method}"
        body = {k: v for k, v in payload.items() if v is not None}
        return self._json_post(url, body, auth=True)

    def _json_post(
        self, url: str, payload: dict[str, Any], *, auth: bool
    ) -> dict[str, Any]:
        data = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json; charset=utf-8"}
        if auth and self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                raw = resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Slack HTTP {exc.code}: {body}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Slack request failed: {exc}") from exc
        parsed: dict[str, Any] = json.loads(raw) if raw else {"ok": True}
        if auth and parsed.get("ok") is False:
            raise RuntimeError(f"Slack API error: {parsed.get('error', parsed)}")
        return parsed
