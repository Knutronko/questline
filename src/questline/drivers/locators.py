"""Driver-agnostic locator model, YAML registry, and compile helpers."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml

from questline.core.errors import AuthoringError


class LocatorStrategy(StrEnum):
    ID = "id"
    NAME = "name"
    PATH = "path"
    TEXT = "text"
    COMPONENT = "component"


@dataclass(frozen=True, slots=True)
class Locator:
    """Abstract element query. Adapters compile this to a native query."""

    by: LocatorStrategy
    value: str
    scope: str | None = None

    def __post_init__(self) -> None:
        if isinstance(self.by, str) and not isinstance(self.by, LocatorStrategy):
            object.__setattr__(self, "by", LocatorStrategy(self.by))
        if not self.value:
            raise AuthoringError("Locator.value must be non-empty")


@dataclass(frozen=True, slots=True)
class LocatorEntry:
    """One named locator inside a page group."""

    page: str
    name: str
    locator: Locator


class LocatorRegistry:
    """Loaded locators.yaml: page → name → Locator."""

    def __init__(self, entries: dict[str, dict[str, Locator]]) -> None:
        self._entries = entries

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> LocatorRegistry:
        pages_raw = data.get("pages", data)
        if not isinstance(pages_raw, dict):
            raise AuthoringError("locators.yaml must contain a mapping of pages")

        entries: dict[str, dict[str, Locator]] = {}
        for page, locators in pages_raw.items():
            if not isinstance(locators, dict):
                raise AuthoringError(f"page '{page}' must map locator names to definitions")
            page_map: dict[str, Locator] = {}
            for name, spec in locators.items():
                page_map[name] = _parse_locator_spec(page, name, spec)
            entries[str(page)] = page_map
        return cls(entries)

    def get(self, page: str, name: str) -> Locator:
        try:
            return self._entries[page][name]
        except KeyError as exc:
            raise AuthoringError(f"unknown locator {page}.{name}") from exc

    def pages(self) -> list[str]:
        return sorted(self._entries)

    def locators_for(self, page: str) -> dict[str, Locator]:
        try:
            return dict(self._entries[page])
        except KeyError as exc:
            raise AuthoringError(f"unknown page '{page}'") from exc

    def all_entries(self) -> list[LocatorEntry]:
        out: list[LocatorEntry] = []
        for page, locs in sorted(self._entries.items()):
            for name, loc in sorted(locs.items()):
                out.append(LocatorEntry(page=page, name=name, locator=loc))
        return out


def load_locators(path: Path | str) -> LocatorRegistry:
    """Load and validate a locators.yaml file."""
    p = Path(path)
    if not p.is_file():
        raise AuthoringError(f"locators file not found: {p}")
    try:
        raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise AuthoringError(f"invalid YAML in {p}: {exc}") from exc
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise AuthoringError(f"locators root must be a mapping, got {type(raw).__name__}")
    return LocatorRegistry.from_mapping(raw)


def _parse_locator_spec(page: str, name: str, spec: Any) -> Locator:
    if not isinstance(spec, dict):
        raise AuthoringError(f"{page}.{name}: locator spec must be a mapping")
    by = spec.get("by")
    value = spec.get("value")
    if by is None or value is None:
        raise AuthoringError(f"{page}.{name}: requires 'by' and 'value'")
    try:
        strategy = LocatorStrategy(str(by))
    except ValueError as exc:
        raise AuthoringError(
            f"{page}.{name}: unknown strategy '{by}' "
            f"(expected {[s.value for s in LocatorStrategy]})"
        ) from exc
    scope = spec.get("scope")
    return Locator(by=strategy, value=str(value), scope=None if scope is None else str(scope))
