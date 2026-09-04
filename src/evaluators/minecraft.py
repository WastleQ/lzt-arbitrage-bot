import re
from typing import Any

from src.config import CATEGORIES_CONFIG
from src.evaluators.base import BaseEvaluator, ValuationResult


class MinecraftEvaluator(BaseEvaluator):
    category = "minecraft"

    def __init__(self) -> None:
        cfg = (CATEGORIES_CONFIG.get("categories") or {}).get("minecraft") or {}
        self._base = float(cfg.get("base_price", 250.0))
        self._confidence = float(cfg.get("confidence", 0.90))
        self._weights: dict[str, float] = cfg.get("weights") or {}
        self._bw_thresholds: list[dict[str, float]] = (
            cfg.get("bedwars_thresholds") or []
        )
        self._full_access_mult = float(
            self._weights.get("full_access_multiplier", 1.25)
        )
        self._tenure_per_day = float(self._weights.get("tenure_per_day", 1.66))

    def evaluate(self, raw_data: dict[str, Any]) -> ValuationResult | None:
        full_text = self.full_text(raw_data)
        if self.parse_banned(full_text):
            return None

        details: dict[str, Any] = {}
        base_price = self._base

        days_inactive = int(raw_data.get("days_inactive", 0) or 0)
        if days_inactive > 30:
            base_price += min(days_inactive, 365) * self._tenure_per_day
            details["tenure_days"] = days_inactive

        if any(w in full_text for w in ["mvp+", "mvpplus", "mvp +"]):
            base_price += float(self._weights.get("mvp_plus", 450.0))
            details["rank"] = "Hypixel MVP+"
        elif "mvp" in full_text:
            base_price += float(self._weights.get("mvp", 280.0))
            details["rank"] = "Hypixel MVP"
        elif "vip+" in full_text or "vip +" in full_text:
            base_price += float(self._weights.get("vip_plus", 160.0))
            details["rank"] = "Hypixel VIP+"
        elif "vip" in full_text:
            base_price += float(self._weights.get("vip", 90.0))
            details["rank"] = "Hypixel VIP"
        else:
            details["rank"] = "Default"

        bw_stars_match = re.search(r"(\d+)\s*(?:зв[её]зд|stars|bw)", full_text)
        if bw_stars_match:
            stars = int(bw_stars_match.group(1))
            details["bedwars_stars"] = stars
            for thr in sorted(self._bw_thresholds, key=lambda x: x["stars"]):
                if stars > int(thr["stars"]):
                    base_price += float(thr["bonus"])

        capes_found: list[str] = []
        if "minecon" in full_text:
            base_price += float(self._weights.get("minecon_cape", 2000.0))
            capes_found.append("Minecon")
        if "migrator" in full_text:
            base_price += float(self._weights.get("migrator_cape", 150.0))
            capes_found.append("Migrator")
        if "optifine" in full_text:
            base_price += float(self._weights.get("optifine_cape", 100.0))
            capes_found.append("OptiFine")
        if capes_found:
            details["capes"] = capes_found

        full_access = any(
            w in full_text for w in ["full access", "родная почта", "авторег", "fa"]
        )
        details["full_access"] = full_access
        if full_access:
            base_price *= self._full_access_mult

        return ValuationResult(
            estimated_price=round(base_price, 2),
            confidence_score=self._confidence,
            details=details,
        )
