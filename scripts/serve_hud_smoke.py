"""Seed a fixture store and serve the HUD (Playwright / maintainer smoke)."""

from __future__ import annotations

import argparse
import threading
import time
from pathlib import Path
from typing import Any

from questline.core.events import EventBus
from questline.hud.fixtures import seed_fixture_store
from questline.hud.launcher import LaunchRequest, LaunchStatus, RunLauncher
from questline.hud.server import create_app


class _SmokeProc:
    """Immediate-finish fake process for Playwright launch/stop smoke."""

    def __init__(self) -> None:
        self.pid = 9001
        self._code: int | None = None
        self._done = threading.Event()

    def poll(self) -> int | None:
        return self._code

    def wait(self) -> int:
        # Auto-finish shortly so status moves to finished without stop.
        self._done.wait(timeout=0.3)
        if self._code is None:
            self._code = 0
        self._done.set()
        return self._code

    def send_signal(self, _sig: int) -> None:
        self._code = -15
        self._done.set()

    def kill(self) -> None:
        self._code = -9
        self._done.set()


class _SmokeLauncher(RunLauncher):
    """Broadcasts live events without writing new runs into the fixture store."""

    def __init__(self, *, bridge: Any, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._bridge = bridge

    def launch(self, req: LaunchRequest) -> LaunchStatus:
        status = super().launch(req)

        def _emit() -> None:
            time.sleep(0.05)
            rid = f"smoke-{status.job_id}"
            self._bridge.broadcast_payload(
                {
                    "type": "RunStarted",
                    "run_id": rid,
                    "profile": req.profile or "mock",
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "tags": {},
                }
            )
            self._bridge.broadcast_payload(
                {
                    "type": "TestStarted",
                    "run_id": rid,
                    "test_id": "t-smoke",
                    "nodeid": "smoke::test_launch",
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "tags": {},
                }
            )

        threading.Thread(target=_emit, daemon=True).start()
        return status


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8741)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument(
        "--db",
        type=Path,
        default=Path(".questline-hud-smoke/store.db"),
        help="Path to SQLite store (re-seeded each start)",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Optional questline.toml (defaults to a smoke file beside the db)",
    )
    args = parser.parse_args()
    args.db.parent.mkdir(parents=True, exist_ok=True)
    if args.db.exists():
        args.db.unlink()
    store = seed_fixture_store(args.db)
    bus = EventBus()
    store.attach(bus)

    root = args.db.parent.resolve()
    config = args.config or (root / "questline.toml")
    if not config.is_file():
        config.write_text(
            '[profile.mock]\ndriver = "mock"\nreporters = ["console"]\n',
            encoding="utf-8",
        )

    def spawn(*_a: Any, **_k: Any) -> _SmokeProc:
        return _SmokeProc()

    try:
        import uvicorn
    except ImportError as exc:
        raise SystemExit("pip install 'questline[hud]'") from exc

    # Build app first so we can wire the live bridge into the smoke launcher.
    app = create_app(
        store=store,
        bus=bus,
        project_root=root,
        config_path=config,
        quarantine_path=root / "quarantine.yaml",
        forward_base_url=f"http://{args.host}:{args.port}",
    )
    bridge = app.state.live
    app.state.launcher = _SmokeLauncher(
        bridge=bridge,
        project_root=root,
        config_path=config,
        forward_url=f"http://{args.host}:{args.port}/api/live/ingest",
        csrf_token="smoke",
        lock_dir=root / "device-locks",
        spawn=spawn,  # type: ignore[arg-type]
    )
    print(f"seeded HUD store at {args.db}")
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
