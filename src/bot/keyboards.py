from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_deal_keyboard(item_id: int, price: float) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⚡ Купить", callback_data=f"buy_{item_id}_{price}"
                ),
                InlineKeyboardButton(
                    text="❌ Пропустить", callback_data=f"skip_{item_id}"
                ),
            ]
        ]
    )
    return keyboard


def get_main_keyboard(parser_active: bool) -> InlineKeyboardMarkup:
    status_text = "⏹ Остановить парсер" if parser_active else "▶️ Запустить парсер"
    status_action = "stop_parser" if parser_active else "start_parser"

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=status_text, callback_data=status_action)],
            [InlineKeyboardButton(text="💰 Баланс LZT", callback_data="check_balance")],
            [InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings")],
        ]
    )
    return keyboard
