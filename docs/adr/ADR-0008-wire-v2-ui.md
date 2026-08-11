# ADR-0008: Wire v2 — Unity UI ops on QuestlineWire (before Poco)

- **Status:** accepted (implemented in **phase-09b**)
- **Context:** ADR-0005 locked Wire MVP to hooks/session and deferred find/hierarchy/tap
  to **Poco (phase-14)**. That deferral blocks €0 UI navigation for game
  `automation/` and for future **GameLens bot playthroughs (FP-G3)** until late in
  the roadmap. The maintainer ordered: **09 PerfProbe → 09b Wire v2 → D11 / FP-G1
  GameLens**, so balance playtests can use Wire UI without waiting for Poco.
  DriverPort + Locator (ADR-0003) and NDJSON framing (ADR-0005) already exist;
  Python stubs raise `AuthoringError` (“use Poco”).
- **Decision:**
  1. **Extend QuestlineWire** with a **v2 UI op set** on the same TCP+NDJSON transport
     (no second port, no Desktop). Happy-path live remains `driver = "questline"`.
  2. **Role split (amends ADR-0005 §2):**
     - **Wire** = Unity happy-path: hooks **and** lightweight hierarchy/find/tap/screenshot.
     - **Poco (14)** = second UI backend / richer or non-Unity stacks; still proves
       “easy to switch drivers”. Not required for ElJuegaso smoke once Wire v2 is green.
     - **AltTester** = legacy remoto only.
  3. **Protocol:** keep framing `{"v":1,"id","op","params"}` / ok|error responses.
     `hello.result` MUST advertise capability, e.g.
     `"protocol_version": 2` and/or `"features": ["hooks","ui"]`. Clients that only
     need hooks keep working against older companions; UI ops against a v1-only
     companion → clear `AuthoringError` (not silent stub).
  4. **Ops in scope (09b):**
     | Op | Purpose |
     |----|---------|
     | `hierarchy` | Normalized tree → `HierarchySnapshot` JSON (depth/node caps) |
     | `find` / `find_all` | Compile `Locator` (`by`/`value`/`scope`) server-side or send compiled query |
     | `tap` | `Element` id from prior find **or** screen `Point` |
     | `screenshot` | PNG bytes (base64 in JSON **or** length-prefixed binary follow-up — pick one in impl; prefer base64 for MVP simplicity) |
     Deferred to later Wire patch / Poco: `press`, `swipe`, `text_input` (may stay
     `AuthoringError` with pointer to hooks or backlog).
  5. **Locator compile:** same ADR-0003 model. Wire maps:
     `id`→instance/stable id, `name`→GameObject.name, `path`→hierarchy path,
     `text`→TMP/UGUI text, `component`→GetComponent type name. Missing under wait
     policy → `ElementNotFoundError` (verdict `test`); transport death → `SessionLostError`.
  6. **Unity implementation constraints:** `#if UNITY_EDITOR \|\| QUESTLINE_DEV` only;
     loopback bind unchanged; hierarchy must be bounded (max depth / max nodes) to avoid
     multi‑MB replies; taps prefer uGUI `ExecuteEvents` when target is a Graphic, else
     screen-point injection documented as best-effort.
  7. **Phase numbering:** **09b** (does not renumber 10–15). Game sync trigger **QL-2c**
     (companion refresh + Dev APK rebuild). Ordered **after 09 / QL-3**, **before**
     FP-G1 / QL-5 GameLens and FP-G3 bots.
  8. **Testing:** Fake transport unit tests in CI; extend `examples/wire-smoke` with a
     UI mini-scene or GO markers; maintainer live Editor (+ optional Android) AC.
- **Consequences:**
  - Update `wire-setup.md`, `drivers.md`, STATUS-DUAL, GAME-INTEGRATION, phase-14 brief.
  - ADR-0005 §2 / §9 “UI → Poco only” is **superseded** by this document for happy-path
    Unity; ADR-0005 transport/security/MVP hooks remain in force.
  - Phase-14 shrinks urgency for ElJuegaso UI smoke but remains the second-adapter proof
    + UTF ingestion.
- **Alternatives considered:** Wait for Poco-14 (rejected — too late for GameLens bots).
  Full Wire parity with AltTester including swipe/text (rejected — scope creep; 09b stays
  thin). Separate WebSocket channel (rejected — ADR-0005 NDJSON is enough).
