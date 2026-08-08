# QuestLine

AI-native game test automation framework (Python + pytest).

## Quick start

```bash
# Install uv (if not already installed)
pip install uv

# Create venv and install dependencies
uv venv
uv pip install -e ".[dev]"

# Run tests
uv run pytest
```

## Project structure

```
questline/
├── src/questline/      # Main package
├── tests/              # Test suite
├── .github/workflows/  # CI
└── pyproject.toml      # Project config
```

## Documentation

- Index: [`docs/README.md`](docs/README.md)
- **Dual status (questline ↔ reference game):** [`docs/STATUS-DUAL.md`](docs/STATUS-DUAL.md)
- Master plan: [`docs/00-MASTER-PLAN.md`](docs/00-MASTER-PLAN.md)

## Documentation

- Index: [`docs/README.md`](docs/README.md)
- **Dual status (questline ↔ reference game):** [`docs/STATUS-DUAL.md`](docs/STATUS-DUAL.md)
- Master plan: [`docs/00-MASTER-PLAN.md`](docs/00-MASTER-PLAN.md)

## License

MIT
