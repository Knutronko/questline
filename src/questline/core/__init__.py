"""Core kernel: config, events, store, errors, waits, logging.

Health / recovery / watchdog live as submodules to avoid import cycles with
``drivers.handle`` (which imports ``core.errors``). Import them explicitly::

    from questline.core.health import HealthMonitor
    from questline.core.recovery import RecoveryPolicy
    from questline.core.watchdog import Watchdog
"""

from questline.core.config import ResilienceSettings, Settings, load_settings
from questline.core.errors import (
    AssertionFailedError,
    AuthoringError,
    DeviceError,
    ElementNotFoundError,
    InfraError,
    ProviderError,
    QuestlineError,
    SessionLostError,
    TestError,
    TimeoutExceededError,
    Verdict,
    classify,
    normalize_exception,
)
from questline.core.events import Event, EventBus
from questline.core.exit_codes import EXIT_CIRCUIT_BREAKER, EXIT_WATCHDOG
from questline.core.migrations import CURRENT_SCHEMA_VERSION
from questline.core.store import RunStore
from questline.core.waits import WaitPolicy, WaitSkipped, resolve_policy, wait_for

__all__ = [
    "CURRENT_SCHEMA_VERSION",
    "AssertionFailedError",
    "AuthoringError",
    "DeviceError",
    "EXIT_CIRCUIT_BREAKER",
    "EXIT_WATCHDOG",
    "ElementNotFoundError",
    "Event",
    "EventBus",
    "InfraError",
    "ProviderError",
    "QuestlineError",
    "ResilienceSettings",
    "RunStore",
    "SessionLostError",
    "Settings",
    "TestError",
    "TimeoutExceededError",
    "Verdict",
    "WaitPolicy",
    "WaitSkipped",
    "classify",
    "load_settings",
    "normalize_exception",
    "resolve_policy",
    "wait_for",
]
