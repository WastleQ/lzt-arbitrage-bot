from pathlib import Path
from typing import Any

import yaml
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from src import __version__


class Settings(BaseSettings):
    bot_token: str = "test_bot_token"
    admin_id: int = 123456
    lzt_api_token: str = "test_lzt_token"
    lzt_deposit_fee_percent: float = 2.0
    lzt_buy_fee_percent: float = 0.0
    lzt_resell_fee_percent: float = 5.0

    min_profit_rub: float = 100.0
    min_roi_percent: float = 25.0
    auto_buy_enabled: bool = False
    check_interval_seconds: float = 3.0

    min_seller_trust: int = 0
    min_account_age_days: int = 0
    exclude_words: str = "откат,бан,нет почты"

    db_path: str = "data/arbitrage.db"

    max_auto_buy_price: float = 0.0
    confirm_above_price: float = 0.0
    seen_cooldown_minutes: int = 30
    min_balance_alert: float = 100.0

    rate_limit_rps: float = 2.0
    rate_limit_burst: int = 5
    request_retries: int = 4
    request_backoff_base: float = 1.5

    log_level: str = "INFO"
    log_file: str = "data/bot.log"
    log_rotation: str = "10 MB"
    log_retention: str = "7 days"

    enabled_categories: str = "minecraft,brawlstars,valorant"
    categories_config_path: str = "categories.yaml"

    version: str = __version__

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_ignore_empty=True,
    )

    @field_validator("bot_token", "lzt_api_token")
    @classmethod
    def _validate_not_placeholder(cls, value: str, info: Any) -> str:
        bad = ("test_", "your_", "changeme")
        if any(value.lower().startswith(b) for b in bad) and not info.data.get(
            "_is_test"
        ):
            pass
        return value

    def enabled_category_list(self) -> list[str]:
        return [c.strip() for c in self.enabled_categories.split(",") if c.strip()]

    def excluded_word_list(self) -> list[str]:
        return [w.strip().lower() for w in self.exclude_words.split(",") if w.strip()]


settings = Settings()


def _load_categories_yaml() -> dict[str, Any]:
    path = Path(settings.categories_config_path)
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except yaml.YAMLError as exc:
        from loguru import logger

        logger.warning(f"Failed to parse {path}: {exc}")
        return {}
    if not isinstance(data, dict):
        return {}
    return data


CATEGORIES_CONFIG: dict[str, Any] = _load_categories_yaml()
