# Eval harness (phase 13)

How to add a golden, how to read the metrics, and what the numbers do **not**
claim. Operator surface: HUD **Eval** (scores) and HUD **Generate** (spec→test).
CLI extra: `questline ai eval` / `questline ai generate --demo`.

Related: [`ai-agents.md`](ai-agents.md) · [`02-AI-ROADMAP.md`](02-AI-ROADMAP.md) §3.6 ·
brief [`phase-13-ai-generation-eval.md`](phases/phase-13-ai-generation-eval.md).

## Run it

HUD: open **Eval**. Fixture smoke already has `eval-a` / `eval-b`. **Compare**
renders B−A. **Run fake eval** re-runs the packaged goldens with a scripted
FakeProvider (no network).

```powershell
uv run questline ai eval --store .questline/store.db
uv run questline ai eval --compare-a eval-a --compare-b eval-b
uv run questline ai eval --export deepeval
```

`--live -p ai_groq` is **maintainer-checked** (two providers → compare two stored
ids). CI always uses `--provider fake` (the default).

`--export deepeval|langfuse` writes a **stub** JSON shape. It does not call
DeepEval or Langfuse.

## Goldens

Packaged YAML: `src/questline/evalharness/goldens/*.yaml`. Each file:

| Field | Meaning |
|-------|---------|
| `id` | Stable slug |
| `failure_class` | `locator` \| `assertion` \| `infra` \| `timing` \| `green` |
| `cause` | Ground-truth `test-bug` / `game-bug` / `infra` / `flaky` / `unknown` |
| `expected_fix_class` | What a correct fix looks like (`locator-update`, `assertion-fix`, `wait-budget`, `none`) |
| `mode` | `diagnose` or `fix` |
| `score_fix` | Count this row in **fix correctness** |
| `sabotage_gate` | Injected gate always returns green while the test is still red |
| `reply` | Scripted FakeProvider JSON for CI |

Setup text is MockDriver-flavoured on purpose (shop/coins/HUD). No P1 type/SO
names.

**Add a golden:** copy a YAML, pick a new `id`, keep `failure_class` in the
allow-list, add a scripted `reply`. Re-run `uv run pytest tests/test_evalharness.py`.

## Metrics

Numbers come from the **gate** and from comparing `cause` to YAML ground truth.
The model claim is logged and ignored.

| Metric | Formula |
|--------|---------|
| **Diagnosis accuracy** | share of rows whose `cause` matches YAML |
| **Fix correctness** | among `score_fix` rows: gate accepted **and** actually green **and** `fix_class` matches |
| **False-green rate** | share of gated rows where the gate accepted but the test was not actually green |
| **Iterations** | tool-loop turns (mean) |
| **Cost** | `ai_calls` USD for the eval run (0 on FakeProvider) |

The sabotage golden (`sabotage-bypass-gate`) **must** appear as `false_green`.
If it does not, the harness is lying — `questline ai eval` exits 1.

## Honest limits

- **n is small** (a dozen MockDriver cases). These scores are a regression
  alarm, not a published model ranking.
- **CI uses a scripted FakeProvider.** Live two-provider comparison is
  maintainer-checked and will move with prompt/model drift.
- **Variance is not estimated.** Do not quote a single run as “the” accuracy.
- **Fix class is coarse.** A locator rename vs a wait-budget is distinguished;
  a “correct” patch that the gate did not re-run is not a fix.
- Generators are adequate, not the flagship. Demo generate succeeds when pytest
  **executes**. Live generate succeeds when pytest **collects** (Unity is a later
  Launch). Collection errors are never success, even if the model said `passed`.

## Spec → test / unit-gen

HUD: **Generate**. Point `--project-root` at the game `automation/` folder so the
model can read pages/locators (never Unity C#). Set `GROQ_API_KEY` in that HUD
process — game toml often has no `[profile.ai_groq]` (INC-0011). Demo writes a
canned MockDriver test (**Unity will not move**). Uncheck Demo to follow your
steps; **collect** is not a live green — use **Launch Editor** / **Launch Android**
(Unity Play or APK must already be up). Launch is hidden for MockDriver files.

```powershell
uv run questline hud --open --config D:\Projects\ElJuegaso\automation\questline.toml --project-root D:\Projects\ElJuegaso\automation
uv run questline ai generate --spec examples/specs/buy_pack.md --out generated-tests --demo
uv run questline ai generate --spec examples/specs/buy_pack.md --out generated-tests -p ai_groq
uv run questline ai generate --spec path.md --rebuild TEST_ID
uv run questline ai unit-gen questline.core.errors
```

Without `--demo` or a live provider, generate exits 1 with `no pytest file written`
(the fake/empty provider never calls `write_file`). That is not a HUD bug.

Unit-gen writes `artifacts/agents/<id>/patch.diff`. It never git-commits.
Coverage with `--coverage` is best-effort and optional (nested pytest-cov is
noisy in CI).
