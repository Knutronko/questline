# Questline — Developer Quick Reference

Personal reference guide for setting up, running, and developing Questline.

---

## 1. Prerequisites

| Tool | Version | How to install |
|------|---------|----------------|
| **Git** | any recent | Already installed (Git for Windows) |
| **GitHub CLI** | any recent | Already installed (`gh`) |
| **uv** | 0.12+ | `irm https://astral.sh/uv/install.ps1 \| iex` |
| **Python** | 3.13 (managed by uv) | `uv python install 3.13` |
| **Cursor** | latest | Already installed (IDE) |

> You do NOT need to install Python manually. uv downloads and manages Python for you.

---

## 2. First-time setup (from scratch)

```powershell
# Clone the repo
cd D:\dev
gh repo clone Knutronko/questline
cd questline

# Create virtual environment + install deps
uv venv
uv pip install -e ".[dev]"
```

---

## 3. Daily workflow

```powershell
# Open the project
cd D:\dev\questline

# Activate venv (optional — uv run does it automatically)
.venv\Scripts\activate

# Or just prefix commands with uv run
uv run pytest
```

---

## 4. Essential commands

### Testing
```powershell
uv run pytest              # Run all tests
uv run pytest -v           # Verbose output
uv run pytest -x           # Stop on first failure
uv run pytest -k "smoke"   # Run tests matching pattern
uv run pytest --tb=short   # Short tracebacks
```

### Linting & formatting
```powershell
uv run ruff check src/ tests/       # Lint (find issues)
uv run ruff check --fix src/ tests/ # Lint + auto-fix
uv run ruff format src/ tests/      # Format code
```

### Dependencies
```powershell
uv pip install <package>             # Add a package to the venv
uv pip install -e ".[dev]"           # Reinstall project + dev deps
uv lock                              # Regenerate uv.lock
uv pip list                          # Show installed packages
```

### Git
```powershell
git status                           # What changed?
git add -A                           # Stage everything
git commit -m "feat: description"    # Commit
git push                             # Push to GitHub
git log --oneline -10                # Last 10 commits
```

### GitHub CLI
```powershell
gh pr create --fill                  # Create PR from current branch
gh pr list                           # List open PRs
gh run list                          # List CI runs
gh run view <id>                     # See CI run details
gh run watch                         # Watch latest CI run live
```

---

## 5. Project structure

```
D:\dev\questline/
├── .github/workflows/ci.yml   # GitHub Actions CI
├── docs/                      # Project documentation (16 phases + 4 core docs)
│   ├── 00-MASTER-PLAN.md
│   ├── 01-ARCHITECTURE.md
│   ├── 02-AI-ROADMAP.md
│   ├── 03-FUTURE-PHASES.md
│   └── phases/                # One brief per phase (00–15)
├── src/questline/             # Main package source
├── tests/                     # Test suite
├── pyproject.toml             # Project metadata, deps, tool config
├── uv.lock                    # Reproducible dependency lock
└── DEV-GUIDE.md               # This file
```

---

## 6. Verification checklist

Run these commands to verify everything is working:

```powershell
# 1. Check uv is installed
uv --version

# 2. Check Python is available
uv run python --version

# 3. Check the package is installed
uv run python -c "import questline; print(questline.__version__)"

# 4. Run tests
uv run pytest -v

# 5. Run linter
uv run ruff check src/ tests/

# 6. Check git remote
git -C D:\dev\questline remote -v

# 7. Check CI status on GitHub
gh run list --repo Knutronko/questline
```

---

## 7. Troubleshooting

**uv not found after install:**
```powershell
$env:Path = "C:\Users\Pablo\.local\bin;$env:Path"
```
To make permanent, add `C:\Users\Pablo\.local\bin` to your system PATH via Windows settings.

**Permission errors moving/deleting `.git`:**
Close any app that might lock files (VS Code, Cursor, Explorer) and retry.

**`&&` not working in PowerShell:**
Use `;` instead. Your PowerShell version doesn't support `&&`.
