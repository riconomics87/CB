from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReturnWindow:
    token_address: str
    return_pct: float


def compute_returns() -> list[ReturnWindow]:
    raise NotImplementedError("Return calculation is not implemented in this phase.")
