# ADR-0005: QuestlineWire — first-party live driver (no AltTester Desktop)

- **Status:** accepted (phase-05b Gate B)
- **Context:** AltTester Community/Desktop is unusable for this duo’s €0 live path
  (Desktop 2.3.x needs license/account; Desktop 2.0.1 does not speak Unity SDK 2.3.2 /
  Python 2.3.3). Architecture already isolates transport behind `DriverPort` +
  `DriverHandle`. The companion already owns the game API (`QuestlineHooks` /
  hooks manifest / `call_game_method`). Live Editor + Android smoke must not depend on
  a third-party hub. Reference-game evidence: ElJuegaso
  `integracion-questline.md` §8 (2026-08-08).
- **Decision:**
  1. **Ship QuestlineWire** as the happy-path live driver: a thin in-process listener in
     `com.questline.companion` plus a Python `QuestlineDriver` (`driver = "questline"`)
     implementing `DriverPort`. Exportable to any Unity project via companion + profile
     config (host/port/adb) — no ElJuegaso-only hacks.
  2. **Prefer Wire for live hooks; Poco for UI hierarchy.** Poco (phase-14) is the planned
     **primary UI** adapter (find/hierarchy/tap). Wire does not grow full UI parity.
  3. **AltTester Desktop is out of the happy path.** Keep `AltTesterDriver` + `[alttester]`
     as **legacy remoto** only. Do not rip game UPM overnight; do not recommend Desktop.
  4. **Transport:** TCP + **NDJSON** (one UTF-8 JSON object per line, `\n`-terminated).
     Unity side uses `System.Net.Sockets` under `#if UNITY_EDITOR || QUESTLINE_DEV` —
     zero third-party deps. WebSocket was rejected for MVP (needs a package or custom
     framing with little gain over line-delimited JSON for request/response).
  5. **Default port: 13000** (existing profiles + `adb reverse`). Wire and an AltTester
     Prefab **must not both bind** the same port; games enable one listener for a given
     profile. Profile keys stay `target_host` / `target_port` / `reverse_port`.
  6. **Security:** listener compiles **only** under `UNITY_EDITOR || QUESTLINE_DEV`.
     Never ship in release/playtest store builds. MVP binds loopback; Android reaches it
     via `adb reverse`. No auth/crypto in MVP (dev-only surface). Document that opening
     the port on non-loopback is out of scope and forbidden for release tooling.
  7. **Protocol sketch (v1):**
     - Client → server request:
       `{"v":1,"id":"<string>","op":"<op>","params":{…}}`
     - Server → client response:
       `{"v":1,"id":"<string>","ok":true,"result":{…}}` or
       `{"v":1,"id":"<string>","ok":false,"error":{"code":"<code>","message":"…"}}`
     - Ops (MVP): `hello` (returns `protocol_version`, `companion_version`, optional
       scene), `ping`, `app_state`, `hooks_manifest`, `call_hook`
       (`name`, `args` JSON array — same semantics as `QuestlineHooks.InvokeHook`).
     - Soft-reload: if the hook (or cached manifest entry) has `causesSoftReload`, the
       Python driver disconnects, waits a configurable delay, and reconnects
       (`DriverHandle` / no frozen refs) — same story as ADR-0004 / AltTesterDriver.
     - Listener host: `DontDestroyOnLoad` (or equivalent) so soft scene reloads do not
       silently kill the TCP accept loop; games call a companion bootstrap
       `EnsureStarted()` under the same define gate as hook registration.
  8. **Error mapping → existing taxonomy:**
     | Wire / transport condition | Questline error | Verdict |
     |---|---|---|
     | Connect refused / timeout / socket closed mid-op | `SessionLostError` / `InfraError` | infra |
     | Unknown / malformed `op` or bad JSON from **client** | `AuthoringError` | authoring |
     | Unknown hook name / bad arg types | `AuthoringError` | authoring |
     | Hook handler throws in game | `TestError` (message from server) | test |
     | UI methods not in MVP (`find` / `tap` / …) | `NotImplementedError` wrapped or documented stub raising `AuthoringError` with “Wire MVP: use hooks / see phase-14 Poco” | authoring |
  9. **MVP scope lock:** connect / disconnect / `is_alive` / `app_state` /
     `hooks_manifest` / `call_game_method` (+ soft-reload re-handshake). **Out:** full
     hierarchy/find/tap/screenshot parity; Poco; Appium; removing AltTester from examples
     overnight.
- **Consequences:** Editor live smoke is green via Wire. Game `automation/` exit is
  unblocked. Android Wire live needs Dev APK rebuild. UI hierarchy → **Poco** (14), not
  Wire v2 and not AltTester. ADR-0004 remains the hook contract; Wire is the happy-path
  *transport*. Update `STATUS-DUAL.md` when status changes.
