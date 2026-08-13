# Phase briefs

Immutable briefs live as `phase-NN-*.md` (see `docs/00-MASTER-PLAN.md` §6: briefs do not
change after merge; scope changes get a revision commit with reasoning).

Inserted bridge phases use a letter suffix (e.g. `phase-05b-questline-wire.md`,
`phase-09b-wire-v2.md`, `phase-09c-wire-play-gestures.md`) so 06–15 stay stable.
Scheduled catalog FPs may use `phase-fp-*.md` (e.g. FP-G1) until numbered.

**Balance automation / GameLens order:** [`BALANCE-AUTOMATION.md`](../BALANCE-AUTOMATION.md).
**Joint D11/QL-5/FP-G1 prompts:** [`SESSION-PROMPTS-D11-QL5-FPG1.md`](SESSION-PROMPTS-D11-QL5-FPG1.md).
**QL-6 / FP-G3 prompts:** [`SESSION-PROMPTS-QL6-FPG3.md`](SESSION-PROMPTS-QL6-FPG3.md).


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
6. **HUD:** if the phase adds store/event data **or operator workflows** users should see,
   extend `questline hud` (API + SPA + `docs/hud.md` + tests) **or** explicitly defer UI
   in the brief / BACKLOG (see [`docs/hud.md`](../hud.md) HUD-first verification contract).
   Prefer proving acceptance **in the HUD** when a surface exists; say
   `Verified in HUD: …` in Self-review (CLI-only only for CI/scripting gaps).

Paste into session prompts if helpful:

```
Also update docs/STATUS-DUAL.md (semáforo + roadmap rows + date) in this PR if status changed.
If this phase adds store/event data or operator workflows users should see, extend questline
hud (API + SPA + docs/hud.md + tests) or explicitly defer UI to a later phase in the brief /
BACKLOG. Prefer HUD verification in Self-review (Verified in HUD: …).
If you hit a maintainer-visible live/CI trap or mid-PR bug, file docs/incidents/INC-NNNN-*.md,
index it in docs/INCIDENTS.md, link from the phase brief Lessons section, and cite it in
the PR Self-review (Incidents: INC-… | none).
```
