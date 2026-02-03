from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


@dataclass(frozen=True)
class ApiConfig:
    base_url: str = "https://api.cdp.coinbase.com"
    host: str = "api.cdp.coinbase.com"
    timeout_s: float = 20.0
    max_retries: int = 3
    retry_backoff_s: float = 0.5


@dataclass(frozen=True)
class SlippageConfig:
    chain_id: int = 8453
    usdc_address: str = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
    max_slippage: float = 0.02
    quote_sizes_usdc: Iterable[float] = field(default_factory=lambda: (100, 500, 1000))


@dataclass(frozen=True)
class FlowConfig:
    window_hours: int = 6
    limit: int = 20
    table_name: str = "base.dex_trades"
    usdc_address: str = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"


@dataclass(frozen=True)
class PipelineConfig:
    poll_interval_s: float = 60.0
    concurrent_quotes: int = 5
