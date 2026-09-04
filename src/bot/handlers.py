import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from bot.keyboards import get_deal_keyboard, get_main_keyboard
from config import settings
from db.database import init_db, is_item_seen, mark_item_seen, record_trade
from engine.arbitrage import ArbitrageEngine
from lzt.client import LZTClient

logger = logging.getLogger(__name__)

dp = Dispatcher()
bot = Bot(token=settings.bot_token)
lzt_client = LZTClient()
arbitrage_engine = ArbitrageEngine()

parser_task = None
is_running = False


async def scanner_loop(bot_instance: Bot) -> None:
    global is_running
    categories = ["minecraft", "brawlstars", "valorant"]

    while is_running:
        for category in categories:
            if not is_running:
                break
            try:
                items = await lzt_client.search_items(category)
                for item in items:
                    if await is_item_seen(item.item_id):
                        continue

                    await mark_item_seen(item.item_id, category, item.price)

                    opportunity = arbitrage_engine.evaluate_item(item)
                    if opportunity:
                        text = (
                            f"🔥 <b>Найдена выгодная сделка! [{category.upper()}]</b>\n\n"
                            f"🎮 <b>{item.title}</b>\n"
                            f"💰 Цена: <b>{item.price} ₽</b> (Оценка: {opportunity['estimated_price']} ₽)\n"
                            f"📈 Ожидаемый чистый профит: <b>+{opportunity['net_profit']} ₽</b> ({opportunity['roi']}% ROI)\n"
                            f"👤 Продавец: {item.seller_username}\n"
                        )
                        keyboard = get_deal_keyboard(item.item_id, item.price)

                        if settings.auto_buy_enabled:
                            buy_res = await lzt_client.fast_buy(item.item_id, item.price)
                            if buy_res.success:
                                await record_trade(
                                    item.item_id, category, item.title, item.price,
                                    opportunity['estimated_price'], opportunity['net_profit'], "bought_auto"
                                )
                                await bot_instance.send_message(
                                    settings.admin_id,
                                    f"🤖 <b>Автоматически куплен аккаунт!</b>\n{text}"
                                )
                            else:
                                await bot_instance.send_message(
                                    settings.admin_id,
                                    f"❌ Не удалось автокупить лот {item.item_id}: {buy_res.message}"
                                )
                        else:
                            await bot_instance.send_message(
                                settings.admin_id, text, reply_markup=keyboard, parse_mode="HTML"
                            )
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"Error in scanner loop for {category}: {e}")

            await asyncio.sleep(2.0)
        await asyncio.sleep(settings.check_interval_seconds)


@dp.message(Command("start"))
async def cmd_start(message: Message) -> None:
    if message.from_user.id != settings.admin_id:
        await message.answer("⛔ У вас нет доступа к этому боту.")
        return

    await init_db()
    await message.answer(
        "🤖 <b>LZT Arbitrage Bot запущен!</b>\n\n"
        "Связка: Minecraft + Brawl Stars + Valorant.\n"
        "Используйте панель управления ниже:",
        reply_markup=get_main_keyboard(is_running),
        parse_mode="HTML",
    )


@dp.callback_query(F.data == "start_parser")
async def cb_start_parser(callback: CallbackQuery) -> None:
    global is_running, parser_task
    if callback.from_user.id != settings.admin_id:
        return

    if not is_running:
        is_running = True
        parser_task = asyncio.create_task(scanner_loop(bot))
        await callback.message.edit_text(
            "🟢 Парсер успешно запущен и мониторит рынок!",
            reply_markup=get_main_keyboard(is_running),
        )
    await callback.answer()


@dp.callback_query(F.data == "stop_parser")
async def cb_stop_parser(callback: CallbackQuery) -> None:
    global is_running, parser_task
    if callback.from_user.id != settings.admin_id:
        return

    if is_running:
        is_running = False
        if parser_task:
            parser_task.cancel()
        await callback.message.edit_text(
            "🔴 Парсер остановлен.",
            reply_markup=get_main_keyboard(is_running),
        )
    await callback.answer()


@dp.callback_query(F.data == "check_balance")
async def cb_check_balance(callback: CallbackQuery) -> None:
    if callback.from_user.id != settings.admin_id:
        return

    balances = await lzt_client.get_my_balance()
    if balances:
        text = f"💰 <b>Баланс LZT:</b>\nОсновной: {balances['balance']} ₽\nХолд: {balances['hold']} ₽"
    else:
        text = "❌ Не удалось получить баланс. Проверьте LZT_API_TOKEN."

    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()


@dp.callback_query(F.data.startswith("buy_"))
async def cb_buy_item(callback: CallbackQuery) -> None:
    if callback.from_user.id != settings.admin_id:
        return

    _, item_id_str, price_str = callback.data.split("_")
    item_id = int(item_id_str)
    price = float(price_str)

    await callback.message.edit_text("⏳ Покупаем аккаунт...")

    buy_res = await lzt_client.fast_buy(item_id, price)
    if buy_res.success:
        await record_trade(
            item_id, "manual", "Manual Deal", price, price * 1.5, price * 0.5, "bought_manual"
        )
        await callback.message.edit_text(
            f"✅ <b>Аккаунт успешно куплен!</b>\nID: {item_id}\nЦена: {price} ₽\n\nДанные аккаунта получены.",
            parse_mode="HTML",
        )
    else:
        await callback.message.edit_text(f"❌ Ошибка покупки: {buy_res.message}")
    await callback.answer()


@dp.callback_query(F.data.startswith("skip_"))
async def cb_skip_item(callback: CallbackQuery) -> None:
    if callback.from_user.id != settings.admin_id:
        return
    await callback.message.edit_text("❌ Сделка пропущена.")
    await callback.answer()
