from typing import Any

from config import settings
from evaluators.base import ValuationResult
from evaluators.brawlstars import BrawlStarsEvaluator
from evaluators.minecraft import MinecraftEvaluator
from evaluators.valorant import ValorantEvaluator
from lzt.schemas import MarketItem


class ArbitrageEngine:
    def __init__(self) -> None:
        self.evaluators = {
            "minecraft": MinecraftEvaluator(),
            "brawlstars": BrawlStarsEvaluator(),
            "valorant": ValorantEvaluator(),
        }

    def evaluate_item(self, item: MarketItem) -> dict[str, Any] | None:
        evaluator = self.evaluators.get(item.category)
        if not evaluator:
            return None

        valuation: ValuationResult | None = evaluator.evaluate(item.raw_data)
        if not valuation:
            return None

        # Расчет комиссий
        buy_price = item.price
        estimated_price = valuation.estimated_price

        # Комиссия на продажу на LZT (например 5%) + возможные накладные расходы
        resell_fee = estimated_price * (settings.lzt_resell_fee_percent / 100.0)
        net_estimated = estimated_price - resell_fee

        net_profit = net_estimated - buy_price
        roi = (net_profit / buy_price) * 100.0 if buy_price > 0 else 0.0

        if net_profit < settings.min_profit_rub or roi < settings.min_roi_percent:
            return None

        return {
            "item": item,
            "estimated_price": estimated_price,
            "net_profit": round(net_profit, 2),
            "roi": round(roi, 1),
            "details": valuation.details,
        }
