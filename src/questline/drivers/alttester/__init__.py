"""AltTester DriverPort adapter (requires optional extra ``questline[alttester]``)."""

from questline.drivers.alttester.driver import SUPPORTED_PLATFORMS, AltTesterDriver
from questline.drivers.alttester.hooks import HookArgSpec, HookManifestEntry
from questline.drivers.alttester.queries import AltNativeQuery, compile_locator

__all__ = [
    "SUPPORTED_PLATFORMS",
    "AltNativeQuery",
    "AltTesterDriver",
    "HookArgSpec",
    "HookManifestEntry",
    "compile_locator",
]
