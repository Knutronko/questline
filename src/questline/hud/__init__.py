"""Questline HUD — local run viewer (phase-08)."""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path

__all__ = ["STATIC_DIR", "create_app", "static_dir"]


def static_dir() -> Path:
    """Resolved directory of embedded SPA assets (may be empty before build)."""
    # Prefer package data next to this module (editable + wheel).
    here = Path(__file__).resolve().parent / "static"
    if here.is_dir():
        return here
    try:
        root = files("questline.hud").joinpath("static")
        return Path(str(root))
    except (TypeError, FileNotFoundError, ModuleNotFoundError):
        return here


STATIC_DIR = static_dir()


def create_app(**kwargs: object):  # noqa: ANN201 — lazy import keeps [hud] optional
    from questline.hud.server import create_app as _create_app

    return _create_app(**kwargs)  # type: ignore[arg-type]
