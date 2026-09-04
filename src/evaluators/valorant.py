from typing import Any

from evaluators.base import BaseEvaluator, ValuationResult


class ValorantEvaluator(BaseEvaluator):
    def evaluate(self, raw_data: dict[str, Any]) -> ValuationResult | None:
        title = raw_data.get("title", "").lower()
        details: dict[str, Any] = {}
        base_price = 350.0

        # Оценка скинов и ножей
        if "нож" in title or "knife" in title or "karambit" in title:
            base_price += 600.0
            details["has_knife"] = True

        if "vandal" in title or "prime" in title or "reaver" in title or "kuronami" in title:
            base_price += 400.0
            details["premium_skins"] = True

        if "eu" in title or "европа" in title:
            base_price *= 1.2
            details["region"] = "EU"
        else:
            details["region"] = "Other"

        return ValuationResult(
            estimated_price=round(base_price, 2),
            confidence_score=0.80,
            details=details,
        )
