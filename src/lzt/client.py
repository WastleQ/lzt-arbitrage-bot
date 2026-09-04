import asyncio
import logging
from typing import Any

import aiohttp

from config import settings
from lzt.schemas import BuyResult, MarketItem

logger = logging.getLogger(__name__)


class LZTClient:
    BASE_URL = "https://api.lzt.market"

    def __init__(self, api_token: str = settings.lzt_api_token) -> None:
        self.api_token = api_token
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    async def _request(
        self, method: str, endpoint: str, params: dict[str, Any] | None = None, data: dict[str, Any] | None = None
    ) -> dict[str, Any] | None:
        url = f"{self.BASE_URL}/{endpoint}"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            try:
                async with session.request(method, url, params=params, json=data, timeout=15) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 429:
                        logger.warning("LZT API Rate limit reached. Waiting...")
                        return None
                    else:
                        text = await response.text()
                        logger.error(f"LZT API Error {response.status} for {url}: {text}")
                        return None
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"LZT API Request exception for {url}: {e}")
                return None

    async def get_my_balance(self) -> dict[str, float] | None:
        data = await self._request("GET", "me")
        if data and "user" in data:
            user = data["user"]
            return {
                "balance": float(user.get("balance", 0.0)),
                "hold": float(user.get("hold", 0.0)),
            }
        return None

    async def search_items(self, category: str, params: dict[str, Any] | None = None) -> list[MarketItem]:
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
                item = MarketItem(
                    item_id=int(raw.get("item_id", 0)),
                    category=category,
                    title=raw.get("title", "No Title"),
                    price=float(raw.get("price", 0.0)),
                    currency=raw.get("currency", "RUB"),
                    item_state=raw.get("item_state", "active"),
                    published_date=int(raw.get("published_date", 0)),
                    seller_username=raw.get("seller", {}).get("username", "unknown"),
                    raw_data=raw,
                )
                items.append(item)
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
        else:
            err_msg = data.get("error", "Unknown error") if data else "Network or API failure"
            return BuyResult(
                success=False,
                message=err_msg,
                item_id=item_id,
            )

    async def relist_item(self, item_id: int, price: float, title: str) -> bool:
        data = await self._request("POST", f"{item_id}/edit", data={"price": price, "title": title})
        return bool(data and data.get("status") == "ok")
