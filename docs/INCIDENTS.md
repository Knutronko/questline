# Incidents & lessons learned

Living log of **maintainer-visible failures** (live smoke, CI flaky, sync mistakes,
env footguns) so future sessions do not repeat them.

This is **not** the feature backlog (`docs/phases/BACKLOG.md`). BACKLOG = deferred
work. INCIDENTS = mistakes / traps already hit and how we avoid them.

## When to file an incident

File an `INC-NNNN` when **any** of these is true during a phase PR / maintainer check:

1. Live Editor/Android smoke fails for a non-obvious reason (env leftover, race, stale
   companion, wrong adb mode, …).
2. A bug ships (or nearly ships) that needs a follow-up fix commit on the same phase.
3. Working-tree / sync confusion between questline ↔ game (uncommitted companion, wrong
   path, “phase closed” but files never PRed).
4. The same class of mistake appears twice — upgrade the older INC with a stronger
   “prevention” rule.

Skip tiny typos and one-line CI fixes that are obvious from the diff.

## How (AI session checklist)

1. Create `docs/incidents/INC-NNNN-short-slug.md` (next free number; English).
2. Add a row to the **Index** below.
3. Link from the **affected phase brief(s)** under `## Lessons / incidents`.
4. If it is an env / live footgun, also add a short warning to the operator guide
   (`wire-setup.md`, `performance.md`, `android.md`, …).
5. Mention the INC id in the PR **Self-review** (`Incidents: INC-0001` or `Incidents: none`).

Paste into phase prompts:

```
If this session hits a maintainer-visible live/CI trap or mid-PR bug, file
docs/incidents/INC-NNNN-*.md, index it in docs/INCIDENTS.md, link from the phase
brief Lessons section, and cite it in the PR Self-review.
```

## Index

| Id | Title | Phases | Status | Date |
|----|-------|--------|--------|------|
| [INC-0001](incidents/INC-0001-wire-perf-socket-race.md) | Wire NDJSON response steal when `QUESTLINE_PERF_ENABLED` left on | 09, 09b | fixed | 2026-08-11 |
| [INC-0002](incidents/INC-0002-companion-sync-uncommitted.md) | Game companion QL-3/QL-2c sat in WT without PR | 09, 09b, QL-3/2c | fixed | 2026-08-11 |

## Template

```markdown
# INC-NNNN: short title

- **Date:** YYYY-MM-DD
- **Phases / triggers:** e.g. 09b, QL-2c
- **Status:** open | fixed | accepted-risk
- **Symptom:** what the maintainer saw (error text / failing test)
- **Root cause:** one paragraph
- **Fix:** code / docs / process
- **Prevention:** what future sessions must do (checklist bullets)
- **See also:** links to PRs, guides, related INCs
```
