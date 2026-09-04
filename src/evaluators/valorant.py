import re
from typing import Any

from evaluators.base import BaseEvaluator, ValuationResult


class ValorantEvaluator(BaseEvaluator):
    def evaluate(self, raw_data: dict[str, Any]) -> ValuationResult | None:
        title = raw_data.get("title", "").lower()
        description = raw_data.get("description", "").lower()
        full_text = f"{title} {description}"
        details: dict[str, Any] = {}

        # Базовая цена для Valorant аккаунта
        base_price = 300.0

        # 1. Регион (EU и NA самые дорогие и ликвидные, TR/RU дешевле)
        if any(w in full_text for w in ["eu", "европа", "europe"]):
            base_price *= 1.4
            details["region"] = "EU"
        elif any(w in full_text for w in ["na", "северная америка", "americas"]):
            base_price *= 1.5
            details["region"] = "NA"
        elif any(w in full_text for w in ["tr", "турция", "turkey"]):
            base_price *= 0.8
            details["region"] = "TR"
        else:
            details["region"] = "Other"

        # 2. Оценка рангов
        ranks = {
            "radiant": 1000.0,
            "immortal": 600.0,
            "ascendant": 400.0,
            "diamond": 250.0,
            "plat": 150.0,
            "gold": 100.0,
        }
        found_rank = False
        for rank_name, bonus in ranks.items():
            if rank_name in full_text:
                base_price += bonus
                details["rank"] = rank_name.capitalize()
                found_rank = True
                break
        if not found_rank:
            details["rank"] = "Unrated / Low"

        # 3. Премиальные ножи (Melee skins)
        knives = ["karambit", "керамбит", "нож", "knife", "butterfly", "бабочка", "ruin", "kuronami", "champions"]
        knife_count = sum(1 for k in knives if k in full_text)
        if knife_count > 0:
            base_price += knife_count * 450.0
            details["knives_detected"] = knife_count

        # 4. Топовые скины на оружие (Vandal / Phantom / Operator)
        top_skins = ["kuronami", "reaper", "потрошитель", "prime", "прайм", "rgx", "glitchpop", "champions", "araxys", "chronovoid", "prelude", "жнец"]
        skin_matches = sum(1 for s in top_skins if s in full_text)
        if skin_matches > 0:
            base_price += skin_matches * 150.0
            details["premium_skins_count"] = skin_matches

        # 5. Количество скинов (парсим цифры перед "скин" или "skins")
        skins_count_match = re.search(r"(\d+)\s*(?:скин|skins|винтовк)", full_text)
        if skins_count_match:
            count = int(skins_count_match.group(1))
            details["total_skins_mentioned"] = count
            if count > 50:
                base_price += 500.0
            elif count > 20:
                base_price += 250.0

        return ValuationResult(
            estimated_price=round(base_price, 2),
            confidence_score=0.88,
            details=details,
        )
