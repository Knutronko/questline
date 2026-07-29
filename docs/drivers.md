# Writing a DriverPort adapter

This guide is for Phase 04+ adapters (AltTester, Poco, Appium, …). Phase 02 ships the
port, locator model, `DriverHandle`, in-memory `MockDriver`, and the **conformance suite**
every adapter must pass.

## Checklist

1. **Implement `DriverPort`** (`questline.drivers.port`) — `connect` / `disconnect` /
   `is_alive`, `find` / `find_all`, `hierarchy`, `screenshot`, interactions
   (`tap` / `press` / `swipe` / `text_input`), `call_game_method`, `app_state`.
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

For a new adapter, parametrize the same cases with your factory:

```python
from questline.drivers.conformance import CONFORMANCE_CASES

@pytest.mark.parametrize("case", CONFORMANCE_CASES, ids=lambda c: c.__name__)
def test_my_adapter_conformance(case):
    case(MyDriver)  # zero-arg factory → fresh disconnected DriverPort
```

Cases that need mock-only hooks (`schedule_appear`, `drop_after_commands`) will
`pytest.skip` on adapters that omit them — still implement forced disconnect coverage
via your own transport-kill test if those hooks are absent.

## DriverHandle (session reset)

```python
from questline.drivers import DriverHandle
from questline.drivers.mock import MockDriver

handle = DriverHandle(MockDriver())
handle.connect(target)
# … later, after recovery …
handle.reset(MockDriver())  # old driver disconnected; callers keep using `handle`
```
