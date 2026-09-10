# Phase briefs

Immutable briefs live as `phase-NN-*.md` (see `docs/00-MASTER-PLAN.md` §6: briefs do not
change after merge; scope changes get a revision commit with reasoning).

Inserted bridge phases use a letter suffix (e.g. `phase-05b-questline-wire.md`,
`phase-09b-wire-v2.md`, `phase-09c-wire-play-gestures.md`) so 06–15 stay stable.
Scheduled catalog FPs may use `phase-fp-*.md` (e.g. FP-G1) until numbered.

**Balance automation / GameLens order:** [`BALANCE-AUTOMATION.md`](../BALANCE-AUTOMATION.md).
**Joint D11/QL-5/FP-G1 prompts:** [`SESSION-PROMPTS-D11-QL5-FPG1.md`](SESSION-PROMPTS-D11-QL5-FPG1.md).
**QL-6 / FP-G3 prompts:** [`SESSION-PROMPTS-QL6-FPG3.md`](SESSION-PROMPTS-QL6-FPG3.md).
**G1 implications live report (after phase-11):** [`SESSION-PROMPTS-G1-IMPLICATIONS.md`](SESSION-PROMPTS-G1-IMPLICATIONS.md) · brief [`phase-fp-g1-implications-live.md`](phase-fp-g1-implications-live.md) — **merged**.
**Next:** [`SESSION-PROMPTS-G4-BALANCE-AGENT.md`](SESSION-PROMPTS-G4-BALANCE-AGENT.md) · brief [`phase-fp-g4-balance-agent.md`](phase-fp-g4-balance-agent.md).
**Parked:** [`phase-12-ai-agents.md`](phase-12-ai-agents.md) (after G4). **Folded:** [`phase-12b-hud-gamelens.md`](phase-12b-hud-gamelens.md) → G4.


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
6. **HUD:** operator workflows ship in `questline hud` in **this** PR (API + SPA +
   `docs/hud.md` + Playwright). PowerShell is extra. Defer UI only if Pablo locks it
   in the brief / BACKLOG. Self-review: `Verified in HUD: …`.

Paste into session prompts if helpful:

```
Also update docs/STATUS-DUAL.md (semáforo + roadmap rows + date) in this PR if status changed.
If this phase adds operator workflows, ship them in questline hud (API + SPA +
docs/hud.md + Playwright) in the same PR. PowerShell is extra. Defer HUD only if
Pablo says so in the brief. Self-review: Verified in HUD: …
If you hit a maintainer-visible live/CI trap or mid-PR bug, file docs/incidents/INC-NNNN-*.md,
index it in docs/INCIDENTS.md, link from the phase brief Lessons section, and cite it in
the PR Self-review (Incidents: INC-… | none).
```
