from typing import Any

from src.config import settings
from src.evaluators.base import ValuationResult
from src.evaluators.brawlstars import BrawlStarsEvaluator
from src.evaluators.minecraft import MinecraftEvaluator
from src.evaluators.valorant import ValorantEvaluator
from src.lzt.schemas import MarketItem
from src.utils.logger import logger


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


class ArbitrageEngine:
    def __init__(self) -> None:
        self.evaluators: dict[str, Any] = {
            "minecraft": MinecraftEvaluator(),
            "brawlstars": BrawlStarsEvaluator(),
            "valorant": ValorantEvaluator(),
        }
        self.exclude_words = settings.excluded_word_list()

    def get_evaluator(self, category: str) -> Any | None:
        return self.evaluators.get(category)

    def evaluate_item(self, item: MarketItem) -> dict[str, Any] | None:
        evaluator = self.get_evaluator(item.category)
        if not evaluator:
            return None

        self.exclude_words = settings.excluded_word_list()
        title_lower = item.title.lower()
        merged: dict[str, Any] = dict(item.raw_data)
        merged.setdefault("title", item.title)
        merged.setdefault("description", merged.get("description", ""))
        desc_lower = merged.get("description", "").lower()

        for word in self.exclude_words:
            if word and (word in title_lower or word in desc_lower):
                logger.debug(f"Skip item {item.item_id}: matched exclude word '{word}'")
                return None

        if settings.require_full_access:
            mail_access = item.raw_data.get("mail_access")
            if mail_access is False or str(mail_access).lower() in ("0", "false", "no"):
                logger.debug(f"Skip item {item.item_id}: mail_access is False")
                return None

            no_access_phrases = [
                "без почты",
                "почта не меняется",
                "без смены почты",
                "временная почта",
                "авторег без доступа",
            ]
            full_text = f"{title_lower} {desc_lower}"
            if any(p in full_text for p in no_access_phrases):
                logger.debug(f"Skip item {item.item_id}: lacks full access / email change")
                return None

        valuation: ValuationResult | None = evaluator.evaluate(merged)
        if not valuation:
            return None

        buy_price = item.price
        estimated_price = valuation.estimated_price

        resell_fee = estimated_price * (settings.lzt_resell_fee_percent / 100.0)
        net_estimated = estimated_price - resell_fee
        net_profit = net_estimated - buy_price
        roi = (net_profit / buy_price) * 100.0 if buy_price > 0 else 0.0

        confidence_penalty = (1.0 - valuation.confidence_score) * 100.0
        adjusted_roi = roi - confidence_penalty
        if (
            adjusted_roi < settings.min_roi_percent
            or net_profit < settings.min_profit_rub
        ):
            logger.debug(
                f"Skip item {item.item_id}: net_profit={net_profit:.2f} roi={roi:.1f}% "
                f"adj_roi={adjusted_roi:.1f}% conf={valuation.confidence_score}"
            )
            return None

        warnings: list[str] = self._collect_warnings(item, valuation)
        price_drop_percent = 0.0
        if estimated_price > 0 and buy_price < estimated_price:
            drop = ((estimated_price - buy_price) / estimated_price) * 100.0
            if drop >= 25.0:
                price_drop_percent = round(drop, 1)
                warnings.insert(0, f"🔥 <b>Слив цены!</b> Дисконт {price_drop_percent}% ниже рынка")

        result: dict[str, Any] = {
            "item": item,
            "valuation": valuation,
            "estimated_price": estimated_price,
            "resell_fee": round(resell_fee, 2),
            "net_profit": round(net_profit, 2),
            "roi": round(roi, 1),
            "adjusted_roi": round(adjusted_roi, 1),
            "confidence": valuation.confidence_score,
            "details": valuation.details,
            "warnings": warnings,
            "price_drop_percent": price_drop_percent,
        }
        return result

    def _collect_warnings(
        self, item: MarketItem, valuation: ValuationResult
    ) -> list[str]:
        warnings: list[str] = []

        seller = item.raw_data.get("seller") or {}
        seller_trust = _safe_int(seller.get("trust", item.seller_trust), 0)
        if settings.min_seller_trust > 0 and seller_trust < settings.min_seller_trust:
            warnings.append(
                f"⚠️ Низкий рейтинг продавца ({seller_trust} < {settings.min_seller_trust})"
            )

        account_age = _safe_int(item.raw_data.get("account_age_days", 0), 0)
        if (
            settings.min_account_age_days > 0
            and 0 < account_age < settings.min_account_age_days
        ):
            warnings.append(
                f"⚠️ Молодой аккаунт ({account_age} дн. < {settings.min_account_age_days} дн.)"
            )

        if item.raw_data.get("account_age_days") in (None, 0):
            warnings.append("⚠️ Возраст аккаунта неизвестен")

        title_lower = item.title.lower()
        found_excluded = [w for w in self.exclude_words if w in title_lower]
        if found_excluded:
            warnings.append(f"🚫 Подозрительные слова: {', '.join(found_excluded)}")

        if not item.item_url:
            warnings.append("⚠️ Нет прямой ссылки на лот")

        if item.currency and item.currency != "RUB":
            warnings.append(
                f"⚠️ Валюта: {item.currency} (возможны потери на конвертации)"
            )

        if valuation.confidence_score < 0.7:
            warnings.append(
                f"⚠️ Низкая уверенность оценки ({int(valuation.confidence_score * 100)}%)"
            )

        return warnings

    def auto_buy_allowed(self, result: dict[str, Any]) -> tuple[bool, str | None]:
        if not settings.auto_buy_enabled:
            return False, "Auto-Buy выключен"
        item: MarketItem = result["item"]
        if settings.max_auto_buy_price > 0 and item.price > settings.max_auto_buy_price:
            return (
                False,
                f"Цена {item.price}₽ превышает лимит {settings.max_auto_buy_price}₽",
            )
        if (
            settings.confirm_above_price > 0
            and item.price > settings.confirm_above_price
        ):
            return (
                False,
                f"Цена {item.price}₽ > {settings.confirm_above_price}₽ — нужно подтверждение",
            )
        return True, None

    async def adaptive_min_roi(self, db_stats: dict[str, Any]) -> float:
        base = float(settings.min_roi_percent)
        realized = db_stats.get("realized_roi")
        if realized is None:
            return base
        if realized < base - 5:
            return min(base + 10.0, 80.0)
        if realized > base + 15:
            return max(base - 5.0, 10.0)
        return base
