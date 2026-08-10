"""GitHub Issues HTTP transport — real (stdlib) + fake for CI."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class GitHubIssuesTransport(Protocol):
    def create_issue(
        self,
        *,
        title: str,
        body: str,
        labels: list[str] | None = None,
    ) -> dict[str, Any]: ...

    def comment(self, *, issue_number: int, body: str) -> dict[str, Any]: ...

    def close_issue(self, *, issue_number: int) -> dict[str, Any]: ...

    def find_open_issues_by_marker(self, marker: str) -> list[dict[str, Any]]: ...


@dataclass
class FakeGitHubIssuesTransport:
    """In-memory GitHub Issues API for unit tests (no network)."""

    issues: list[dict[str, Any]] = field(default_factory=list)
    comments: list[dict[str, Any]] = field(default_factory=list)
    closed: list[int] = field(default_factory=list)
    _next: int = 1

    def create_issue(
        self,
        *,
        title: str,
        body: str,
        labels: list[str] | None = None,
    ) -> dict[str, Any]:
        number = self._next
        self._next += 1
        issue = {
            "number": number,
            "title": title,
            "body": body,
            "labels": [{"name": x} for x in (labels or [])],
            "state": "open",
            "html_url": f"https://example.test/issues/{number}",
        }
        self.issues.append(issue)
        return issue

    def comment(self, *, issue_number: int, body: str) -> dict[str, Any]:
        row = {"issue_number": issue_number, "body": body}
        self.comments.append(row)
        return row

    def close_issue(self, *, issue_number: int) -> dict[str, Any]:
        self.closed.append(issue_number)
        for issue in self.issues:
            if issue["number"] == issue_number:
                issue["state"] = "closed"
                return issue
        return {"number": issue_number, "state": "closed"}

    def find_open_issues_by_marker(self, marker: str) -> list[dict[str, Any]]:
        return [
            i
            for i in self.issues
            if i.get("state") == "open" and marker in (i.get("body") or "")
        ]


class HttpGitHubIssuesTransport:
    """GitHub REST via urllib. Token: ``QUESTLINE_GITHUB_TOKEN``."""

    def __init__(
        self,
        *,
        token: str,
        repo: str,
        timeout_s: float = 30.0,
        api_base: str = "https://api.github.com",
    ) -> None:
        if "/" not in repo:
            raise ValueError(f"github_repo must be 'owner/name', got {repo!r}")
        self.token = token
        self.repo = repo
        self.timeout_s = timeout_s
        self.api_base = api_base.rstrip("/")

    def create_issue(
        self,
        *,
        title: str,
        body: str,
        labels: list[str] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"title": title, "body": body}
        if labels:
            payload["labels"] = labels
        return self._request("POST", f"/repos/{self.repo}/issues", payload)

    def comment(self, *, issue_number: int, body: str) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/repos/{self.repo}/issues/{issue_number}/comments",
            {"body": body},
        )

    def close_issue(self, *, issue_number: int) -> dict[str, Any]:
        return self._request(
            "PATCH",
            f"/repos/{self.repo}/issues/{issue_number}",
            {"state": "closed"},
        )

    def find_open_issues_by_marker(self, marker: str) -> list[dict[str, Any]]:
        # Search within the repo for the signature marker in open issues.
        q = f'repo:{self.repo} is:issue is:open "{marker}"'
        path = "/search/issues?" + urllib.parse.urlencode({"q": q})
        data = self._request("GET", path)
        return list(data.get("items") or [])

    def _request(
        self, method: str, path: str, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        url = path if path.startswith("http") else f"{self.api_base}{path}"
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self.token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "questline",
        }
        if data is not None:
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                raw = resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"GitHub HTTP {exc.code}: {body}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"GitHub request failed: {exc}") from exc
        if not raw:
            return {}
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return {"items": parsed}
        return parsed
