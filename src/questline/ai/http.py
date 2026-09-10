"""Shared HTTP transport for LLM adapters (stdlib urllib + fake for CI)."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from questline.ai.errors import RateLimitedError
from questline.core.errors import ProviderError

# Groq (and other CDNs) return Cloudflare 1010 if urllib's default
# ``Python-urllib/3.x`` User-Agent is sent. Match the GitHub reporter.
_DEFAULT_USER_AGENT = "questline"


@dataclass(frozen=True, slots=True)
class HttpResponse:
    status: int
    text: str
    headers: dict[str, str] = field(default_factory=dict)

    def json(self) -> dict[str, Any]:
        try:
            data = json.loads(self.text) if self.text else {}
        except json.JSONDecodeError as exc:
            raise ProviderError(f"provider returned non-JSON (status {self.status})") from exc
        if not isinstance(data, dict):
            raise ProviderError(f"provider JSON root must be an object, got {type(data).__name__}")
        return data


@runtime_checkable
class HttpTransport(Protocol):
    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
        body: bytes | None,
        timeout_s: float,
    ) -> HttpResponse: ...


def _header_map(headers: Any) -> dict[str, str]:
    if headers is None:
        return {}
    try:
        return {str(k).lower(): str(v) for k, v in headers.items()}
    except AttributeError:
        return {}


class UrllibHttpTransport:
    """Real HTTP via urllib. Used by live adapters; tests inject FakeHttpTransport."""

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
        body: bytes | None,
        timeout_s: float,
    ) -> HttpResponse:
        merged = dict(headers)
        if not any(k.lower() == "user-agent" for k in merged):
            merged["User-Agent"] = _DEFAULT_USER_AGENT
        req = urllib.request.Request(url, data=body, headers=merged, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout_s) as resp:
                raw = resp.read()
                text = raw.decode("utf-8", errors="replace")
                return HttpResponse(
                    status=int(getattr(resp, "status", 200)),
                    text=text,
                    headers=_header_map(getattr(resp, "headers", None)),
                )
        except urllib.error.HTTPError as exc:
            raw = exc.read() if exc.fp is not None else b""
            text = raw.decode("utf-8", errors="replace")
            status = int(exc.code)
            hdrs = _header_map(exc.headers)
            if status == 429:
                retry = _retry_after(hdrs)
                raise RateLimitedError(
                    f"HTTP 429 from {url}",
                    retry_after_s=retry,
                ) from exc
            if status >= 500:
                raise ProviderError(f"HTTP {status} from {url}: {text[:200]}") from exc
            raise ProviderError(f"HTTP {status} from {url}: {text[:200]}") from exc
        except TimeoutError as exc:
            raise ProviderError(f"timeout calling {url}") from exc
        except urllib.error.URLError as exc:
            raise ProviderError(f"network error calling {url}: {exc.reason}") from exc


def _retry_after(headers: dict[str, str]) -> float | None:
    raw = headers.get("retry-after")
    if raw is None:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


@dataclass
class FakeHttpTransport:
    """Scripted HTTP for CI. No network."""

    queue: list[HttpResponse | BaseException] = field(default_factory=list)
    requests: list[dict[str, Any]] = field(default_factory=list)

    def enqueue_json(
        self,
        status: int,
        body: dict[str, Any],
        *,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.queue.append(
            HttpResponse(
                status=status,
                text=json.dumps(body),
                headers={k.lower(): v for k, v in (headers or {}).items()},
            )
        )

    def enqueue_error(self, exc: BaseException) -> None:
        self.queue.append(exc)

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
        body: bytes | None,
        timeout_s: float,
    ) -> HttpResponse:
        self.requests.append(
            {
                "method": method,
                "url": url,
                "headers": dict(headers),
                "body": body,
                "timeout_s": timeout_s,
            }
        )
        if not self.queue:
            raise ProviderError("fake HTTP queue empty")
        item = self.queue.pop(0)
        if isinstance(item, BaseException):
            raise item
        if item.status == 429:
            retry = _retry_after(item.headers)
            raise RateLimitedError(f"HTTP 429 from {url}", retry_after_s=retry)
        if item.status >= 500:
            raise ProviderError(f"HTTP {item.status} from {url}: {item.text[:200]}")
        if item.status >= 400:
            raise ProviderError(f"HTTP {item.status} from {url}: {item.text[:200]}")
        return item
