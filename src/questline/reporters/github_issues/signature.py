"""Failure signature hashing for GitHub Issues dedupe."""

from __future__ import annotations

import hashlib
import re

_WHITESPACE = re.compile(r"\s+")
_HEX = re.compile(r"\b0x[0-9a-fA-F]+\b")
_NUM = re.compile(r"\b\d{4,}\b")


def normalize_message(message: str | None) -> str:
    """Collapse volatile tokens so reruns hash to the same signature."""
    if not message:
        return ""
    text = message.strip()
    text = _HEX.sub("<hex>", text)
    text = _NUM.sub("<n>", text)
    text = _WHITESPACE.sub(" ", text)
    return text.lower()


def failure_signature(
    *,
    test_id: str,
    error_type: str | None,
    error_message: str | None,
) -> str:
    """Stable hash: test_id + error class + normalized message."""
    raw = "|".join(
        [
            (test_id or "").strip(),
            (error_type or "").strip(),
            normalize_message(error_message),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
