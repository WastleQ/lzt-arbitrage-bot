import asyncio
import statistics
from pathlib import Path
from typing import Any

import yaml

from src.lzt.client import LZTClient
from src.utils.logger import logger


class MarketCalibrator:
    def __init__(self, client: LZTClient | None = None) -> None:
        self.client = client or LZTClient()

    async def calibrate_category(self, category: str) -> dict[str, Any]:
        """Собирает лоты с LZT Market и вычисляет актуальные медианные цены."""
        items = await self.client.search_items(category, params={"limit": 50})
        if not items:
            logger.warning(f"No items fetched for calibration of {category}")
            return {}

        prices = [item.price for item in items if item.price > 0]
        if not prices:
            return {}

        median_price = statistics.median(prices)
        
        analysis: dict[str, Any] = {
            "median_price": round(median_price, 2),
            "sample_size": len(prices),
        }

        if category == "minecraft":
            mvp_plus_prices = [
                i.price for i in items if "mvp+" in i.title.lower() or "mvpplus" in i.title.lower()
            ]
            if mvp_plus_prices:
                analysis["mvp_plus_avg"] = round(statistics.median(mvp_plus_prices), 2)
        elif category == "brawlstars":
            high_trophy_prices = [
                i.price for i in items if "кубк" in i.title.lower() or "к" in i.title.lower()
            ]
            if high_trophy_prices:
                analysis["high_trophy_avg"] = round(statistics.median(high_trophy_prices), 2)
        elif category == "valorant":
            knife_prices = [
                i.price for i in items if any(w in i.title.lower() for w in ["нож", "knife", "karambit"])
            ]
            if knife_prices:
                analysis["knife_avg"] = round(statistics.median(knife_prices), 2)

        return analysis

    async def calibrate_and_update_yaml(self, yaml_path: str = "categories.yaml") -> dict[str, Any]:
        path = Path(yaml_path)
        if not path.exists():
            logger.error(f"Config yaml not found at {yaml_path}")
            return {"status": "error", "message": "categories.yaml not found"}

        def _load_yaml() -> dict[str, Any]:
            with open(path, encoding="utf-8") as f:
                return yaml.safe_load(f) or {}

        data = await asyncio.to_thread(_load_yaml)

        categories = data.get("categories", {})
        report: dict[str, Any] = {}

        for cat in ["minecraft", "brawlstars", "valorant"]:
            calib = await self.calibrate_category(cat)
            if not calib:
                continue
            report[cat] = calib
            
            median = calib.get("median_price", 0)
            if median > 0 and cat in categories:
                suggested_base = round(median * 0.75, 2)
                categories[cat]["base_price"] = suggested_base
                logger.info(f"Calibrated {cat}: median market={median}₽, new base_price={suggested_base}₽")

                if cat == "minecraft" and "mvp_plus_avg" in calib:
                    base = categories[cat]["base_price"]
                    mvp_bonus = max(50.0, calib["mvp_plus_avg"] - base)
                    categories[cat]["weights"]["mvp_plus"] = round(mvp_bonus, 2)
                elif cat == "valorant" and "knife_avg" in calib:
                    base = categories[cat]["base_price"]
                    knife_bonus = max(100.0, calib["knife_avg"] - base)
                    categories[cat]["knife_bonus_each"] = round(knife_bonus, 2)

        data["categories"] = categories

        def _save_yaml(d: dict[str, Any]) -> None:
            with open(path, "w", encoding="utf-8") as f:
                yaml.safe_dump(d, f, allow_unicode=True, sort_keys=False)

        await asyncio.to_thread(_save_yaml, data)

        return {"status": "success", "report": report}
