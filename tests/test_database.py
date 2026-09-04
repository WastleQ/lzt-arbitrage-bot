import os
import tempfile
from datetime import datetime, timedelta

import pytest
import pytest_asyncio

from src.db.database import (
    blacklist_item,
    db,
    get_setting,
    get_stats,
    init_db,
    is_blacklisted,
    is_item_seen,
    mark_item_seen,
    record_trade,
    set_setting,
)


@pytest_asyncio.fixture
async def temp_db():
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "test.db")
        original = db.path
        db.path = path
        db._initialized = False
        await init_db()
        yield path
        db.path = original
        db._initialized = False


@pytest.mark.asyncio
async def test_seen_items_cooldown_zero(temp_db):
    assert not await is_item_seen(1)
    await mark_item_seen(1, "minecraft", 100.0)
    assert await is_item_seen(1)


@pytest.mark.asyncio
async def test_seen_items_cooldown_blocks_recent(temp_db):
    db.path = temp_db
    db._initialized = False
    from src.config import settings

    original = settings.seen_cooldown_minutes
    settings.seen_cooldown_minutes = 60
    try:
        await mark_item_seen(7, "minecraft", 50.0)
        assert await is_item_seen(7)
    finally:
        settings.seen_cooldown_minutes = original


@pytest.mark.asyncio
async def test_blacklist(temp_db):
    assert not await is_blacklisted(99)
    await blacklist_item(99, reason="spam")
    assert await is_blacklisted(99)


@pytest.mark.asyncio
async def test_record_trade_and_stats(temp_db):
    await record_trade(1, "minecraft", "Acc1", 100.0, 200.0, 100.0, "bought_auto")
    await record_trade(2, "valorant", "Acc2", 300.0, 500.0, 200.0, "bought_manual")
    stats = await get_stats()
    assert stats["total_trades"] == 2
    assert stats["total_spent"] == 400.0
    assert stats["total_expected_profit"] == 300.0
    assert "bought_auto" in stats["by_status"]


@pytest.mark.asyncio
async def test_kv_roundtrip(temp_db):
    await set_setting("foo", {"a": 1})
    assert await get_setting("foo") == {"a": 1}
    assert await get_setting("missing", default="d") == "d"


@pytest.mark.asyncio
async def test_stats_since_filter(temp_db):
    await record_trade(1, "minecraft", "A", 10.0, 20.0, 10.0, "bought_auto")
    future = datetime.now() + timedelta(days=1)  # noqa: DTZ005
    stats = await get_stats(since=future)
    assert stats["total_trades"] == 0
