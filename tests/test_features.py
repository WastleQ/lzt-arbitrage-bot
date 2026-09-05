from src.config import settings
from src.engine.arbitrage import ArbitrageEngine
from src.lzt.schemas import MarketItem


def test_exclude_words_filtering():
    engine = ArbitrageEngine()
    settings.exclude_words = "бан, восстановлен"
    
    item = MarketItem(
        item_id=123,
        category="minecraft",
        title="Minecraft Java Account [Восстановлен]",
        price=100.0,
        currency="RUB",
        item_state="active",
        published_date=1234567890,
        seller_username="test_seller",
        seller_trust=5,
        item_url="https://lzt.market/123/",
        raw_data={}
    )

    result = engine.evaluate_item(item)
    assert result is None
