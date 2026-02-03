from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class WmaPoint:
    timestamp: float
    value: float


def compute_wma(prices: Iterable[float], window: int) -> list[WmaPoint]:
    raise NotImplementedError("Indicators are not implemented in this phase.")
