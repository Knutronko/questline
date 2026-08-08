"""Distinct process exit codes for resilience aborts (phase-06).

These are reserved outside pytest's usual 0-5 range and typer's 1-2 usage.
"""

from __future__ import annotations

EXIT_WATCHDOG = 140
EXIT_CIRCUIT_BREAKER = 141

__all__ = ["EXIT_CIRCUIT_BREAKER", "EXIT_WATCHDOG"]
