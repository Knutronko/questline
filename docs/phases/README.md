# Phase briefs

Immutable briefs live as `phase-NN-*.md` (see `docs/00-MASTER-PLAN.md` §6: briefs do not
change after merge; scope changes get a revision commit with reasoning).

Inserted bridge phases use a letter suffix (e.g. `phase-05b-questline-wire.md`,
`phase-09b-wire-v2.md`) so 06–15 stay stable.

## Every phase session — living checklist

Before coding: read `docs/STATUS-DUAL.md` (cross-project semáforo) and the phase brief.

Before opening / updating the PR:

1. Brief acceptance checklist + **Self-review** section (include **`Incidents: INC-…` or
   `Incidents: none`** — see [`docs/INCIDENTS.md`](../INCIDENTS.md)).
2. Out-of-scope → `BACKLOG.md`.
3. Maintainer-visible live/CI traps or mid-PR bugs → file `docs/incidents/INC-NNNN-*.md`,
   index in `INCIDENTS.md`, link from this brief’s **Lessons / incidents** section.
4. **Update `docs/STATUS-DUAL.md`** if done/next/blocked changed.
5. Game-related needs → `docs/GAME-INTEGRATION.md` (do not invent game commits).
6. **HUD:** if the phase adds store/event data users should see, extend `questline hud`
   (API + SPA + `docs/hud.md` + tests) **or** explicitly defer UI in the brief (see
   [`docs/hud.md`](../hud.md) integration contract). Example: PerfProbe (09) → store now,
   graphs in HUD II (10).

Paste into session prompts if helpful:

```
Also update docs/STATUS-DUAL.md (semáforo + roadmap rows + date) in this PR if status changed.
If this phase adds store/event data users should see, extend questline hud (API + SPA +
docs/hud.md + tests) or explicitly defer UI to a later phase in the brief / BACKLOG.
If you hit a maintainer-visible live/CI trap or mid-PR bug, file docs/incidents/INC-NNNN-*.md,
index it in docs/INCIDENTS.md, link from the phase brief Lessons section, and cite it in
the PR Self-review (Incidents: INC-… | none).
```
