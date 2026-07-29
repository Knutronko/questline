# Phase 00 — Repository bootstrap

> **How to use this brief (applies to every phase):** You are an AI coding session building
> **Questline**, an open-source AI-native game test automation framework (Python + pytest).
> Work ONLY within this brief's scope. Read `docs/00-MASTER-PLAN.md` and
> `docs/01-ARCHITECTURE.md` before writing code (in this phase, you create them from the
> provided sources). Anything out of scope goes to `docs/phases/BACKLOG.md`.
>
> **Mandatory self-review before finishing:** audit your own implementation — future
> failure modes, inconsistencies with the architecture and design rules, unhandled edge
> cases, weak tests. Write a **Self-review** section in the PR description: findings
> (fixed vs accepted-risk) + improvement proposals (add them to BACKLOG.md). A PR without
> this section is incomplete.
>
> End state: a branch pushed with all acceptance criteria met, CI green, PR description =
> brief checklist + self-review. You do NOT merge. **Expect a revision round:** the
> maintainer will test the branch hands-on and request changes; apply them on the same
> branch until approved.

## Context
Empty repository `questline` (public, MIT). This phase creates the skeleton every later
phase builds on. The maintainer will provide the three planning docs to commit.

## Objective
A clean, CI-gated Python monorepo scaffold where `pip install -e .` works and an empty
test suite passes in GitHub Actions.

## In scope
1. `pyproject.toml` — package `questline`, Python ≥3.12, `src/` layout; deps: none yet
   (dev deps: pytest, ruff, mypy, pytest-cov). Extras declared but empty:
   `[alttester,poco,appium,slack,notion,ai,hud]`.
2. Directory skeleton per `docs/01-ARCHITECTURE.md §1` (packages with `__init__.py` and
   module docstrings only).
3. Tooling: ruff (lint+format), mypy (strict), pre-commit config, `.editorconfig`,
   `.gitignore` (Python + Unity + `.questline/` runtime dirs).
4. CI: `.github/workflows/ci.yml` — on PR: ruff, mypy, pytest (with one placeholder test).
   Branch protection notes documented in CONTRIBUTING.
5. Docs: commit `00-MASTER-PLAN.md`, `01-ARCHITECTURE.md`, `02-AI-ROADMAP.md`,
   `03-FUTURE-PHASES.md` under `docs/`;
   `README.md` (what Questline is, status badge, phase table); `CONTRIBUTING.md` including:
   - the **phase workflow** (brief → session → self-review → PR → maintainer revision
     round on the branch → maintainer merges),
   - the **self-review requirement** (every PR carries a Self-review section: findings +
     proposals),
   - the **design rules** (copy of master plan §3),
   - the **clean-room rule**: this project is written from scratch; no code, identifiers or
     internal names from any proprietary codebase may be introduced.
6. `docs/phases/BACKLOG.md` (empty, with format header) and `docs/adr/` with ADR-0001
   (stack: Python+pytest, monorepo, MIT — short).
7. LICENSE (MIT).

## Out of scope
Any functional code (config, events, drivers…). No dependencies beyond dev tooling.

## Acceptance criteria
- [ ] `pip install -e ".[dev]"` succeeds on Windows (primary dev OS) and Linux (CI).
- [ ] `pytest` collects and passes the placeholder test.
- [ ] `ruff check .` and `mypy src/` pass.
- [ ] CI runs and is green on the PR.
- [ ] README, CONTRIBUTING, LICENSE, docs and ADR-0001 present and coherent.

## PR checklist
- Title `phase-00: repository bootstrap`; description lists deliverables vs this brief;
  no TODOs without a BACKLOG entry.
