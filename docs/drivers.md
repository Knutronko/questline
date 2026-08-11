# Writing a DriverPort adapter

This guide is for Phase 04+ adapters (**QuestlineWire**, Poco, AltTester legacy, Appium, …).
Phase 02 ships the port, locator model, `DriverHandle`, in-memory `MockDriver`, and the
**conformance suite** every adapter must pass.

## Checklist

1. **Implement `DriverPort`** (`questline.drivers.port`) — `connect` / `disconnect` /
   `is_alive`, `find` / `find_all`, `hierarchy`, `screenshot`, interactions
   (`tap` / `press` / `swipe` / `text_input`), `call_game_method`, `app_state`,
   `hooks_manifest`.
   **QuestlineWire:** session + hooks (05b) + UI find/hierarchy/tap/screenshot (**09b** ✅,
   ADR-0008). **Poco** (phase-14) is the second UI backend — not AltTester.
   Wire parity vs Mock: find/wait/hierarchy/screenshot/tap Element|Point; deferred
   `press`/`swipe`/`text_input` → explicit `AuthoringError` (unit-tested). Vs Poco:
   Wire is Unity happy-path; Poco proves driver switch + richer/non-Unity stacks.
2. **Implement `compile(Locator) -> native query`** — map
   `by ∈ {id,name,path,text,component}` (+ optional `scope`) to the backend’s selector
   language. Do not leak native types through `Element` / `HierarchySnapshot`.
3. **Map failures to the taxonomy** (`questline.core.errors`):
   - session/transport death → `SessionLostError` (verdict `infra`)
   - missing UI under wait policy → `ElementNotFoundError` (verdict `test`)
   - malformed author input → `AuthoringError`
4. **Honor wait budgets** — `find(..., policy, budget="probe"|"deadline")`:
   - `policy is None` → single immediate check
   - `budget="probe"` → total wait ≤ `policy.probe`
   - `budget="deadline"` → total wait ≤ `policy.deadline`  
   Never silently replace a caller’s `WaitPolicy` with defaults (`resolve_policy` /
   `with_overrides` only).
5. **Never freeze the driver** — pages/steps take a `DriverHandle` and call through it.
   After `handle.reset(new_driver)`, the old instance is disconnected/disposed.
6. **Pass conformance** — see below. MockDriver is the reference (must stay at 100%).

## Locator registry + codegen

```bash
# Author locators in YAML, then generate typed accessors (commit the output).
python -m questline.drivers.codegen path/to/locators.yaml -o path/to/generated_locators.py
```

The generated module header says **DO NOT EDIT BY HAND**. Regenerate instead of patching.

Sample files in this repo: `examples/locators.yaml` → `examples/generated_locators.py`.

See [ADR-0003](adr/ADR-0003-locator-model.md) for why adapters compile locators.

## Run the conformance suite

Against MockDriver (CI):

```bash
uv run pytest tests/test_driver_conformance.py -q
```

Against AltTesterDriver with a **fake transport** (CI, no Unity):

```bash
uv run pytest tests/test_alttester_conformance_fake.py -q
```

Against a **live** Unity session (skipped unless `QUESTLINE_LIVE_TARGET=1`):

```bash
# PowerShell — QuestlineWire (happy path; no Desktop)
$env:QUESTLINE_LIVE_TARGET = "1"
uv run pytest examples/wire-smoke -q -o addopts= `
  --questline-profile editor `
  --questline-config examples/wire-smoke/questline.toml

# Legacy AltTester (optional; requires Desktop hub — not €0 happy path)
uv run pytest tests/test_alttester_conformance_live.py -q -o addopts=
```

See [wire-setup.md](wire-setup.md) for the happy-path companion listener.
See [ADR-0008](adr/ADR-0008-wire-v2-ui.md) for Wire v2 UI ops (phase-09b).
See [unity-setup.md](unity-setup.md) for legacy AltTester only.
See [android.md](android.md) for `android_local` (`adb forward` + LocalAdbProvider for Wire).
See [ADR-0005](adr/ADR-0005-questline-wire.md) for protocol and security.


## DriverHandle (session reset)

```python
from questline.drivers import DriverHandle
from questline.drivers.mock import MockDriver

handle = DriverHandle(MockDriver())
handle.connect(target)
# … later, after recovery …
handle.reset(MockDriver())  # old driver disconnected; callers keep using `handle`
```
