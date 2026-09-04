import re
from typing import Any

from evaluators.base import BaseEvaluator, ValuationResult


class MinecraftEvaluator(BaseEvaluator):
    def evaluate(self, raw_data: dict[str, Any]) -> ValuationResult | None:
        title = raw_data.get("title", "").lower()
        description = raw_data.get("description", "").lower()
        full_text = f"{title} {description}"
        details: dict[str, Any] = {}

        # Проверка на баны (если аккаунт в бане на Hypixel, он почти ничего не стоит)
        if any(w in full_text for w in ["бан", "banned", "hypixel ban", "чс"]):
            return None  # Пропускаем забаненные аккаунты

        base_price = 250.0  # Базовая стоимость живой лицензии с почтой

        # 1. Оценка отлеги (Tenure / Inactivity) по дням если есть в пропсах
        # LZT часто передает отлегу в properties или заголовке
        days_inactive = raw_data.get("days_inactive", 0)
        if days_inactive > 30:
            base_price += 50.0
            details["tenure_days"] = days_inactive

        # 2. Оценка Hypixel рангов
        if any(w in full_text for w in ["mvp+", "mvpplus", "mvp +"]):
            base_price += 450.0
            details["rank"] = "Hypixel MVP+"
        elif "mvp" in full_text:
            base_price += 280.0
            details["rank"] = "Hypixel MVP"
        elif "vip+" in full_text or "vip +" in full_text:
            base_price += 160.0
            details["rank"] = "Hypixel VIP+"
        elif "vip" in full_text:
            base_price += 90.0
            details["rank"] = "Hypixel VIP"
        else:
            details["rank"] = "Default"

        # 3. Парсинг звезд Bedwars (например: "150 звёзд", "200 star", "bw 300")
        bw_stars_match = re.search(r"(\d+)\s*(?:зв[её]зд|stars|bw)", full_text)
        if bw_stars_match:
            stars = int(bw_stars_match.group(1))
            details["bedwars_stars"] = stars
            if stars > 300:
                base_price += 400.0
            elif stars > 150:
                base_price += 250.0
            elif stars > 50:
                base_price += 100.0

        # 4. Плащи (Migrator, OptiFine, Minecon)
        if "migrator" in full_text:
            base_price += 150.0
            details["cape"] = "Migrator Cape"
        if "minecon" in full_text:
            base_price += 2000.0  # Minecon плащи очень редкие и дорогие
            details["cape"] = "Minecon Cape"
        if "optifine" in full_text:
            base_price += 100.0
            details["cape"] = "OptiFine Cape"

        # 5. Полный доступ / почта
        if any(w in full_text for w in ["full access", "родная почта", "авторег", "fa"]):
            base_price *= 1.25
            details["full_access"] = True
        else:
            details["full_access"] = False

        return ValuationResult(
            estimated_price=round(base_price, 2),
            confidence_score=0.90,
            details=details,
        )
