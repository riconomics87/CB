from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from cdp_http import CdpHttpClient
from config import FlowConfig


@dataclass(frozen=True)
class FlowToken:
    token_address: str
    gross_flow_usd: float
    trade_count: int


def build_gross_flow_query(config: FlowConfig) -> str:
    return f"""
    SELECT
        if(token_in = '{config.usdc_address}', token_out, token_in) AS token_address,
        sum(usd_amount) AS gross_flow_usd,
        count() AS trade_count
    FROM {config.table_name}
    WHERE chain_id = 8453
      AND block_time >= now() - INTERVAL {config.window_hours} HOUR
      AND (
          token_in = '{config.usdc_address}'
          OR token_out = '{config.usdc_address}'
      )
    GROUP BY token_address
    ORDER BY gross_flow_usd DESC
    LIMIT {config.limit}
    """


def parse_flow_rows(rows: Iterable[Iterable[Any]]) -> list[FlowToken]:
    tokens: list[FlowToken] = []
    for row in rows:
        try:
            token_address = row[0]
            gross_flow = float(row[1])
            trade_count = int(row[2])
        except (IndexError, ValueError, TypeError):
            continue
        tokens.append(
            FlowToken(
                token_address=token_address,
                gross_flow_usd=gross_flow,
                trade_count=trade_count,
            )
        )
    return tokens


async def fetch_gross_flows(client: CdpHttpClient, config: FlowConfig) -> list[FlowToken]:
    query = build_gross_flow_query(config)
    response = await client.post("/platform/v2/data/query/run", json={"query": query})
    if response.status >= 400:
        raise RuntimeError(f"Query failed with status {response.status}: {response.json}")
    rows = response.json.get("rows") if isinstance(response.json, dict) else None
    if not rows:
        return []
    return parse_flow_rows(rows)
