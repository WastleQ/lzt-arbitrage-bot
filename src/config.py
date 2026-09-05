from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict

from src import __version__

# Ключи, которые разрешено менять в рантайме через /settings и хранить в settings_kv.
# Эти поля pydantic-settings не перечитывает из env (они динамические).
RUNTIME_MUTABLE_KEYS: frozenset[str] = frozenset(
    {
        "min_profit_rub",
        "min_roi_percent",
        "auto_buy_enabled",
        "auto_relist_enabled",
        "relist_markup_percent",
        "min_seller_trust",
        "min_account_age_days",
        "exclude_words",
        "max_auto_buy_price",
        "confirm_above_price",
        "seen_cooldown_minutes",
        "min_balance_alert",
        "check_interval_seconds",
        "enabled_categories",
    }
)

# Ключи, которые НЕЛЬЗЯ менять из бота (секреты, infra, логирование).
IMMUTABLE_KEYS: frozenset[str] = frozenset(
    {
        "bot_token",
        "admin_id",
        "lzt_api_token",
        "db_path",
        "log_level",
        "log_file",
        "log_rotation",
        "log_retention",
        "rate_limit_rps",
        "rate_limit_burst",
        "request_retries",
        "request_backoff_base",
        "categories_config_path",
        "version",
    }
)


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
    auto_relist_enabled: bool = False
    relist_markup_percent: float = 30.0
    check_interval_seconds: float = 3.0

    min_seller_trust: int = 0
    min_account_age_days: int = 0
    exclude_words: str = "откат,бан,нет почты"

    db_path: str = "data/arbitrage.db"

    max_auto_buy_price: float = 0.0
    confirm_above_price: float = 0.0
    seen_cooldown_minutes: int = 30
    min_balance_alert: float = 100.0

    proxy_url: str | None = None
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

    def enabled_category_list(self) -> list[str]:
        return [c.strip() for c in self.enabled_categories.split(",") if c.strip()]

    def excluded_word_list(self) -> list[str]:
        return [w.strip().lower() for w in self.exclude_words.split(",") if w.strip()]

    def update(self, key: str, value: Any) -> None:
        """Безопасно обновляет runtime-mutable поле и валидирует через pydantic."""
        if key not in RUNTIME_MUTABLE_KEYS:
            raise ValueError(f"Setting {key!r} is not runtime-mutable")
        coerced = self.__class__.model_validate({**self.model_dump(), key: value})
        setattr(self, key, getattr(coerced, key))

    def apply_overrides(self, overrides: dict[str, Any]) -> None:
        """Применяет dict переопределений (например, загруженный из settings_kv)."""
        if not overrides:
            return
        filtered = {k: v for k, v in overrides.items() if k in RUNTIME_MUTABLE_KEYS}
        if not filtered:
            return
        coerced = self.__class__.model_validate({**self.model_dump(), **filtered})
        for key in filtered:
            setattr(self, key, getattr(coerced, key))

    def runtime_snapshot(self) -> dict[str, Any]:
        """Снимок runtime-mutable полей для сохранения в БД."""
        return {k: getattr(self, k) for k in RUNTIME_MUTABLE_KEYS}


settings = Settings()


def reload_settings() -> Settings:
    """Перезагружает settings из env (используется в тестах)."""
    global settings
    settings = Settings()
    return settings


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
