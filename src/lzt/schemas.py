from dataclasses import dataclass
from typing import Any


@dataclass
class MarketItem:
    item_id: int
    category: str
    title: str
    price: float
    currency: str
    item_state: str
    published_date: int
    seller_username: str
    raw_data: dict[str, Any]


@dataclass
class BuyResult:
    success: bool
    message: str
    item_id: int
    purchase_price: float | None = None
    account_data: dict[str, Any] | None = None
