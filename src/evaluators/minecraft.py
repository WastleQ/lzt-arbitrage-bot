from typing import Any

from evaluators.base import BaseEvaluator, ValuationResult


class MinecraftEvaluator(BaseEvaluator):
    def evaluate(self, raw_data: dict[str, Any]) -> ValuationResult | None:
        title = raw_data.get("title", "").lower()
        details: dict[str, Any] = {}
        base_price = 200.0  # Базовая стоимость чистой майнкрафт лицухи

        # Оценка по рангам Hypixel в названии или параметрах
        if "mvp+" in title or "mvpplus" in title:
            base_price += 400.0
            details["rank"] = "Hypixel MVP+"
        elif "mvp" in title:
            base_price += 250.0
            details["rank"] = "Hypixel MVP"
        elif "vip+" in title:
            base_price += 150.0
            details["rank"] = "Hypixel VIP+"
        elif "vip" in title:
            base_price += 80.0
            details["rank"] = "Hypixel VIP"
        else:
            details["rank"] = "Default"

        # Проверка на наличие почты / полный доступ
        if "full access" in title or " родная" in title or raw_data.get("mail_access"):
            base_price *= 1.3
            details["full_access"] = True
        else:
            details["full_access"] = False

        return ValuationResult(
            estimated_price=round(base_price, 2),
            confidence_score=0.85,
            details=details,
        )
