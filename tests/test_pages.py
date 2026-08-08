"""Page wait-policy composition and DriverHandle access."""

from __future__ import annotations

from questline.authoring.context import Context
from questline.authoring.pages import Page
from questline.core.events import EventBus
from questline.core.waits import WaitPolicy
from questline.drivers.handle import DriverHandle
from questline.drivers.locators import Locator, LocatorStrategy
from questline.drivers.mock import MockDriver
from questline.drivers.mock.scene import MockNode, MockScene
from questline.drivers.port import ConnectionTarget


def test_page_find_and_exists() -> None:
    scene = MockScene()
    scene.add(MockNode(id="a", name="A", text="hi"))
    driver = MockDriver(scene)
    driver.connect(ConnectionTarget())
    ctx = Context(
        driver=DriverHandle(driver),
        bus=EventBus(),
        run_id="r",
        test_id="t",
        wait_policy=WaitPolicy(probe=0.05, deadline=0.3, interval=0.01),
    )
    page = Page(ctx, wait=WaitPolicy(probe=0.05, deadline=0.4, interval=0.01))
    loc = Locator(by=LocatorStrategy.ID, value="a")
    assert page.find(loc).text == "hi"
    assert page.exists(loc) is True
    assert page.exists(Locator(by=LocatorStrategy.ID, value="nope")) is False
    page.tap(loc)
    assert page.driver is ctx.driver
    policy = page.wait_policy()
    assert policy.deadline == 0.4
