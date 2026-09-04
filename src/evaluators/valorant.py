import re
from typing import Any

from src.config import CATEGORIES_CONFIG
from src.evaluators.base import BaseEvaluator, ValuationResult


class ValorantEvaluator(BaseEvaluator):
    category = "valorant"

    def __init__(self) -> None:
        cfg = (CATEGORIES_CONFIG.get("categories") or {}).get("valorant") or {}
        self._base = float(cfg.get("base_price", 300.0))
        self._confidence = float(cfg.get("confidence", 0.88))
        self._region_multipliers: dict[str, float] = cfg.get("region_multipliers") or {
            "EU": 1.4,
            "NA": 1.5,
            "TR": 0.8,
        }
        self._rank_bonuses: dict[str, float] = cfg.get("rank_bonuses") or {
            "radiant": 1000.0,
            "immortal": 600.0,
            "ascendant": 400.0,
            "diamond": 250.0,
            "plat": 150.0,
            "gold": 100.0,
        }
        self._knife_bonus = float(cfg.get("knife_bonus_each", 450.0))
        self._skin_bonus = float(cfg.get("premium_skin_bonus_each", 150.0))
        self._skins_thresholds: list[dict[str, float]] = (
            cfg.get("skins_count_thresholds") or []
        )

    def evaluate(self, raw_data: dict[str, Any]) -> ValuationResult | None:
        full_text = self.full_text(raw_data)
        details: dict[str, Any] = {}
        base_price = self._base

        region = "Other"
        if any(w in full_text for w in ["eu", "европа", "europe"]):
            region = "EU"
        elif any(w in full_text for w in ["na", "северная америка", "americas"]):
            region = "NA"
        elif any(w in full_text for w in ["tr", "турция", "turkey"]):
            region = "TR"
        details["region"] = region
        base_price *= float(self._region_multipliers.get(region, 1.0))

        rank_found = None
        for rank_name in self._rank_bonuses:
            if rank_name in full_text:
                rank_found = rank_name
                base_price += float(self._rank_bonuses[rank_name])
                details["rank"] = rank_name.capitalize()
                break
        if not rank_found:
            details["rank"] = "Unrated / Low"

        knives = [
            "karambit",
            "керамбит",
            "нож",
            "knife",
            "butterfly",
            "бабочка",
            "ruin",
            "kuronami",
            "champions",
        ]
        knife_count = sum(1 for k in knives if k in full_text)
        if knife_count > 0:
            base_price += knife_count * self._knife_bonus
            details["knives_detected"] = knife_count

        top_skins = [
            "kuronami",
            "reaper",
            "потрошитель",
            "prime",
            "прайм",
            "rgx",
            "glitchpop",
            "champions",
            "araxys",
            "chronovoid",
            "prelude",
            "жнец",
        ]
        skin_matches = sum(1 for s in top_skins if s in full_text)
        if skin_matches > 0:
            base_price += skin_matches * self._skin_bonus
            details["premium_skins_count"] = skin_matches

        skins_count_match = re.search(r"(\d+)\s*(?:скин|skins|винтовк)", full_text)
        if skins_count_match:
            count = int(skins_count_match.group(1))
            details["total_skins_mentioned"] = count
            for thr in sorted(self._skins_thresholds, key=lambda x: x["count"]):
                if count > int(thr["count"]):
                    base_price += float(thr["bonus"])

        return ValuationResult(
            estimated_price=round(base_price, 2),
            confidence_score=self._confidence,
            details=details,
        )
