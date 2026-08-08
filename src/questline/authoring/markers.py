"""Questline pytest markers (architecture §4).

Pytest cannot do ``@pytest.mark.quest.smoke`` (attribute access on a MarkDecorator).
Use either ``@quest.smoke`` from this module or ``@pytest.mark.quest_smoke``.
"""

from __future__ import annotations

import pytest

smoke = pytest.mark.quest_smoke
regression = pytest.mark.quest_regression
quarantined = pytest.mark.quest_quarantined


class _QuestMarks:
    smoke = smoke
    regression = regression
    quarantined = quarantined


quest = _QuestMarks()

__all__ = ["quest", "quarantined", "regression", "smoke"]
