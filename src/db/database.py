import os

import aiosqlite

from config import settings


async def init_db() -> None:
    db_dir = os.path.dirname(settings.db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

    async with aiosqlite.connect(settings.db_path) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS seen_items (
                item_id INTEGER PRIMARY KEY,
                category TEXT NOT NULL,
                price REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER UNIQUE,
                category TEXT NOT NULL,
                title TEXT NOT NULL,
                buy_price REAL NOT NULL,
                estimated_price REAL NOT NULL,
                net_profit REAL NOT NULL,
                status TEXT NOT NULL,
                purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        await db.commit()


async def is_item_seen(item_id: int) -> bool:
    async with aiosqlite.connect(settings.db_path) as db, db.execute(
        "SELECT 1 FROM seen_items WHERE item_id = ?", (item_id,)
    ) as cursor:
        row = await cursor.fetchone()
        return row is not None


async def mark_item_seen(item_id: int, category: str, price: float) -> None:
    async with aiosqlite.connect(settings.db_path) as db:
        await db.execute(
            "INSERT OR IGNORE INTO seen_items (item_id, category, price) VALUES (?, ?, ?)",
            (item_id, category, price),
        )
        await db.commit()


async def record_trade(
    item_id: int,
    category: str,
    title: str,
    buy_price: float,
    estimated_price: float,
    net_profit: float,
    status: str,
) -> None:
    async with aiosqlite.connect(settings.db_path) as db:
        await db.execute(
            """
            OR IGNORE INSERT INTO trades (item_id, category, title, buy_price, estimated_price, net_profit, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (item_id, category, title, buy_price, estimated_price, net_profit, status),
        )
        await db.commit()
