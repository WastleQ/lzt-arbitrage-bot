from unittest.mock import patch

from src.engine.arbitrage import ArbitrageEngine
from src.lzt.schemas import MarketItem


def make_item(
    title: str = "Minecraft Java Full Access Hypixel MVP+",
    price: float = 50.0,
    category: str = "minecraft",
    raw_data: dict | None = None,
    seller_username: str = "good_seller",
    seller_trust: int = 0,
) -> MarketItem:
    return MarketItem(
        item_id=1,
        category=category,
        title=title,
        price=price,
        currency="RUB",
        item_state="active",
        published_date=1234567890,
        seller_username=seller_username,
        seller_trust=seller_trust,
        item_url=f"https://lzt.market/{1}/",
        raw_data=raw_data or {},
    )


def test_arbitrage_engine_no_warnings():
    with patch("src.config.settings.min_profit_rub", 10.0), patch("src.config.settings.min_roi_percent", 5.0):
        engine = ArbitrageEngine()
        item = make_item(
            title="Minecraft Java Default",
            price=240.0,
            raw_data={
                "seller": {"trust": 999},
                "account_age_days": 100,
            },
            seller_trust=999,
        )
        result = engine.evaluate_item(item)
        assert result is not None
        assert result.get("warnings") == []


def test_price_drop_tracker():
    engine = ArbitrageEngine()
    item = make_item(
        title="Minecraft Java Full Access Hypixel MVP+",
        price=50.0,  # Огромная скидка от оценки ~175
        raw_data={
            "seller": {"trust": 999},
            "account_age_days": 100,
        },
        seller_trust=999,
    )
    result = engine.evaluate_item(item)
    assert result is not None
    assert result.get("price_drop_percent", 0.0) >= 25.0
    assert any("слив цены" in w.lower() for w in result["warnings"])


def test_arbitrage_engine_low_trust_warning():
    with patch("src.config.settings.min_seller_trust", 10):
        engine = ArbitrageEngine()
        item = make_item(
            raw_data={"seller": {"trust": 5}, "account_age_days": 100},
            seller_trust=5,
        )
        result = engine.evaluate_item(item)
        assert result is not None
        assert any("низкий рейтинг продавца" in w.lower() for w in result["warnings"])


def test_arbitrage_engine_young_account_warning():
    with patch("src.config.settings.min_account_age_days", 30):
        engine = ArbitrageEngine()
        item = make_item(
            raw_data={"seller": {"trust": 999}, "account_age_days": 5},
            seller_trust=999,
        )
        result = engine.evaluate_item(item)
        assert result is not None
        assert any("молодой аккаунт" in w.lower() for w in result["warnings"])


def test_arbitrage_engine_excluded_words_rejection():
    with patch("src.config.settings.exclude_words", "откат,бан"):
        engine = ArbitrageEngine()
        item = make_item(title="Minecraft Java (откат)")
        result = engine.evaluate_item(item)
        assert result is None


def test_arbitrage_engine_profit_and_roi_calculation():
    engine = ArbitrageEngine()
    item = make_item(
        title="Minecraft MVP+ Migrator 100 звёзд full access",
        price=200.0,
    )
    result = engine.evaluate_item(item)
    assert result is not None
    assert result["net_profit"] > 0
    assert result["resell_fee"] > 0
    assert result["roi"] > 0
    assert result["adjusted_roi"] <= result["roi"]


def test_arbitrage_engine_skip_low_profit():
    engine = ArbitrageEngine()
    item = make_item(
        title="Minecraft default",
        price=10000.0,
    )
    result = engine.evaluate_item(item)
    assert result is None


def test_arbitrage_engine_unknown_category():
    engine = ArbitrageEngine()
    item = make_item(category="unknown", title="x", price=10.0)
    assert engine.evaluate_item(item) is None


def test_arbitrage_engine_currency_warning():
    engine = ArbitrageEngine()
    item = MarketItem(
        item_id=1,
        category="minecraft",
        title="Minecraft MVP+",
        price=100.0,
        currency="USD",
        item_state="active",
        published_date=0,
        seller_username="u",
        item_url="",
        raw_data={},
    )
    result = engine.evaluate_item(item)
    assert result is not None
    assert any("Валюта" in w for w in result["warnings"])


def test_auto_buy_allowed_respects_max_price():
    with (
        patch("src.config.settings.auto_buy_enabled", True),
        patch("src.config.settings.max_auto_buy_price", 100.0),
    ):
        engine = ArbitrageEngine()
        item = make_item(
            title="Minecraft MVP+ Migrator 100 звёзд full access", price=500.0
        )
        result = engine.evaluate_item(item)
        assert result is not None
        allowed, reason = engine.auto_buy_allowed(result)
        assert not allowed
        assert reason and "лимит" in reason


def test_auto_buy_allowed_when_disabled():
    with patch("src.config.settings.auto_buy_enabled", False):
        engine = ArbitrageEngine()
        item = make_item(title="Minecraft MVP+ 50 звёзд", price=100.0)
        result = engine.evaluate_item(item)
        assert result is not None
        allowed, reason = engine.auto_buy_allowed(result)
        assert not allowed
        assert "Auto-Buy" in (reason or "")
