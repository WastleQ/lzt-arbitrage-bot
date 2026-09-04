import json
import os
from datetime import datetime
from typing import Any

import aiosqlite

from src.config import settings


class Database:
    def __init__(self, path: str | None = None) -> None:
        self.path = path or settings.db_path
        self._initialized = False

    async def init(self) -> None:
        if self._initialized:
            return
        db_dir = os.path.dirname(self.path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

        async with aiosqlite.connect(self.path) as db:
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
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS blacklist (
                    item_id INTEGER PRIMARY KEY,
                    reason TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS settings_kv (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            await db.commit()
        self._initialized = True

    async def is_seen(self, item_id: int) -> bool:
        cooldown_min = settings.seen_cooldown_minutes
        if cooldown_min <= 0:
            async with (
                aiosqlite.connect(self.path) as db,
                db.execute(
                    "SELECT 1 FROM seen_items WHERE item_id = ?", (item_id,)
                ) as cur,
            ):
                return (await cur.fetchone()) is not None

        async with (
            aiosqlite.connect(self.path) as db,
            db.execute(
                """
            SELECT 1 FROM seen_items
            WHERE item_id = ?
              AND datetime(created_at, '+' || ? || ' minutes') > datetime('now')
            """,
                (item_id, cooldown_min),
            ) as cur,
        ):
            return (await cur.fetchone()) is not None

    async def mark_seen(self, item_id: int, category: str, price: float) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "INSERT OR IGNORE INTO seen_items (item_id, category, price) VALUES (?, ?, ?)",
                (item_id, category, price),
            )
            await db.commit()

    async def is_blacklisted(self, item_id: int) -> bool:
        async with (
            aiosqlite.connect(self.path) as db,
            db.execute("SELECT 1 FROM blacklist WHERE item_id = ?", (item_id,)) as cur,
        ):
            return (await cur.fetchone()) is not None

    async def blacklist_item(self, item_id: int, reason: str = "") -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO blacklist (item_id, reason) VALUES (?, ?)",
                (item_id, reason),
            )
            await db.commit()

    async def record_trade(
        self,
        item_id: int,
        category: str,
        title: str,
        buy_price: float,
        estimated_price: float,
        net_profit: float,
        status: str,
    ) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """
                INSERT OR IGNORE INTO trades
                    (item_id, category, title, buy_price, estimated_price, net_profit, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item_id,
                    category,
                    title,
                    buy_price,
                    estimated_price,
                    net_profit,
                    status,
                ),
            )
            await db.commit()

    async def stats(self, since: datetime | None = None) -> dict[str, Any]:
        where = ""
        params: tuple = ()
        if since:
            where = "WHERE purchased_at >= ?"
            params = (since.isoformat(sep=" "),)
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                f"SELECT COUNT(*) AS cnt, COALESCE(SUM(buy_price),0) AS spent, "
                f"COALESCE(SUM(net_profit),0) AS expected_profit "
                f"FROM trades {where}",
                params,
            ) as cur:
                row = await cur.fetchone()
            async with db.execute(
                "SELECT status, COUNT(*) AS cnt FROM trades GROUP BY status", ()
            ) as cur:
                by_status = {r["status"]: r["cnt"] for r in await cur.fetchall()}
            async with db.execute(
                "SELECT category, COUNT(*) AS cnt, COALESCE(SUM(net_profit),0) AS profit "
                "FROM trades GROUP BY category",
                (),
            ) as cur:
                by_category = [dict(r) for r in await cur.fetchall()]

        return {
            "total_trades": row["cnt"] if row else 0,
            "total_spent": float(row["spent"] or 0),
            "total_expected_profit": float(row["expected_profit"] or 0),
            "by_status": by_status,
            "by_category": by_category,
        }

    async def get_kv(self, key: str, default: Any = None) -> Any:
        async with (
            aiosqlite.connect(self.path) as db,
            db.execute("SELECT value FROM settings_kv WHERE key = ?", (key,)) as cur,
        ):
            row = await cur.fetchone()
        if not row:
            return default
        try:
            return json.loads(row[0])
        except (json.JSONDecodeError, TypeError):
            return row[0]

    async def set_kv(self, key: str, value: Any) -> None:
        payload = json.dumps(value, ensure_ascii=False)
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """
                INSERT INTO settings_kv (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (key, payload),
            )
            await db.commit()


db = Database()


async def init_db() -> None:
    await db.init()


async def is_item_seen(item_id: int) -> bool:
    return await db.is_seen(item_id)


async def mark_item_seen(item_id: int, category: str, price: float) -> None:
    await db.mark_seen(item_id, category, price)


async def is_blacklisted(item_id: int) -> bool:
    return await db.is_blacklisted(item_id)


async def blacklist_item(item_id: int, reason: str = "") -> None:
    await db.blacklist_item(item_id, reason)


async def record_trade(
    item_id: int,
    category: str,
    title: str,
    buy_price: float,
    estimated_price: float,
    net_profit: float,
    status: str,
) -> None:
    await db.record_trade(
        item_id, category, title, buy_price, estimated_price, net_profit, status
    )


async def get_stats(since: datetime | None = None) -> dict[str, Any]:
    return await db.stats(since)


async def get_setting(key: str, default: Any = None) -> Any:
    return await db.get_kv(key, default)


async def set_setting(key: str, value: Any) -> None:
    await db.set_kv(key, value)
