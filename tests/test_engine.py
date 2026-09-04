from unittest.mock import patch

from engine.arbitrage import ArbitrageEngine
from lzt.schemas import MarketItem


def make_item(
    title: str = "Minecraft Java Full Access Hypixel MVP+",
    price: float = 50.0,
    category: str = "minecraft",
    raw_data: dict | None = None,
    seller_username: str = "good_seller",
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
        raw_data=raw_data or {},
    )


def test_arbitrage_engine_no_warnings():
    """Test that no warnings are generated for a clean, high-trust item."""
    engine = ArbitrageEngine()
    item = make_item(
        raw_data={
            "seller": {"trust": 999},
            "account_age_days": 100,
        }
    )
    result = engine.evaluate_item(item)
    assert result is not None
    assert result.get("warnings") == []


def test_arbitrage_engine_low_trust_warning():
    """Test that a warning is generated when seller trust is too low."""
    with patch("config.settings.min_seller_trust", 10):
        engine = ArbitrageEngine()
        item = make_item(
            raw_data={
                "seller": {"trust": 5},
                "account_age_days": 100,
            }
        )
        result = engine.evaluate_item(item)
        assert result is not None
        assert any("низкий рейтинг продавца" in w.lower() for w in result.get("warnings", []))


def test_arbitrage_engine_young_account_warning():
    """Test that a warning is generated when account age is too young."""
    with patch("config.settings.min_account_age_days", 30):
        engine = ArbitrageEngine()
        item = make_item(
            raw_data={
                "seller": {"trust": 999},
                "account_age_days": 5,
            }
        )
        result = engine.evaluate_item(item)
        assert result is not None
        assert any("молодой аккаунт" in w.lower() for w in result.get("warnings", []))


def test_arbitrage_engine_excluded_words_warning():
    """Test that a warning is generated when title contains excluded words."""
    with patch("config.settings.exclude_words", "откат,бан"):
        engine = ArbitrageEngine()
        item = make_item(title="Minecraft Java (откат)")
        result = engine.evaluate_item(item)
        assert result is not None
        assert any("откат" in w for w in result.get("warnings", []))
