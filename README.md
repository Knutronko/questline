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

## License

MIT
