"""Versioned prompt files + cache-friendly composition."""

from __future__ import annotations

from importlib.resources import files

from questline.core.errors import AuthoringError


def load_prompt(name: str, version: str) -> str:
    """Load ``{name}.{version}.md`` from the packaged prompt store."""
    filename = f"{name}.{version}.md"
    try:
        return files("questline.ai.prompts").joinpath(filename).read_text(encoding="utf-8")
    except (FileNotFoundError, ModuleNotFoundError, OSError) as exc:
        raise AuthoringError(
            f"Unknown prompt {name!r} version {version!r} (looked for {filename})."
        ) from exc


def compose_stable_prefix(*parts: str) -> str:
    """Join parts with the stable prefix first (system / static instructions).

    Provider-side prompt caches hash a prefix; keep invariant text at the front
    and put per-call measured JSON / diffs last.
    """
    chunks = [p.strip() for p in parts if p and p.strip()]
    return "\n\n".join(chunks)
