# Phase briefs

Immutable briefs live as `phase-NN-*.md` (see `docs/00-MASTER-PLAN.md` §6: briefs do not
change after merge; scope changes get a revision commit with reasoning).

## Every phase session — living checklist

Before coding: read `docs/STATUS-DUAL.md` (cross-project semáforo) and the phase brief.

Before opening / updating the PR:

1. Brief acceptance checklist + **Self-review** section.
2. Out-of-scope → `BACKLOG.md`.
3. **Update `docs/STATUS-DUAL.md`** if done/next/blocked changed.
4. Game-related needs → `docs/GAME-INTEGRATION.md` (do not invent game commits).

Paste into session prompts if helpful:

```
Also update docs/STATUS-DUAL.md (semáforo + roadmap rows + date) in this PR if status changed.
```
