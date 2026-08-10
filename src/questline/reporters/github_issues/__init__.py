"""GitHub Issues reporter package."""

from questline.reporters.github_issues.reporter import GitHubIssuesReporter
from questline.reporters.github_issues.signature import failure_signature, normalize_message
from questline.reporters.github_issues.transport import (
    FakeGitHubIssuesTransport,
    HttpGitHubIssuesTransport,
)

__all__ = [
    "FakeGitHubIssuesTransport",
    "GitHubIssuesReporter",
    "HttpGitHubIssuesTransport",
    "failure_signature",
    "normalize_message",
]
