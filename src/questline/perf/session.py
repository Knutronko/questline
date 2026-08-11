"""Session helpers: choose collectors and bind probe lifecycle to pytest."""

from __future__ import annotations

import logging
from typing import Any

from questline.core.config import PerfSettings, Settings
from questline.perf.android import AndroidPerfCollector, bind_android_shell
from questline.perf.companion import companion_collector_from_driver
from questline.perf.probe import PerfProbe

logger = logging.getLogger("questline.perf.session")

DEFAULT_METRICS = (
    "fps",
    "jank_pct",
    "memory_pss_mb",
    "cpu_pct",
    "battery_temp_c",
    "battery_level",
    "allocated_mb",
    "draw_calls",
    "thermal_temp_c",
)


def build_collectors(
    settings: Settings,
    *,
    driver: Any | None = None,
    device_bundle: Any | None = None,
) -> list[Any]:
    """Select Android and/or companion collectors from ``settings.perf.source``."""
    perf = settings.perf
    source = (perf.source or "auto").lower()
    collectors: list[Any] = []

    want_android = source in {"auto", "android"}
    want_companion = source in {"auto", "companion"}

    if want_android and device_bundle is not None and settings.app_package:
        provider = device_bundle.get("provider")
        device = device_bundle.get("device")
        if provider is not None and device is not None:
            shell = bind_android_shell(provider, device)
            collectors.append(AndroidPerfCollector(shell=shell, package=settings.app_package))
            logger.info("PerfProbe: android collectors enabled for %s", settings.app_package)
        elif source == "android":
            logger.warning("PerfProbe source=android but no adb device/package — no collectors")

    if want_companion and driver is not None:
        platform = (settings.target_platform or "").lower()
        driver_name = (settings.driver or "").lower()
        supports_hooks = driver_name in {"questline", "alttester"} or hasattr(
            driver, "call_game_method"
        )
        # Prefer companion on editor/standalone; on android auto, dumpsys covers device.
        use_companion = False
        if source == "companion" and supports_hooks:
            use_companion = True
        elif source == "auto" and supports_hooks:
            if platform in {"editor", "standalone", "standalone_exe"}:
                use_companion = True
            elif not collectors:
                use_companion = True
        if use_companion:
            collectors.append(companion_collector_from_driver(driver))
            logger.info("PerfProbe: companion collector enabled")

    if not collectors:
        logger.warning(
            "PerfProbe enabled but no collectors configured "
            "(need adb+app_package and/or a connected driver with GetPerfSample)"
        )
    return collectors


def create_probe(
    settings: Settings,
    *,
    bus: Any,
    run_id: str,
    driver: Any | None = None,
    device_bundle: Any | None = None,
) -> PerfProbe | None:
    """Build a ``PerfProbe`` when ``settings.perf.enabled``, else None."""
    perf: PerfSettings = settings.perf
    if not perf.enabled:
        return None
    collectors = build_collectors(settings, driver=driver, device_bundle=device_bundle)
    if not collectors:
        return None
    metrics = list(perf.metrics) if perf.metrics else list(DEFAULT_METRICS)
    return PerfProbe(
        bus=bus,
        run_id=run_id,
        collectors=collectors,
        interval_s=perf.interval_s,
        metrics=metrics,
    )
