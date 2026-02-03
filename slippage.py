from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from cdp_http import CdpHttpClient
from config import SlippageConfig


@dataclass(frozen=True)
class QuoteResult:
    slippage: float
    liquidity_available: bool
    to_amount: int
    min_to_amount: int


@dataclass(frozen=True)
class SlippageAssessment:
    token_address: str
    ok: bool
    max_slippage: float


def _to_base_units(amount: float, decimals: int) -> int:
    return int(Decimal(str(amount)) * (Decimal(10) ** decimals))


def _compute_slippage(to_amount: int, min_to_amount: int) -> float:
    if to_amount <= 0:
        return 1.0
    return max(0.0, 1.0 - (min_to_amount / to_amount))


async def _fetch_quote(
    client: CdpHttpClient,
    chain_id: int,
    from_asset: str,
    to_asset: str,
    amount: int,
) -> QuoteResult:
    response = await client.get(
        "/platform/v2/evm/swaps/quote",
        params={
            "chainId": chain_id,
            "fromAsset": from_asset,
            "toAsset": to_asset,
            "amount": str(amount),
        },
    )
    if response.status >= 400:
        raise RuntimeError(f"Quote failed: {response.status} {response.json}")
    payload = response.json if isinstance(response.json, dict) else {}
    to_amount = int(payload.get("toAmount", 0))
    min_to_amount = int(payload.get("minToAmount", 0))
    slippage = _compute_slippage(to_amount, min_to_amount)
    return QuoteResult(
        slippage=slippage,
        liquidity_available=bool(payload.get("liquidityAvailable", False)),
        to_amount=to_amount,
        min_to_amount=min_to_amount,
    )


async def assess_token_slippage(
    client: CdpHttpClient,
    token_address: str,
    config: SlippageConfig,
    sizes_usdc: Iterable[float] | None = None,
) -> SlippageAssessment:
    sizes = list(sizes_usdc or config.quote_sizes_usdc)
    max_seen = 0.0
    for size in sizes:
        amount_in = _to_base_units(size, 6)
        buy_quote = await _fetch_quote(
            client,
            config.chain_id,
            config.usdc_address,
            token_address,
            amount_in,
        )
        if not buy_quote.liquidity_available:
            return SlippageAssessment(token_address=token_address, ok=False, max_slippage=1.0)
        if buy_quote.to_amount <= 0:
            return SlippageAssessment(token_address=token_address, ok=False, max_slippage=1.0)
        max_seen = max(max_seen, buy_quote.slippage)

        sell_quote = await _fetch_quote(
            client,
            config.chain_id,
            token_address,
            config.usdc_address,
            buy_quote.to_amount,
        )
        if not sell_quote.liquidity_available:
            return SlippageAssessment(token_address=token_address, ok=False, max_slippage=1.0)
        max_seen = max(max_seen, sell_quote.slippage)

    ok = max_seen <= config.max_slippage
    return SlippageAssessment(token_address=token_address, ok=ok, max_slippage=max_seen)
