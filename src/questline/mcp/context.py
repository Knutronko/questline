"""Runtime context for MCP tools (store + flags)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from questline.core.config import load_settings
from questline.core.store import RunStore


@dataclass
class McpContext:
    """One stdio session. Default is read-only (no agent invocations)."""

    store: RunStore
    settings: Any
    project_root: Path
    allow_write: bool = False
    allow_fix: bool = False
    llm_provider: Any | None = None
    locators_path: Path | None = None

    def locators_file(self) -> Path:
        return Path(self.locators_path) if self.locators_path else (
            self.project_root / "locators.yaml"
        )


def open_context(
    *,
    config: Path | None = None,
    profile: str | None = None,
    store_db: Path | None = None,
    project_root: Path | None = None,
    allow_write: bool = False,
    allow_fix: bool = False,
    llm_provider: Any | None = None,
) -> McpContext:
    """Resolve settings + store the same way CLI/HUD do."""
    root = project_root.resolve() if project_root is not None else None
    settings = load_settings(config_path=config, profile=profile, project_root=root)
    db_path = Path(store_db) if store_db is not None else settings.store_db
    artifacts = (
        settings.artifacts_dir if store_db is None else (db_path.parent / "artifacts")
    )
    store = RunStore(
        db_path,
        artifacts_dir=artifacts,
        ledger_path=settings.ledger_path,
    )
    return McpContext(
        store=store,
        settings=settings,
        project_root=Path(settings.project_root).resolve(),
        allow_write=bool(allow_write or allow_fix),
        allow_fix=bool(allow_fix),
        llm_provider=llm_provider,
    )
