import re
from typing import Any

from evaluators.base import BaseEvaluator, ValuationResult


class BrawlStarsEvaluator(BaseEvaluator):
    def evaluate(self, raw_data: dict[str, Any]) -> ValuationResult | None:
        title = raw_data.get("title", "").lower()
        description = raw_data.get("description", "").lower()
        full_text = f"{title} {description}"
        details: dict[str, Any] = {}

        base_price = 100.0

        # 1. Парсим кубки (например: "30к кубков", "25000 trophies", "35k")
        trophies_match = re.search(r"(\d{1,2})[\s\.,]?k\s*кубк|(\d{4,6})\s*кубк", full_text)
        if trophies_match:
            if trophies_match.group(1):
                trophies = int(trophies_match.group(1)) * 1000
            else:
                trophies = int(trophies_match.group(2))
            details["trophies"] = trophies
            if trophies > 40000:
                base_price += 400.0
            elif trophies > 25000:
                base_price += 250.0
            elif trophies > 15000:
                base_price += 120.0
        else:
            if "к кубков" in full_text or "тыс кубков" in full_text:
                base_price += 150.0

        # 2. Гиперзаряды (Hypercharge)
        hc_match = re.search(r"(\d+)\s*гипер", full_text)
        if hc_match:
            hc_count = int(hc_match.group(1))
            base_price += hc_count * 40.0
            details["hypercharges_count"] = hc_count
        elif "гиперзаряд" in full_text or "hypercharge" in full_text:
            base_price += 80.0
            details["hypercharge"] = True

        # 3. Редкие скины (Star Shelly / Звездная Шелли, Mecha)
        if any(w in full_text for w in ["star shelly", "звездная шелли", "шелли со звездой"]):
            base_price += 500.0  # Очень редкий скин за бравл токен 2018
            details["rare_skin"] = "Star Shelly"

        if "меха" in full_text or "mecha" in full_text:
            base_price += 100.0
            details["mecha_skins"] = True

        # 4. Легендарные бравлеры
        if "лего" in full_text or "легендарк" in full_text:
            base_price += 90.0
            details["legendary_brawlers"] = True

        return ValuationResult(
            estimated_price=round(base_price, 2),
            confidence_score=0.82,
            details=details,
        )
