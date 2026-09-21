"""Poll QuestlineWire ``hello`` on the Editor host. No adb, no AltTester."""

from __future__ import annotations

import json
import socket
import time
from collections.abc import Callable

from questline.core.errors import InfraError
from questline.drivers.wire.protocol import make_request

Connect = Callable[..., socket.socket]


def wait_for_editor_wire(
    *,
    host: str,
    port: int,
    timeout_s: float,
    interval_s: float = 0.5,
    connect: Connect | None = None,
) -> None:
    """Block until Wire answers ``hello`` with ``ok: true``, or raise InfraError."""
    opener = connect or socket.create_connection
    deadline = time.monotonic() + max(timeout_s, 0.1)
    last_err = "not attempted"
    hello = (make_request("hello", {}, req_id="ensure-editor") + "\n").encode("utf-8")
    while time.monotonic() < deadline:
        try:
            with opener((host, port), timeout=1.5) as sock:
                sock.settimeout(2.0)
                sock.sendall(hello)
                buf = b""
                while b"\n" not in buf:
                    chunk = sock.recv(4096)
                    if not chunk:
                        raise OSError("peer closed before hello reply")
                    buf += chunk
                line = buf.split(b"\n", 1)[0].decode("utf-8")
                msg = json.loads(line)
                if isinstance(msg, dict) and msg.get("ok") is True:
                    return
                last_err = "hello not ok"
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError, TimeoutError):
            last_err = "hello failed"
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        time.sleep(min(interval_s, remaining))
    raise InfraError(
        f"QuestlineWire did not answer hello on {host}:{port} "
        f"within {timeout_s:.0f}s ({last_err}). Press Play in the Editor "
        f"so the companion binds Wire. See docs/wire-setup.md."
    )
