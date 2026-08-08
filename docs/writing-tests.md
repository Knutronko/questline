# Writing tests with Questline

Phase 03 authoring layer: pytest plugin, pages, declarative steps, fluent
assertions, and the quarantine ledger. Drivers are consumed via `DriverHandle`
(see [drivers.md](drivers.md)) — never cache a raw `DriverPort`.

## Quick start (demo suite)

Phases 00–03 dogfood against **MockDriver** only (see
[GAME-INTEGRATION.md](GAME-INTEGRATION.md) §4). Live happy path is **QuestlineWire**
(`driver = "questline"`) — see [wire-setup.md](wire-setup.md) and `examples/wire-smoke/`.
Phase 04 AltTester is **legacy remoto**; phase 14 **Poco** is UI hierarchy.
Android: [android.md](android.md). Real game suites live under game-repo `automation/`
(GAME-INTEGRATION §2–3; exit task unblocked after Editor Wire green).

```bash
# From the repo root — MockDriver fake game under examples/demo-tests/
uv run pytest examples/demo-tests \
  --questline-profile mock \
  --questline-config examples/questline.toml \
  --questline-quarantine examples/demo-tests/quarantine.yaml
```

Quarantined tests are **excluded by default**. Include them with
`--include-quarantined`. Filter by feature metadata with `--feature <id>`.

## Profiles & fixtures

Session wiring (when a test requests them):

| Fixture | Scope | Role |
|---------|-------|------|
| `questline_settings` | session | Resolved `questline.toml` profile |
| `questline_bus` | session | Event bus |
| `questline_store` | session | SQLite + JSONL ledger under `.questline/` |
| `questline_run_id` | session | One `RunStarted`/`RunFinished` per session |
| `driver_handle` | session | Live `DriverHandle` (mock in phase 03) |
| `questline_ctx` | function | Per-test `Context` (driver, bus, wait policy, data) |

CLI options: `--questline-profile`, `--questline-config`, `--include-quarantined`,
`--feature`, `--questline-quarantine`.

## Markers

```python
from questline.authoring.markers import quest

@quest.smoke
@quest.regression
@quest.quarantined   # excluded unless --include-quarantined
@pytest.mark.feature("shop-pack")  # optional; stored as tests.feature_id
```

(Pytest cannot express `@pytest.mark.quest.smoke` — use `@quest.smoke` or
`@pytest.mark.quest_smoke`.)

Custom markers can be listed on a profile:

```toml
[profile.mock]
driver = "mock"
markers = ["quest.demo"]
```

### Feature metadata (feature-pipeline hook)

`@pytest.mark.feature("<id>")` is optional and non-breaking. When present it:

1. Is written to the run store `tests.feature_id` column (migration v2).
2. Is filterable at collection with `--feature <id>`.
3. May appear on quarantine ledger entries (`feature:` field).

A future feature-registry module will join on this column.

## Pages

```python
from questline.authoring import Page

class ShopPage(Page):
    def buy(self):
        self.tap(Shop.buy_pack_button)  # locator from registry/codegen
```

Wait policies compose: **profile default < page override < call override**.
Never rebuild a fresh `WaitPolicy(deadline=…)` that silently resets other fields —
use `WaitPolicy.with_overrides(...)`.

## Steps & Scenario

Nothing executes until `.run(ctx)`. Inline callables are first-class steps.

```python
from questline.authoring import (
    AssertThat, HandleOptional, Save, Scenario, Tap, WaitFor, expect,
)

scenario = (
    Scenario("buy pack")
    .step(Tap(Shop.open_button))
    .step(WaitFor(Shop.root))
    .step(HandleOptional(Popup.rate_us, Tap(Popup.dismiss, budget="probe")))
    .call(lambda ctx: ctx.save("coins", ShopPage(ctx).coins()))
    .step(AssertThat(lambda ctx: expect(ctx["coins"]).equals(50)))
)
scenario.run(questline_ctx)
```

Every step emits `StepStarted` / `StepFinished` with real timestamps (execution
truth). `HandleOptional` uses the **probe** budget only.

## Assertions

```python
expect(actual).equals(x)
expect(actual).differs(x)
expect(actual).is_true()
expect(actual).contains(item)
```

Constructing `expect(x)` **without** a comparator and wrapping it in
`AssertThat(...)` raises `AuthoringError` at build time.

## Quarantine ledger

Versioned file (default `quarantine.yaml`):

```yaml
version: 1
entries:
  - test_id: path/to/test.py::test_name
    reason: "..."
    date: "2026-07-29"
    owner: "you"
    exit_criteria: "passes 20 CI runs"
    issue: "https://..."
    feature: "shop-pack"   # optional
```

```bash
questline quarantine add <nodeid> --reason ... --owner ... --exit-criteria ...
questline quarantine remove <nodeid>
questline quarantine audit --path examples/demo-tests/quarantine.yaml \
  --tests examples/demo-tests
```

`audit` exits non-zero on **limbo** (marker without ledger entry or vice versa).
Also mark the test `@pytest.mark.quest.quarantined`.

## Death-point

On failure the store answers last-started / last-finished step plus driver health
tags captured by the plugin (`driver_alive`, `app_scene`, …):

```python
store.death_point(test_id)
```
