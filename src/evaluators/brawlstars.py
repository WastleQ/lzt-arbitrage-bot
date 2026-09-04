from typing import Any

from evaluators.base import BaseEvaluator, ValuationResult


class BrawlStarsEvaluator(BaseEvaluator):
    def evaluate(self, raw_data: dict[str, Any]) -> ValuationResult | None:
        title = raw_data.get("title", "").lower()
        details: dict[str, Any] = {}
        base_price = 120.0

        # Оценка по кубкам
        if "к кубков" in title or "кубков" in title:
            base_price += 150.0
            details["trophies"] = "High trophies"
        
        if "гиперзаряд" in title or "hypercharge" in title:
            base_price += 100.0
            details["hypercharge"] = True

        if "лего" in title or "легендарк" in title:
            base_price += 80.0
            details["legendary_brawlers"] = True

        return ValuationResult(
            estimated_price=round(base_price, 2),
            confidence_score=0.75,
            details=details,
        )
