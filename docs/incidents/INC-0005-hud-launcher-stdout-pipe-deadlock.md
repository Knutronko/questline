# INC-0005: HUD launcher hung on unread stdout PIPE (409 forever)

- **Date:** 2026-08-11
- **Phases / triggers:** 10 (HUD Launch → Wire Editor / any managed pytest)
- **Status:** fixed
- **Symptom:** After one Launch, later Launch shows
  `409 … a run is already running (job …); stop it before launching another`
  and does not navigate to Live. Status stays `running` with a live PID that
  makes no progress (CPU ~0). Stop eventually frees the slot.
- **Root cause:** `RunLauncher` spawned pytest with `stdout=PIPE` /
  `stderr=STDOUT` but never read the pipe. On Windows the OS pipe buffer fills;
  pytest blocks on write; the waiter thread never sees exit → HUD thinks a run
  is still active. Live never got useful progress because the session was wedged
  before / during suite output.
- **Fix:** Spawn with `stdout=stderr=DEVNULL` (events still reach HUD via
  `QUESTLINE_HUD_FORWARD_URL`). Launch UI: busy banner + Open Live; on 409
  “already …” navigate to `#/live`; enable/disable Launch/Stop from status poll.
- **Prevention:**
  - Never `PIPE` a HUD-managed subprocess without a dedicated drain thread.
  - Dogfood: if Launch 409s, open Live or Stop once; if PID is idle forever,
    suspect pipe/IO hang and check launcher spawn kwargs.
  - Keep a regression assert that spawn uses `DEVNULL` in `test_hud_control`.
- **See also:** INC-0004 (wrong HUD process), [`hud-operator-guide.md`](../hud-operator-guide.md)
