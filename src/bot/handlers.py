import asyncio
from datetime import datetime, timedelta
from typing import Any

from aiogram import Bot, Dispatcher, F
from aiogram.exceptions import AiogramError
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from src.bot.formatters import (
    format_balance,
    format_buy_success,
    format_deal_card,
    format_stats,
    set_lzt_client,
)
from src.bot.keyboards import (
    get_deal_keyboard,
    get_main_keyboard,
    get_settings_keyboard,
)
from src.bot.states import SettingsStates
from src.config import settings
from src.db.database import (
    blacklist_item as db_blacklist_item,
)
from src.db.database import (
    get_stats,
    init_db,
    is_blacklisted,
    is_item_seen,
    mark_item_seen,
    record_trade,
    set_setting,
)
from src.engine.arbitrage import ArbitrageEngine
from src.lzt.client import LZTClient
from src.utils.logger import logger

aiogram_exc = AiogramError

dp = Dispatcher()
bot = Bot(token=settings.bot_token)
lzt_client = LZTClient()
arbitrage_engine = ArbitrageEngine()
set_lzt_client(lzt_client)

_state: dict[str, Any] = {
    "is_running": False,
    "parser_task": None,
    "health_task": None,
    "last_balance_alert": None,
    "last_api_failure": None,
    "low_balance_notified": False,
}


def _is_admin(user_id: int | None) -> bool:
    return user_id == settings.admin_id


async def _admin_guard(message_or_callback) -> bool:
    user_id = (
        message_or_callback.from_user.id if message_or_callback.from_user else None
    )
    if not _is_admin(user_id):
        if isinstance(message_or_callback, Message):
            await message_or_callback.answer("⛔ У вас нет доступа к этому боту.")
        return False
    return True


async def _balance_monitor_loop() -> None:
    while True:
        try:
            await asyncio.sleep(600)
            balances = await lzt_client.get_my_balance()
            if not balances:
                continue
            available = balances.get("balance", 0.0) - balances.get("hold", 0.0)
            if (
                available < settings.min_balance_alert
                and not _state["low_balance_notified"]
            ):
                _state["low_balance_notified"] = True
                try:
                    await bot.send_message(
                        settings.admin_id,
                        f"⚠️ <b>Низкий баланс LZT:</b> {available:g} ₽ "
                        f"(< порога {settings.min_balance_alert:g} ₽)",
                    )
                except (aiogram_exc, OSError) as exc:
                    logger.warning(f"Failed to send low-balance alert: {exc}")
            elif available >= settings.min_balance_alert:
                _state["low_balance_notified"] = False
        except asyncio.CancelledError:
            raise
        except (OSError, RuntimeError) as exc:
            logger.warning(f"Balance monitor error: {exc}")


async def _search_one_category(category: str) -> list[Any]:
    try:
        return await lzt_client.search_items(category)
    except (OSError, RuntimeError, ValueError) as exc:
        logger.error(f"search_items({category}) failed: {exc}")
        _state["last_api_failure"] = datetime.now()  # noqa: DTZ005
        return []


async def scanner_loop(bot_instance: Bot) -> None:
    while _state["is_running"]:
        categories = [
            c
            for c in settings.enabled_category_list()
            if c in arbitrage_engine.evaluators
        ]
        if not categories:
            await asyncio.sleep(5)
            continue

        results = await asyncio.gather(
            *(_search_one_category(c) for c in categories),
            return_exceptions=False,
        )

        for category, items in zip(categories, results, strict=False):
            for item in items:
                if not _state["is_running"]:
                    break
                try:
                    if await is_item_seen(item.item_id):
                        continue
                    if await is_blacklisted(item.item_id):
                        continue
                    await mark_item_seen(item.item_id, category, item.price)

                    opportunity = arbitrage_engine.evaluate_item(item)
                    if not opportunity:
                        continue

                    text = format_deal_card(opportunity)
                    keyboard = get_deal_keyboard(item.item_id, item.price)

                    if settings.auto_buy_enabled:
                        allowed, reason = arbitrage_engine.auto_buy_allowed(opportunity)
                        if not allowed:
                            await bot_instance.send_message(
                                settings.admin_id,
                                f"{text}\n\n🛑 <b>Auto-Buy отклонён:</b> {reason}",
                                parse_mode="HTML",
                            )
                            continue
                        buy_res = await lzt_client.fast_buy(item.item_id, item.price)
                        if buy_res.success:
                            await record_trade(
                                item.item_id,
                                category,
                                item.title,
                                item.price,
                                opportunity["estimated_price"],
                                opportunity["net_profit"],
                                "bought_auto",
                            )
                            await bot_instance.send_message(
                                settings.admin_id,
                                "🤖 <b>Автоматически куплен аккаунт!</b>\n\n"
                                + format_buy_success(opportunity, buy_res),
                                parse_mode="HTML",
                            )
                        else:
                            await bot_instance.send_message(
                                settings.admin_id,
                                f"❌ Автопокупка лота {item.item_id} не удалась: {buy_res.message}",
                            )
                    else:
                        await bot_instance.send_message(
                            settings.admin_id,
                            text,
                            reply_markup=keyboard,
                            parse_mode="HTML",
                        )
                except asyncio.CancelledError:
                    raise
                except (OSError, RuntimeError, ValueError) as exc:
                    logger.exception(f"scanner loop item {item.item_id} failed: {exc}")

        await asyncio.sleep(settings.check_interval_seconds)


@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext) -> None:
    if not await _admin_guard(message):
        return
    await state.clear()
    await init_db()
    await message.answer(
        "🤖 <b>LZT Arbitrage Bot запущен!</b>\n\n"
        "Связка: Minecraft + Brawl Stars + Valorant.\n"
        f"Версия: <code>{settings.version}</code>\n"
        "Используйте панель управления:",
        reply_markup=get_main_keyboard(_state["is_running"]),
        parse_mode="HTML",
    )


@dp.callback_query(F.data == "start_parser")
async def cb_start_parser(callback: CallbackQuery) -> None:
    if not await _admin_guard(callback):
        return
    if not _state["is_running"]:
        _state["is_running"] = True
        _state["parser_task"] = asyncio.create_task(scanner_loop(bot))
        if not _state["health_task"]:
            _state["health_task"] = asyncio.create_task(_balance_monitor_loop())
        await callback.message.edit_text(
            "🟢 Парсер запущен и мониторит рынок!",
            reply_markup=get_main_keyboard(_state["is_running"]),
        )
    await callback.answer()


@dp.callback_query(F.data == "stop_parser")
async def cb_stop_parser(callback: CallbackQuery) -> None:
    if not await _admin_guard(callback):
        return
    if _state["is_running"]:
        _state["is_running"] = False
        if _state["parser_task"]:
            _state["parser_task"].cancel()
            try:
                await _state["parser_task"]
            except asyncio.CancelledError:
                pass
            except (OSError, RuntimeError) as exc:
                logger.warning(f"Parser task cleanup error: {exc}")
            _state["parser_task"] = None
        await callback.message.edit_text(
            "🔴 Парсер остановлен.",
            reply_markup=get_main_keyboard(_state["is_running"]),
        )
    await callback.answer()


@dp.callback_query(F.data == "check_balance")
async def cb_check_balance(callback: CallbackQuery) -> None:
    if not await _admin_guard(callback):
        return
    balances = await lzt_client.get_my_balance()
    await callback.message.answer(format_balance(balances), parse_mode="HTML")
    await callback.answer()


@dp.callback_query(F.data == "stats")
async def cb_stats(callback: CallbackQuery) -> None:
    if not await _admin_guard(callback):
        return
    since = datetime.now() - timedelta(days=30)  # noqa: DTZ005
    stats = await get_stats(since=since)
    text = format_stats(stats) + "\n\n<i>Период: последние 30 дней</i>"
    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()


@dp.callback_query(F.data == "settings")
async def cb_settings(callback: CallbackQuery) -> None:
    if not await _admin_guard(callback):
        return
    await callback.message.edit_text(
        "⚙️ <b>Настройки</b>\n\nТекущие пороги. Нажмите, чтобы изменить:",
        reply_markup=get_settings_keyboard(
            settings.min_profit_rub,
            settings.min_roi_percent,
            settings.auto_buy_enabled,
            settings.seen_cooldown_minutes,
        ),
        parse_mode="HTML",
    )
    await callback.answer()


@dp.callback_query(F.data == "back_main")
async def cb_back_main(callback: CallbackQuery, state: FSMContext) -> None:
    if not await _admin_guard(callback):
        return
    await state.clear()
    await callback.message.edit_text(
        "🤖 <b>Панель управления</b>",
        reply_markup=get_main_keyboard(_state["is_running"]),
        parse_mode="HTML",
    )
    await callback.answer()


@dp.callback_query(F.data == "toggle_auto")
async def cb_toggle_auto(callback: CallbackQuery) -> None:
    if not await _admin_guard(callback):
        return
    new_value = not settings.auto_buy_enabled
    object.__setattr__(settings, "auto_buy_enabled", new_value)
    await set_setting("auto_buy_enabled", new_value)
    status = "🟢 Включён" if new_value else "🔴 Выключен"
    await callback.answer(f"Auto-Buy: {status}", show_alert=True)
    await cb_settings(callback)


@dp.callback_query(F.data == "set_profit")
async def cb_set_profit(callback: CallbackQuery, state: FSMContext) -> None:
    if not await _admin_guard(callback):
        return
    await state.set_state(SettingsStates.waiting_profit)
    await callback.message.answer(
        f"Введите новый <b>min profit</b> в рублях (сейчас {settings.min_profit_rub:g}):",
        parse_mode="HTML",
    )
    await callback.answer()


@dp.callback_query(F.data == "set_roi")
async def cb_set_roi(callback: CallbackQuery, state: FSMContext) -> None:
    if not await _admin_guard(callback):
        return
    await state.set_state(SettingsStates.waiting_roi)
    await callback.message.answer(
        f"Введите новый <b>min ROI %</b> (сейчас {settings.min_roi_percent:g}):",
        parse_mode="HTML",
    )
    await callback.answer()


@dp.callback_query(F.data == "set_cooldown")
async def cb_set_cooldown(callback: CallbackQuery, state: FSMContext) -> None:
    if not await _admin_guard(callback):
        return
    await state.set_state(SettingsStates.waiting_cooldown)
    await callback.message.answer(
        f"Введите <b>cooldown</b> для seen_items в минутах "
        f"(сейчас {settings.seen_cooldown_minutes}, 0 = навсегда):",
        parse_mode="HTML",
    )
    await callback.answer()


@dp.message(SettingsStates.waiting_profit)
async def process_profit(message: Message, state: FSMContext) -> None:
    if not await _admin_guard(message):
        await state.clear()
        return
    try:
        value = float(message.text.replace(",", "."))
        if value < 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введите положительное число.")
        return
    object.__setattr__(settings, "min_profit_rub", value)
    await set_setting("min_profit_rub", value)
    await state.clear()
    await message.answer(
        f"✅ Min profit = {value:g}₽",
        reply_markup=get_main_keyboard(_state["is_running"]),
    )


@dp.message(SettingsStates.waiting_roi)
async def process_roi(message: Message, state: FSMContext) -> None:
    if not await _admin_guard(message):
        await state.clear()
        return
    try:
        value = float(message.text.replace(",", "."))
        if value < 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введите положительное число.")
        return
    object.__setattr__(settings, "min_roi_percent", value)
    await set_setting("min_roi_percent", value)
    await state.clear()
    await message.answer(
        f"✅ Min ROI = {value:g}%", reply_markup=get_main_keyboard(_state["is_running"])
    )


@dp.message(SettingsStates.waiting_cooldown)
async def process_cooldown(message: Message, state: FSMContext) -> None:
    if not await _admin_guard(message):
        await state.clear()
        return
    try:
        value = int(message.text.strip())
        if value < 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введите целое число ≥ 0.")
        return
    object.__setattr__(settings, "seen_cooldown_minutes", value)
    await set_setting("seen_cooldown_minutes", value)
    await state.clear()
    await message.answer(
        f"✅ Cooldown = {value} мин",
        reply_markup=get_main_keyboard(_state["is_running"]),
    )


@dp.callback_query(F.data.startswith("buy_"))
async def cb_buy_item(callback: CallbackQuery) -> None:
    if not await _admin_guard(callback):
        return
    parts = callback.data.split("_")
    if len(parts) < 3:
        await callback.answer("Некорректные данные", show_alert=True)
        return
    item_id = int(parts[1])
    price = float(parts[2])

    await callback.message.edit_text("⏳ Покупаем аккаунт...")
    buy_res = await lzt_client.fast_buy(item_id, price)
    if buy_res.success:
        await record_trade(
            item_id,
            "manual",
            "Manual Deal",
            price,
            price * 1.5,
            price * 0.5,
            "bought_manual",
        )
        result_placeholder = {
            "item": type(
                "Item",
                (),
                {
                    "item_id": item_id,
                    "category": "manual",
                    "title": "Manual Deal",
                    "price": price,
                    "item_url": lzt_client.build_item_url(item_id),
                    "short_title": lambda self=None: "Manual Deal",
                },
            )(),
            "estimated_price": price * 1.5,
            "resell_fee": 0.0,
            "net_profit": price * 0.5,
            "roi": 50.0,
            "adjusted_roi": 50.0,
            "confidence": 0.7,
        }
        await callback.message.edit_text(
            format_buy_success(result_placeholder, buy_res),
            parse_mode="HTML",
        )
    else:
        await callback.message.edit_text(f"❌ Ошибка покупки: {buy_res.message}")
    await callback.answer()


@dp.callback_query(F.data.startswith("blacklist_"))
async def cb_blacklist_item(callback: CallbackQuery) -> None:
    if not await _admin_guard(callback):
        return
    item_id = int(callback.data.split("_", 1)[1])
    await db_blacklist_item(item_id, reason="manual_skip")
    await callback.message.edit_text(
        f"🚫 Лот <code>{item_id}</code> добавлен в чёрный список."
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("skip_"))
async def cb_skip_item(callback: CallbackQuery) -> None:
    if not await _admin_guard(callback):
        return
    await callback.message.edit_text("❌ Сделка пропущена.")
    await callback.answer()
