"""Allow-list rendering tests — poisoned paths/env must never leak."""

from __future__ import annotations

from questline.reporters.allowlist import (
    ALLOWED_EXPORT_FIELDS,
    allowlisted_context,
    render_template,
)


def test_poisoned_path_and_env_never_appear_in_rendered_message() -> None:
    template = (
        "run={{run_id}} status={{status}} "
        "artifact={{artifact_path}} home={{HOME}} secret={{api_key}} "
        "msg={{error_message}}"
    )
    poisoned = {
        "run_id": "r-1",
        "status": "failed",
        "error_message": "assertion failed",
        "artifact_path": r"D:\secrets\token.dump",
        "HOME": r"C:\Users\secret",
        "api_key": "sk-live-should-never-leak",
        "QUESTLINE_GITHUB_TOKEN": "ghp_should_never_leak",
        "raw_env": "PATH=/evil/bin",
    }
    rendered = render_template(template, poisoned)
    assert "r-1" in rendered
    assert "failed" in rendered
    assert "assertion failed" in rendered
    assert r"D:\secrets\token.dump" not in rendered
    assert r"C:\Users\secret" not in rendered
    assert "sk-live-should-never-leak" not in rendered
    assert "ghp_should_never_leak" not in rendered
    assert "/evil/bin" not in rendered
    # Non-allow-listed placeholders become empty, not the raw key name from context.
    assert "artifact=" in rendered
    assert rendered.count("artifact=") == 1


def test_allowlisted_context_drops_unknown_keys() -> None:
    ctx = allowlisted_context(
        {
            "nodeid": "tests/test_x.py::test_a",
            "artifact_path": "/tmp/pwned.png",
            "verdict": "test",
        }
    )
    assert ctx == {
        "nodeid": "tests/test_x.py::test_a",
        "verdict": "test",
    }
    assert "artifact_path" not in ALLOWED_EXPORT_FIELDS
