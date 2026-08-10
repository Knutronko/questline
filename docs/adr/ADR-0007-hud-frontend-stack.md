# ADR-0007: HUD frontend stack + wheel embedding

- **Status:** accepted (phase-08)
- **Context:** Phase 08 ships a local run viewer (`questline hud`). The phase brief
  checklist cited “ADR-0006” for the frontend decision, but ADR-0006 is already the
  recovery ladder — this document is **ADR-0007**. Constraints: no Node at *runtime*,
  €0 CI, localhost-first, information-dense dark HUD aesthetic, boring stack (no heavy
  SPA framework), built assets must ship inside the Python wheel so
  `pip install questline[hud]` serves the UI.
- **Decision:**
  1. **Backend:** FastAPI + uvicorn under optional extra `questline[hud]`. REST reads
     the `RunStore`; WebSocket `/api/live` bridges the in-process `EventBus` for the
     run in progress. Default bind `127.0.0.1` (`--host` opt-in).
  2. **Frontend:** Vite + vanilla TypeScript (no React/Vue). Source lives at
     `hud/frontend/`; production build emits to `src/questline/hud/static/`. Hash or
     History routing with FastAPI SPA fallback. Dark game-HUD CSS (dense tables, muted
     chrome, infra-vs-test color split matching the HTML reporter).
  3. **Wheel embedding:** hatch `force-include` of `src/questline/hud/static/**` into
     the wheel. CI builds the frontend before tests that need assets; maintainers rebuild
     with `npm ci && npm run build` under `hud/frontend/` before release. Runtime only
     needs Python + `[hud]` — never Node.
  4. **Empty store:** API returns empty lists; SPA shows a clear empty state (not an
     error).
- **Consequences:**
  - Dev machines need Node only to change the SPA; consumers of the wheel do not.
  - Built `static/` is committed (or regenerated in CI and asserted) so editable installs
    work without a manual frontend build step on every clone.
  - Control-center actions (launch/stop, quarantine UI) stay out until phase 10.
- **Alternatives considered:** React/Vue (rejected — heavier than needed for a viewer).
  Pure Jinja server-rendered pages (rejected — live WebSocket view and drill-down UX are
  clumsier). Serving from a CDN / separate process (rejected — local-first, wheel-embedded
  AC). Shipping source and compiling with Brython/pyodide (rejected — novelty, slow).
