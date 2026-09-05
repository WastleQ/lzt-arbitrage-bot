import asyncio
import time
from typing import Any

import aiohttp

from src.config import settings
from src.lzt.schemas import BuyResult, MarketItem
from src.utils.logger import logger
from src.utils.rate_limiter import AsyncRateLimiter


class LZTAPIError(Exception):
    pass


class LZTClient:
    BASE_URL = "https://api.lzt.market"

    def __init__(
        self,
        api_token: str | None = None,
        session: aiohttp.ClientSession | None = None,
        rate_limiter: AsyncRateLimiter | None = None,
    ) -> None:
        self.api_token = api_token or settings.lzt_api_token
        self._external_session = session is not None
        self._session = session
        self._rate_limiter = rate_limiter or AsyncRateLimiter(
            rate=settings.rate_limit_rps,
            burst=settings.rate_limit_burst,
        )

    @property
    def headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": f"lzt-arbitrage-bot/{settings.version}",
        }

    async def _ensure_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(headers=self.headers)
            self._external_session = False
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed and not self._external_session:
            await self._session.close()

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"
        last_exc: Exception | None = None

        for attempt in range(settings.request_retries):
            try:
                await self._rate_limiter.acquire()
                session = await self._ensure_session()
                request_kwargs: dict[str, Any] = {
                    "params": params,
                    "json": data,
                    "timeout": 15,
                }
                if settings.proxy_url:
                    request_kwargs["proxy"] = settings.proxy_url

                async with session.request(
                    method,
                    url,
                    **request_kwargs,
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    if response.status == 429:
                        retry_after = float(response.headers.get("Retry-After", 0) or 0)
                        wait = retry_after or settings.request_backoff_base * (
                            2**attempt
                        )
                        logger.warning(
                            f"Rate limited (429) on {endpoint}. Sleeping {wait:.1f}s (attempt {attempt + 1})"
                        )
                        await asyncio.sleep(wait)
                        continue
                    if 500 <= response.status < 600:
                        wait = settings.request_backoff_base * (2**attempt)
                        logger.warning(
                            f"Server error {response.status} on {endpoint}. Retry in {wait:.1f}s"
                        )
                        await asyncio.sleep(wait)
                        continue
                    text = await response.text()
                    logger.error(
                        f"LZT API Error {response.status} for {url}: {text[:300]}"
                    )
                    return None
            except asyncio.CancelledError:
                raise
            except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                last_exc = exc
                wait = settings.request_backoff_base * (2**attempt)
                logger.warning(
                    f"Network error for {url}: {exc}. Retry in {wait:.1f}s (attempt {attempt + 1})"
                )
                await asyncio.sleep(wait)

        logger.error(f"All retries exhausted for {url}: {last_exc}")
        return None

    async def get_my_balance(self) -> dict[str, float] | None:
        started = time.monotonic()
        data = await self._request("GET", "me")
        logger.debug(f"Balance API response: {data}")
        if data:
            user = data.get("user") or data
            balance = float(user.get("balance", user.get("money", 0.0)))
            hold = float(user.get("hold", user.get("hold_money", 0.0)))
            logger.debug(
                f"Balance fetched in {(time.monotonic() - started) * 1000:.0f}ms: balance={balance}, hold={hold}"
            )
            return {
                "balance": balance,
                "hold": hold,
            }
        return None

    def build_item_url(self, item_id: int) -> str:
        return f"https://lzt.market/{item_id}/"

    def build_seller_profile_url(self, username: str) -> str:
        if not username or username == "unknown":
            return "https://lzt.market/"
        return f"https://lzt.market/{username}/"

    async def search_items(
        self, category: str, params: dict[str, Any] | None = None
    ) -> list[MarketItem]:
        endpoint_map = {
            "minecraft": "minecraft",
            "brawlstars": "supercell",
            "valorant": "riot",
        }
        path = endpoint_map.get(category, category)
        query_params = params or {}
        query_params.setdefault("order_by", "pushed_at")

        response = await self._request("GET", path, params=query_params)
        items: list[MarketItem] = []

        if response and "items" in response:
            for raw in response["items"]:
                seller = raw.get("seller") or {}
                items.append(
                    MarketItem(
                        item_id=int(raw.get("item_id", 0)),
                        category=category,
                        title=raw.get("title", "No Title"),
                        price=float(raw.get("price", 0.0)),
                        currency=raw.get("currency", "RUB"),
                        item_state=raw.get("item_state", "active"),
                        published_date=int(raw.get("published_date", 0)),
                        seller_username=seller.get("username", "unknown"),
                        seller_trust=int(seller.get("trust", 0))
                        if str(seller.get("trust", 0)).isdigit()
                        else 0,
                        item_url=raw.get("url")
                        or self.build_item_url(int(raw.get("item_id", 0))),
                        raw_data=raw,
                    )
                )
        return items

    async def fast_buy(self, item_id: int, price: float) -> BuyResult:
        data = await self._request("POST", f"{item_id}/fast-buy", data={"price": price})
        if data and data.get("status") == "ok":
            return BuyResult(
                success=True,
                message="Successfully purchased!",
                item_id=item_id,
                purchase_price=price,
                account_data=data.get("account", {}),
            )
        err_msg = (
            data.get("error", "Unknown error") if data else "Network or API failure"
        )
        return BuyResult(success=False, message=err_msg, item_id=item_id)

    async def relist_item(self, item_id: int, price: float, title: str) -> bool:
        data = await self._request(
            "POST", f"{item_id}/edit", data={"price": price, "title": title}
        )
        return bool(data and data.get("status") == "ok")
