from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ValuationResult:
    estimated_price: float
    confidence_score: float
    details: dict[str, Any] = field(default_factory=dict)


class BaseEvaluator(ABC):
    category: str = ""

    @abstractmethod
    def evaluate(self, raw_data: dict[str, Any]) -> ValuationResult | None:
        pass

    @staticmethod
    def full_text(raw_data: dict[str, Any]) -> str:
        title = (raw_data.get("title") or "").lower()
        description = (raw_data.get("description") or "").lower()
        return f"{title} {description}"

    @staticmethod
    def parse_banned(full_text: str, banned: list[str] | None = None) -> bool:
        keywords = banned or ["бан", "banned", "hypixel ban", "чс"]
        return any(w in full_text for w in keywords)
