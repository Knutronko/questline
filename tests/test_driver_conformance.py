"""MockDriver passes the full DriverPort conformance suite."""

from __future__ import annotations

import pytest

from questline.drivers.conformance import CONFORMANCE_CASES
from questline.drivers.mock import MockDriver


@pytest.mark.parametrize("case", CONFORMANCE_CASES, ids=lambda c: c.__name__)
def test_mock_conformance(case) -> None:
    case(MockDriver)
