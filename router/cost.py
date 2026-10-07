"""Cost from configured prices. Prices live in config/prices.yaml; a missing price is an error, never a guess."""
from __future__ import annotations

from dataclasses import dataclass

from .errors import MissingPriceError


@dataclass(frozen=True)
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0

    def __add__(self, o: "Usage") -> "Usage":
        return Usage(self.input_tokens + o.input_tokens, self.output_tokens + o.output_tokens)


class PriceBook:
    def __init__(self, table: dict):
        self.table = table or {}

    def cost(self, price_key: str, usage: Usage) -> float:
        entry = self.table.get(price_key)
        if entry is None:
            raise MissingPriceError(f"no entry for {price_key!r} in config/prices.yaml — add one (fill from the provider's pricing page)")
        missing = [f for f in ("input_per_million", "output_per_million") if entry.get(f) is None]
        if missing:
            raise MissingPriceError(f"config/prices.yaml: {price_key!r} has no value for {', '.join(missing)} — "
                                    "fill from the provider's pricing page (write 0.0 if the model is genuinely free)")
        for f in ("input_per_million", "output_per_million"):
            if not isinstance(entry[f], (int, float)) or entry[f] < 0:
                raise MissingPriceError(f"config/prices.yaml: {price_key!r}.{f} must be a non-negative number")
        return (usage.input_tokens * entry["input_per_million"] + usage.output_tokens * entry["output_per_million"]) / 1_000_000

    def has_price(self, price_key: str) -> bool:
        e = self.table.get(price_key) or {}
        return isinstance(e.get("input_per_million"), (int, float)) and isinstance(e.get("output_per_million"), (int, float))
