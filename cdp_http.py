from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any, Mapping
from urllib.parse import urlparse

import aiohttp

from config import ApiConfig

logger = logging.getLogger(__name__)

TRANSIENT_STATUS = {429, 500, 502, 503, 504}


@dataclass
class CdpResponse:
    status: int
    json: Any
    latency_s: float


class CdpHttpClient:
    def __init__(
        self,
        api_config: ApiConfig,
        session: aiohttp.ClientSession,
        semaphore: asyncio.Semaphore,
    ) -> None:
        self._api_config = api_config
        self._session = session
        self._semaphore = semaphore

    async def get(self, path: str, params: Mapping[str, Any] | None = None) -> CdpResponse:
        return await self._request("GET", path, params=params)

    async def post(self, path: str, json: Mapping[str, Any]) -> CdpResponse:
        return await self._request("POST", path, json=json)

    async def _request(
        self,
        method: str,
        path: str,
        params: Mapping[str, Any] | None = None,
        json: Mapping[str, Any] | None = None,
    ) -> CdpResponse:
        url = f"{self._api_config.base_url}{path}"
        parsed = urlparse(url)
        timeout = aiohttp.ClientTimeout(total=self._api_config.timeout_s)
        attempt = 0
        while True:
            attempt += 1
            headers = self._build_auth_headers(method, parsed.path)
            async with self._semaphore:
                start = time.monotonic()
                async with self._session.request(
                    method,
                    url,
                    params=params,
                    json=json,
                    headers=headers,
                    timeout=timeout,
                ) as response:
                    latency = time.monotonic() - start
                    payload = await self._parse_json(response)
                    if response.status in TRANSIENT_STATUS and attempt <= self._api_config.max_retries:
                        logger.warning(
                            "Transient HTTP %s on %s %s attempt=%s",
                            response.status,
                            method,
                            path,
                            attempt,
                        )
                        await asyncio.sleep(self._api_config.retry_backoff_s * attempt)
                        continue
                    return CdpResponse(status=response.status, json=payload, latency_s=latency)

    @staticmethod
    async def _parse_json(response: aiohttp.ClientResponse) -> Any:
        content_type = response.headers.get("Content-Type", "")
        if "application/json" in content_type:
            return await response.json()
        return await response.text()

    def _build_auth_headers(self, method: str, path: str) -> Mapping[str, str]:
        try:
            from cdp.auth import get_auth_headers
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "cdp.auth is required. Install the Coinbase CDP SDK to use JWT auth."
            ) from exc

        return get_auth_headers(method=method, host=self._api_config.host, path=path)
