import re
from typing import Any

from src.config import CATEGORIES_CONFIG
from src.evaluators.base import BaseEvaluator, ValuationResult


class BrawlStarsEvaluator(BaseEvaluator):
    category = "brawlstars"

    def __init__(self) -> None:
        cfg = (CATEGORIES_CONFIG.get("categories") or {}).get("brawlstars") or {}
        self._base = float(cfg.get("base_price", 100.0))
        self._confidence = float(cfg.get("confidence", 0.82))
        self._weights: dict[str, float] = cfg.get("weights") or {}
        self._trophies_thresholds: list[dict[str, float]] = (
            cfg.get("trophies_thresholds") or []
        )

    def evaluate(self, raw_data: dict[str, Any]) -> ValuationResult | None:
        full_text = self.full_text(raw_data)
        details: dict[str, Any] = {}
        base_price = self._base

        api_trophies = raw_data.get("trophies") or raw_data.get("brawlstars_trophies")
        trophies = 0
        if api_trophies is not None:
            trophies = int(api_trophies)
            details["trophies"] = trophies
        else:
            trophies_match = re.search(
                r"(\d{1,2})[\s\.,]?k\s*кубк|(\d{4,6})\s*кубк", full_text
            )
            if trophies_match:
                if trophies_match.group(1):
                    trophies = int(trophies_match.group(1)) * 1000
                else:
                    trophies = int(trophies_match.group(2))
                details["trophies"] = trophies
            elif "к кубков" in full_text or "тыс кубков" in full_text:
                trophies = 15000
                details["trophies"] = trophies

        if trophies > 0:
            for thr in sorted(self._trophies_thresholds, key=lambda x: x["trophies"]):
                if trophies >= int(thr["trophies"]):
                    base_price += float(thr["bonus"])

        api_hc = raw_data.get("hypercharges_count") or raw_data.get("hypercharge_count")
        hc_count = 0
        if api_hc is not None:
            hc_count = int(api_hc)
            base_price += hc_count * float(self._weights.get("hypercharge_each", 40.0))
            details["hypercharges_count"] = hc_count
        else:
            hc_match = re.search(r"(\d+)\s*гипер", full_text)
            if hc_match:
                hc_count = int(hc_match.group(1))
                base_price += hc_count * float(self._weights.get("hypercharge_each", 40.0))
                details["hypercharges_count"] = hc_count
            elif "гиперзаряд" in full_text or "hypercharge" in full_text:
                base_price += 80.0
                details["hypercharge"] = True

        if any(
            w in full_text
            for w in ["star shelly", "звездная шелли", "шелли со звездой"]
        ):
            base_price += float(self._weights.get("star_shelly", 500.0))
            details["rare_skin"] = "Star Shelly"

        if "меха" in full_text or "mecha" in full_text:
            base_price += float(self._weights.get("mecha", 100.0))
            details["mecha_skins"] = True

        if "лего" in full_text or "легендарк" in full_text:
            base_price += float(self._weights.get("legendary", 90.0))
            details["legendary_brawlers"] = True

        return ValuationResult(
            estimated_price=round(base_price, 2),
            confidence_score=self._confidence,
            details=details,
        )
