from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass

import aiohttp

from cdp_http import CdpHttpClient
from config import ApiConfig, FlowConfig, PipelineConfig, SlippageConfig
from slippage import assess_token_slippage
from sql_flows import fetch_gross_flows

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Candidate:
    token_address: str
    gross_flow_usd: float
    trade_count: int
    max_slippage: float


async def _rank_candidates(
    client: CdpHttpClient,
    flow_config: FlowConfig,
    slippage_config: SlippageConfig,
) -> list[Candidate]:
    start = time.monotonic()
    flows = await fetch_gross_flows(client, flow_config)
    flow_latency = time.monotonic() - start
    logger.info("flow_scan_tokens=%s flow_latency_s=%.3f", len(flows), flow_latency)

    flow_map = {token.token_address: token for token in flows}
    tasks = []
    for token in flows:
        if token.token_address.lower() == slippage_config.usdc_address.lower():
            continue
        tasks.append(assess_token_slippage(client, token.token_address, slippage_config))
    start = time.monotonic()
    assessments = await asyncio.gather(*tasks, return_exceptions=True)
    slippage_latency = time.monotonic() - start
    logger.info("slippage_latency_s=%.3f", slippage_latency)

    ok_tokens: list[Candidate] = []
    for assessment in assessments:
        if isinstance(assessment, Exception):
            logger.warning("slippage check failed: %s", assessment)
            continue
        if not assessment.ok:
            continue
        flow = flow_map.get(assessment.token_address)
        if not flow:
            continue
        ok_tokens.append(
            Candidate(
                token_address=assessment.token_address,
                gross_flow_usd=flow.gross_flow_usd,
                trade_count=flow.trade_count,
                max_slippage=assessment.max_slippage,
            )
        )
    return sorted(ok_tokens, key=lambda item: item.gross_flow_usd, reverse=True)


async def run_pipeline() -> None:
    logging.basicConfig(level=logging.INFO)
    api_config = ApiConfig()
    flow_config = FlowConfig()
    slippage_config = SlippageConfig()
    pipeline_config = PipelineConfig()
    semaphore = asyncio.Semaphore(pipeline_config.concurrent_quotes)

    async with aiohttp.ClientSession() as session:
        client = CdpHttpClient(api_config, session, semaphore)
        while True:
            start = time.monotonic()
            try:
                candidates = await _rank_candidates(client, flow_config, slippage_config)
            except Exception as exc:
                logger.exception("pipeline error: %s", exc)
                candidates = []
            latency = time.monotonic() - start
            logger.info("candidate_count=%s total_latency_s=%.3f", len(candidates), latency)
            for candidate in candidates:
                logger.info(
                    "candidate=%s gross_flow_usd=%.2f trade_count=%s max_slippage=%.4f",
                    candidate.token_address,
                    candidate.gross_flow_usd,
                    candidate.trade_count,
                    candidate.max_slippage,
                )
            await asyncio.sleep(pipeline_config.poll_interval_s)


if __name__ == "__main__":
    asyncio.run(run_pipeline())
