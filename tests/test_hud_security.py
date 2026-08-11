"""Unit tests for HUD security helpers."""

from __future__ import annotations

from questline.hud.security import is_loopback_host, new_csrf_token


def test_loopback_hosts() -> None:
    assert is_loopback_host("127.0.0.1")
    assert is_loopback_host("::1")
    assert is_loopback_host("localhost")
    assert is_loopback_host("testclient")
    assert is_loopback_host("::ffff:127.0.0.1")
    assert not is_loopback_host("8.8.8.8")
    assert not is_loopback_host("")
    assert not is_loopback_host(None)


def test_csrf_token_entropy() -> None:
    a = new_csrf_token()
    b = new_csrf_token()
    assert a != b
    assert len(a) >= 20
