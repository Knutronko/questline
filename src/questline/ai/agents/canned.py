"""Canned MockDriver spec test for HUD smoke / CLI --demo (no live LLM)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from questline.ai.port import LlmResponse, TokenUsage, ToolCall

CANNED_MOCKDRIVER_TEST = '''\
"""Generated spec test (self-contained MockDriver, no game-repo pages)."""
from questline.drivers.locators import Locator, LocatorStrategy
from questline.drivers.mock import MockDriver, MockNode, MockScene
from questline.drivers.port import ConnectionTarget


def _scene() -> MockScene:
    scene = MockScene()
    scene.scene_name = "DemoGame"
    root = MockNode(id="main.root", name="MainMenu", path="/MainMenu")
    play = MockNode(
        id="main.play", name="PlayButton", path="/MainMenu/Play", text="Play"
    )
    scene.add(root)
    scene.add(play, parent=root)
    hud = MockNode(id="hud.root", name="Hud", path="/Hud", visible=False)
    coins = MockNode(
        id="hud.coins",
        name="Coins",
        path="/Hud/Coins",
        text="Coins: 100",
        visible=False,
    )
    scene.add(hud)
    scene.add(coins, parent=hud)

    def on_play() -> None:
        root.visible = False
        play.visible = False
        hud.visible = True
        coins.visible = True

    play.on_tap = on_play
    return scene


def test_play_reaches_hud_from_spec() -> None:
    driver = MockDriver(_scene())
    driver.connect(ConnectionTarget(host="mock", port=0))
    play = driver.find(Locator(by=LocatorStrategy.ID, value="main.play"))
    driver.tap(play)
    node = driver.find(Locator(by=LocatorStrategy.ID, value="hud.coins"))
    assert node.text == "Coins: 100"
'''

NO_KEY_HINT = (
    "The model did not write a pytest file (typical with no live LLM / fake-ok). "
    "HUD: open Generate and leave 'Demo' checked. CLI: add --demo. "
    "Live: -p ai_groq with GROQ_API_KEY."
)


def output_dir_from_text(*parts: str) -> str:
    blob = "\n".join(p for p in parts if p)
    for line in blob.splitlines():
        if line.startswith("OUTPUT_DIR:"):
            return line.split(":", 1)[1].strip()
    return "generated-tests"


def write_test_to_from_text(*parts: str) -> str | None:
    blob = "\n".join(p for p in parts if p)
    for line in blob.splitlines():
        if line.startswith("WRITE_TEST_TO:"):
            return line.split(":", 1)[1].strip()
    return None


def demo_generate_complete(req: Any) -> LlmResponse:
    """First turn: write_file. Second: JSON claim (gate still owns green/red)."""
    usage = TokenUsage(tokens_in=10, tokens_out=20)
    saw_tools = any("TOOL RESULTS" in (m.content or "") for m in req.messages)
    if req.tools and not saw_tools:
        dest = output_dir_from_text(
            req.system or "", *(m.content for m in req.messages)
        )
        assigned = write_test_to_from_text(
            req.system or "", *(m.content for m in req.messages)
        )
        path = assigned or str(Path(dest) / "test_from_spec.py")
        return LlmResponse(
            text="",
            tool_calls=(
                ToolCall(
                    id="c1",
                    name="write_file",
                    arguments=json.dumps(
                        {"path": path, "content": CANNED_MOCKDRIVER_TEST}
                    ),
                ),
            ),
            usage=usage,
            provider="fake",
            model="fake-test",
            duration_ms=1.0,
        )
    return LlmResponse(
        text=json.dumps(
            {
                "verdict": "diagnosed",
                "cause": "unknown",
                "summary": (
                    "Wrote canned MockDriver Play→HUD test. Unity will not move. "
                    "Gate owns green/red."
                ),
            }
        ),
        usage=usage,
        provider="fake",
        model="fake-test",
        duration_ms=1.0,
    )


class DemoGenerateProvider:
    """Deterministic spec→test writer for smoke / --demo. No network."""

    name = "fake"
    model = "fake-test"
    kind = "fake"

    def complete(self, req: Any) -> LlmResponse:
        return demo_generate_complete(req)
