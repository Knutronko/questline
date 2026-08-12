# INC-0003: HUD test detail 404 when pytest nodeid contains `/`

- **Date:** 2026-08-11
- **Phases / triggers:** 10 (HUD II), any live Wire/mock run whose store `test_id` is the pytest nodeid
- **Status:** fixed
- **Symptom:** Clicking a test in Run detail (e.g.
  `examples/wire-smoke/test_smoke.py::test_wire_v2_hierarchy_find_tap`) shows
  `Failed to load HUD: 404 …`. Two forms observed:
  1. `…/tests/examples` → `test not found: examples` (SPA took only the first segment).
  2. `…/tests/examples/wire-smoke/…::…` → `API route not found: …` (**stale**
     `questline hud` process still registered `{test_id}` without `:path`, while
     the rebuilt SPA already requested multi-segment paths).
- **Root cause:** Store ids are pytest **nodeids** (paths with `/`). Hash router
  and API path params must not assume a single segment. Also: **static SPA assets
  reload from disk; Python routes do not** until HUD restart — verifying only the
  source tree is not enough.
- **Fix:**
  - Hash route joins/decodes the remainder after `/tests/`; links encode the id.
  - Preferred API: `GET /api/runs/{run_id}/test?id=<nodeid>` (query param).
  - Keep `GET …/tests/{test_id:path}` as fallback.
  - `/api/meta` exposes `api.revision` / `api.test_by_query` so a stale process is detectable.
- **Prevention:**
  - After any HUD **API** change, restart `questline hud` and confirm
    `GET /api/meta` → `api.test_by_query: true` (or probe the new route on :8741).
  - Prefer query params for nodeids; never split them on `/` in the SPA.
  - Playwright / API tests must cover a nodeid containing `/`.
- **See also:** [`hud.md`](../hud.md), [`hud-operator-guide.md`](../hud-operator-guide.md),
  PR phase-10
