from pydantic_settings import BaseSettings, SettingsConfigDict


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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_ignore_empty=True
    )


settings = Settings()
