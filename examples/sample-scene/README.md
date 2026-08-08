# Sample scene notes (generic)

For the phase-04 smoke suite (`examples/unity-smoke/`), any Unity scene works if it has:

1. AltTester Prefab (instrumentation server)
2. `com.questline.companion` with at least one registered hook (e.g. `Ping` → `"pong"`)
3. GameObjects named `QuestlineSmokeRoot` and `QuestlineSmokeButton` (UI Button)

Full steps: [docs/unity-setup.md](../../docs/unity-setup.md).
