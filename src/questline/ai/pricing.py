"""Versioned model pricing table. Cost is estimated locally — never from the model."""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib.resources import files
from typing import Any

PRICING_VERSION = "1"


@dataclass(frozen=True, slots=True)
class ModelRates:
    input_per_mtok: float
    output_per_mtok: float
    cached_input_factor: float = 0.5


@dataclass(frozen=True, slots=True)
class PricingTable:
    version: str
    models: dict[str, ModelRates]
    kind_defaults: dict[str, ModelRates]
    unknown: ModelRates

    def rates_for(self, *, model: str, kind: str) -> ModelRates:
        if kind == "ollama":
            return self.kind_defaults.get("ollama", ModelRates(0.0, 0.0))
        if model in self.models:
            return self.models[model]
        if kind in self.kind_defaults:
            return self.kind_defaults[kind]
        return self.unknown

    def estimate(
        self,
        *,
        model: str,
        kind: str,
        tokens_in: int,
        tokens_out: int,
        cached: bool = False,
        cached_tokens: int = 0,
    ) -> float:
        if kind == "ollama":
            return 0.0
        rates = self.rates_for(model=model, kind=kind)
        billed_in = max(0, int(tokens_in))
        cached_n = max(0, int(cached_tokens))
        if cached and cached_n == 0:
            cached_n = billed_in
        cached_n = min(cached_n, billed_in)
        full_in = billed_in - cached_n
        in_cost = (full_in / 1_000_000.0) * rates.input_per_mtok
        in_cost += (cached_n / 1_000_000.0) * rates.input_per_mtok * rates.cached_input_factor
        out_cost = (max(0, int(tokens_out)) / 1_000_000.0) * rates.output_per_mtok
        return round(in_cost + out_cost, 8)


def load_pricing(*, version: str = PRICING_VERSION) -> PricingTable:
    if version != PRICING_VERSION:
        raise ValueError(f"unknown pricing version {version!r}; have {PRICING_VERSION}")
    raw_text = files("questline.ai").joinpath("pricing_v1.json").read_text(encoding="utf-8")
    raw: dict[str, Any] = json.loads(raw_text)
    return PricingTable(
        version=str(raw.get("version") or version),
        models={k: _rates(v) for k, v in (raw.get("models") or {}).items()},
        kind_defaults={k: _rates(v) for k, v in (raw.get("kind_defaults") or {}).items()},
        unknown=_rates(raw.get("unknown") or {"input_per_mtok": 1.0, "output_per_mtok": 3.0}),
    )


def _rates(raw: Any) -> ModelRates:
    if not isinstance(raw, dict):
        return ModelRates(1.0, 3.0)
    return ModelRates(
        input_per_mtok=float(raw.get("input_per_mtok") or 0.0),
        output_per_mtok=float(raw.get("output_per_mtok") or 0.0),
        cached_input_factor=float(raw.get("cached_input_factor") or 0.5),
    )
