"""AltTesterDriver passes DriverPort conformance against a fake transport (CI)."""

from __future__ import annotations

import pytest

from questline.drivers.alttester.fake import FakeAltDriverHarness
from questline.drivers.conformance import CONFORMANCE_CASES


@pytest.mark.parametrize("case", CONFORMANCE_CASES, ids=lambda c: c.__name__)
def test_alttester_conformance_fake_transport(case) -> None:
    case(FakeAltDriverHarness(sleeper=lambda _s: None))
