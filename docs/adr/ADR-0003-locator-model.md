# ADR-0003: Driver-agnostic locator model (adapters compile)

- **Status:** accepted (phase-02)
- **Context:** Questline must switch UI drivers (Mock → AltTester → Poco → Appium) without
  rewriting pages/steps. Each backend has a different query language. Hard-coding native
  selectors in tests would freeze the stack to one adapter.
- **Decision:** Authors declare locators in a driver-agnostic model
  `Locator(by=id|name|path|text|component, value, scope?)`, typically via `locators.yaml`
  and a codegen step that emits typed page accessors (generated file committed; never
  hand-edited). Each `DriverPort` adapter implements `compile(Locator) -> native query`
  and runs that query against its transport. The conformance suite asserts semantic
  contracts (find/wait/errors/hierarchy/screenshot/alive) so “easy to switch drivers”
  is a tested claim. Consumers never cache a raw driver: they hold a `DriverHandle` that
  resolves the live instance after session reset.
- **Consequences:** New adapters are mostly a compile + transport layer. Locator expressiveness
  is the intersection of backends (no adapter-specific `by` values in the shared model).
  Richer native queries stay behind `compile` / adapter extras, not in page objects.
  Codegen must be re-run when `locators.yaml` changes; CI should treat generated drift as a
  failure once a check is added (backlog if not in this phase).
