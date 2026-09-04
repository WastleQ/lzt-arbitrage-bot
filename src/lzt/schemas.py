from dataclasses import dataclass, field
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
    seller_trust: int = 0
    item_url: str = ""
    raw_data: dict[str, Any] = field(default_factory=dict)

    def short_title(self, max_len: int = 60) -> str:
        t = self.title.strip() or "No Title"
        return t if len(t) <= max_len else t[: max_len - 1] + "…"


@dataclass
class BuyResult:
    success: bool
    message: str
    item_id: int
    purchase_price: float | None = None
    account_data: dict[str, Any] | None = None

    def account_lines(self) -> list[str]:
        if not self.account_data:
            return []
        lines: list[str] = []
        for key, value in self.account_data.items():
            value_str = str(value)
            if len(value_str) > 200:
                value_str = value_str[:200] + "…"
            lines.append(f"<code>{key}</code>: <code>{value_str}</code>")
        return lines
