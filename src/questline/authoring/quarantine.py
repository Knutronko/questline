"""Quarantine ledger (YAML) — versioned, audited against markers (architecture §4)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from questline.core.errors import AuthoringError

LEDGER_VERSION = 1
QUARANTINED_MARKER = "quest_quarantined"


@dataclass(slots=True)
class QuarantineEntry:
    """One quarantined test in the versioned ledger."""

    test_id: str
    reason: str
    date: str
    owner: str
    exit_criteria: str
    issue: str | None = None
    feature: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        return {k: v for k, v in data.items() if v is not None}


@dataclass(slots=True)
class AuditReport:
    """Result of comparing ledger entries vs ``quest_quarantined`` markers."""

    ledger_only: list[str]
    marker_only: list[str]

    @property
    def ok(self) -> bool:
        return not self.ledger_only and not self.marker_only

    def summary(self) -> str:
        lines: list[str] = []
        if self.ledger_only:
            lines.append("Ledger entries without quest_quarantined marker:")
            lines.extend(f"  - {t}" for t in self.ledger_only)
        if self.marker_only:
            lines.append("quest_quarantined markers without ledger entry:")
            lines.extend(f"  - {t}" for t in self.marker_only)
        if not lines:
            return "quarantine audit: ok (marker <-> ledger in sync)"
        return "quarantine audit: LIMBO\n" + "\n".join(lines)


class QuarantineLedger:
    """Load/save ``quarantine.yaml`` and keep marker↔ledger sync auditable."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.version = LEDGER_VERSION
        self._entries: dict[str, QuarantineEntry] = {}

    @classmethod
    def load(cls, path: Path) -> QuarantineLedger:
        ledger = cls(path)
        if not path.is_file():
            return ledger
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise AuthoringError(f"Invalid YAML in quarantine ledger {path}: {exc}") from exc
        if raw is None:
            return ledger
        if not isinstance(raw, dict):
            raise AuthoringError(
                f"Quarantine ledger {path} must be a mapping with 'version' and 'entries'."
            )
        version = raw.get("version", LEDGER_VERSION)
        if int(version) != LEDGER_VERSION:
            raise AuthoringError(
                f"Unsupported quarantine ledger version {version} in {path} "
                f"(expected {LEDGER_VERSION})."
            )
        ledger.version = int(version)
        entries = raw.get("entries") or []
        if not isinstance(entries, list):
            raise AuthoringError(f"'entries' in {path} must be a list.")
        for item in entries:
            entry = _parse_entry(item, path)
            ledger._entries[entry.test_id] = entry
        return ledger

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": self.version,
            "entries": [
                e.to_dict() for e in sorted(self._entries.values(), key=lambda e: e.test_id)
            ],
        }
        self.path.write_text(
            yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )

    def entries(self) -> list[QuarantineEntry]:
        return sorted(self._entries.values(), key=lambda e: e.test_id)

    def get(self, test_id: str) -> QuarantineEntry | None:
        return self._entries.get(test_id)

    def contains(self, test_id: str) -> bool:
        return test_id in self._entries

    def test_ids(self) -> set[str]:
        return set(self._entries)

    def add(
        self,
        test_id: str,
        *,
        reason: str,
        owner: str,
        exit_criteria: str,
        issue: str | None = None,
        feature: str | None = None,
        when: str | None = None,
    ) -> QuarantineEntry:
        if not test_id:
            raise AuthoringError("quarantine add requires a test_id (pytest nodeid)")
        if not reason:
            raise AuthoringError("quarantine add requires --reason")
        if not owner:
            raise AuthoringError("quarantine add requires --owner")
        if not exit_criteria:
            raise AuthoringError("quarantine add requires --exit-criteria")
        entry = QuarantineEntry(
            test_id=test_id,
            reason=reason,
            date=when or date.today().isoformat(),
            owner=owner,
            exit_criteria=exit_criteria,
            issue=issue,
            feature=feature,
        )
        self._entries[test_id] = entry
        return entry

    def remove(self, test_id: str) -> bool:
        if test_id not in self._entries:
            return False
        del self._entries[test_id]
        return True

    def audit(self, marked_nodeids: set[str]) -> AuditReport:
        ledger_ids = self.test_ids()
        return AuditReport(
            ledger_only=sorted(ledger_ids - marked_nodeids),
            marker_only=sorted(marked_nodeids - ledger_ids),
        )


def _parse_entry(item: Any, path: Path) -> QuarantineEntry:
    if not isinstance(item, dict):
        raise AuthoringError(f"Each quarantine entry in {path} must be a mapping.")
    required = ("test_id", "reason", "date", "owner", "exit_criteria")
    missing = [k for k in required if not item.get(k)]
    if missing:
        raise AuthoringError(
            f"Quarantine entry in {path} missing required fields: {', '.join(missing)}"
        )
    return QuarantineEntry(
        test_id=str(item["test_id"]),
        reason=str(item["reason"]),
        date=str(item["date"]),
        owner=str(item["owner"]),
        exit_criteria=str(item["exit_criteria"]),
        issue=str(item["issue"]) if item.get("issue") else None,
        feature=str(item["feature"]) if item.get("feature") else None,
    )


def collect_quarantined_nodeids(
    testpaths: list[str] | None = None,
    *,
    rootdir: Path | None = None,
) -> set[str]:
    """Collect pytest nodeids that carry the ``quest_quarantined`` marker.

    Always passes ``--include-quarantined`` so the plugin does not deselect them
    before markers are inspected.
    """
    import pytest

    nodeids: set[str] = set()

    class _MarkerCollector:
        def pytest_collection_modifyitems(
            self,
            config: pytest.Config,
            items: list[pytest.Item],
        ) -> None:
            _ = config
            for item in items:
                if item.get_closest_marker(QUARANTINED_MARKER) is not None:
                    nodeids.add(item.nodeid)

    args = ["--collect-only", "-q", "--include-quarantined", "-o", "addopts="]
    if rootdir is not None:
        args.extend(["--rootdir", str(rootdir)])
    if testpaths:
        args.extend(testpaths)

    code = pytest.main(args, plugins=[_MarkerCollector()])
    # ExitCode.OK=0, NO_TESTS_COLLECTED=5
    if int(code) not in (0, 5):
        raise AuthoringError(
            f"Failed to collect tests for quarantine audit (pytest exit {code})."
        )
    return nodeids
