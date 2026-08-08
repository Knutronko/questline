"""Wire smoke path bootstrap."""

from __future__ import annotations

import sys
from pathlib import Path

_SMOKE = Path(__file__).resolve().parent
if str(_SMOKE) not in sys.path:
    sys.path.insert(0, str(_SMOKE))
