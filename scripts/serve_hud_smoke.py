"""Seed a fixture store and serve the HUD (Playwright / maintainer smoke)."""

from __future__ import annotations

import argparse
from pathlib import Path

from questline.core.events import EventBus
from questline.hud.fixtures import seed_fixture_store
from questline.hud.server import serve


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
    args = parser.parse_args()
    args.db.parent.mkdir(parents=True, exist_ok=True)
    if args.db.exists():
        args.db.unlink()
    store = seed_fixture_store(args.db)
    bus = EventBus()
    store.attach(bus)
    print(f"seeded HUD store at {args.db}")
    serve(store=store, bus=bus, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
