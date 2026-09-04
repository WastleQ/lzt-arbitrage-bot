import pytest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

from src.bot.formatters import format_balance, format_deal_card, format_stats
from src.bot.states import SettingsStates
from src.lzt.schemas import MarketItem


def _item(**overrides) -> MarketItem:
    base: dict = {
        "item_id": 42,
        "category": "minecraft",
        "title": "Minecraft Java MVP+ Minecon migrator 200 звёзд full access",
        "price": 300.0,
        "currency": "RUB",
        "item_state": "active",
        "published_date": 0,
        "seller_username": "top_seller",
        "seller_trust": 999,
        "item_url": "https://lzt.market/42/",
        "raw_data": {
            "seller": {"username": "top_seller", "trust": 999},
            "account_age_days": 365,
        },
    }
    base.update(overrides)
    return MarketItem(**base)


def test_format_deal_card_contains_essential_sections():
    from src.lzt.client import LZTClient
    from src.utils.rate_limiter import AsyncRateLimiter

    client = LZTClient(
        api_token="t", session=None, rate_limiter=AsyncRateLimiter(100, 100)
    )
    from src.bot.formatters import set_lzt_client

    set_lzt_client(client)

    item = _item()
    result = {
        "item": item,
        "estimated_price": 4500.0,
        "resell_fee": 225.0,
        "net_profit": 4000.0,
        "roi": 1300.0,
        "adjusted_roi": 1290.0,
        "confidence": 0.9,
        "details": {
            "rank": "Hypixel MVP+",
            "bedwars_stars": 200,
            "capes": ["Minecon", "Migrator"],
            "full_access": True,
        },
        "warnings": [],
    }
    text = format_deal_card(result)
    assert "MVP+" in text
    assert "Minecon" in text
    assert "Migrator" in text
    assert "https://lzt.market/42/" in text
    assert "top_seller" in text
    assert "Full Access" in text


def test_format_deal_card_includes_warnings():
    from src.lzt.client import LZTClient
    from src.utils.rate_limiter import AsyncRateLimiter

    client = LZTClient(
        api_token="t", session=None, rate_limiter=AsyncRateLimiter(100, 100)
    )
    from src.bot.formatters import set_lzt_client

    set_lzt_client(client)

    item = _item()
    result = {
        "item": item,
        "estimated_price": 1000.0,
        "resell_fee": 50.0,
        "net_profit": 700.0,
        "roi": 200.0,
        "adjusted_roi": 195.0,
        "confidence": 0.85,
        "details": {"rank": "Hypixel VIP"},
        "warnings": ["⚠️ Пример предупреждения"],
    }
    text = format_deal_card(result)
    assert "Пример предупреждения" in text


def test_format_balance_handles_none():
    assert "Не удалось" in format_balance(None)
    out = format_balance({"balance": 10.0, "hold": 2.0})
    assert "10" in out and "2" in out


def test_format_stats_renders():
    text = format_stats(
        {
            "total_trades": 5,
            "total_spent": 1000.0,
            "total_expected_profit": 500.0,
            "by_status": {"bought_auto": 3, "bought_manual": 2},
            "by_category": [{"category": "minecraft", "cnt": 5, "profit": 500.0}],
        }
    )
    assert "5" in text
    assert "minecraft" in text


@pytest.mark.asyncio
async def test_settings_state_storage_roundtrip():
    storage = MemoryStorage()
    state = FSMContext(storage=storage, key="user:1")
    await state.set_state(SettingsStates.waiting_profit)
    assert await state.get_state() == SettingsStates.waiting_profit.state
    await state.clear()
    assert await state.get_state() is None
