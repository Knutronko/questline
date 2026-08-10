# QuestLine

AI-native game test automation framework (Python + pytest).

## Quick start

```bash
pip install uv
uv venv
uv pip install -e ".[dev]"
uv run pytest
```

## Live smoke (happy path — QuestlineWire)

```powershell
cd D:\dev\questline
# Unity Play: QuestlineWireServer listening on :13000
$env:QUESTLINE_LIVE_TARGET = "1"
uv run pytest examples/wire-smoke -q -o addopts= `
  --questline-profile editor `
  --questline-config examples/wire-smoke/questline.toml
```

See [`docs/wire-setup.md`](docs/wire-setup.md). AltTester Desktop is **not** required.
UI hierarchy later = **Poco** (phase-14), not AltTester.

## HUD (local run viewer)

```powershell
uv pip install -e ".[hud]"
questline hud --open
```

See [`docs/hud.md`](docs/hud.md).

## Documentation

- Index: [`docs/README.md`](docs/README.md)
- **Dual status (questline ↔ reference game):** [`docs/STATUS-DUAL.md`](docs/STATUS-DUAL.md)
- Master plan: [`docs/00-MASTER-PLAN.md`](docs/00-MASTER-PLAN.md)

## License

MIT
