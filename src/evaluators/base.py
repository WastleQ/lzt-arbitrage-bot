from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ValuationResult:
    estimated_price: float
    confidence_score: float  # 0.0 to 1.0
    details: dict[str, Any]


class BaseEvaluator(ABC):
    @abstractmethod
    def evaluate(self, raw_data: dict[str, Any]) -> ValuationResult | None:
        pass
