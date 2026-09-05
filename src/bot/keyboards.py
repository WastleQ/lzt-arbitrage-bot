from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_deal_keyboard(item_id: int, price: float) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"⚡ Купить за {price:g}₽",
                    callback_data=f"buy_{item_id}_{price}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🚫 В чёрный список",
                    callback_data=f"blacklist_{item_id}",
                ),
                InlineKeyboardButton(
                    text="❌ Пропустить", callback_data=f"skip_{item_id}"
                ),
            ],
        ]
    )


def get_main_keyboard(parser_active: bool) -> InlineKeyboardMarkup:
    status_text = "⏹ Остановить парсер" if parser_active else "▶️ Запустить парсер"
    status_action = "stop_parser" if parser_active else "start_parser"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=status_text, callback_data=status_action)],
            [
                InlineKeyboardButton(
                    text="💰 Баланс LZT", callback_data="check_balance"
                ),
                InlineKeyboardButton(text="📊 Статистика", callback_data="stats"),
            ],
            [
                InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings"),
                InlineKeyboardButton(text="🤖 Auto-Buy", callback_data="toggle_auto"),
            ],
        ]
    )


def get_settings_keyboard(
    min_profit: float,
    min_roi: float,
    auto_buy: bool,
    cooldown: int,
    enabled_cats: str = "minecraft,brawlstars,valorant",
) -> InlineKeyboardMarkup:
    auto_label = "🟢 Auto-Buy Вкл" if auto_buy else "🔴 Auto-Buy Выкл"
    cats = [c.strip() for c in enabled_cats.split(",") if c.strip()]

    mc_icon = "🟩" if "minecraft" in cats else "🟥"
    bs_icon = "🟩" if "brawlstars" in cats else "🟥"
    val_icon = "🟩" if "valorant" in cats else "🟥"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"💵 Min Profit: {min_profit:g}₽", callback_data="set_profit"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"📈 Min ROI: {min_roi:g}%", callback_data="set_roi"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"⏱ Cooldown: {cooldown} мин", callback_data="set_cooldown"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"{mc_icon} Minecraft", callback_data="toggle_cat_minecraft"
                ),
                InlineKeyboardButton(
                    text=f"{bs_icon} Brawl Stars", callback_data="toggle_cat_brawlstars"
                ),
                InlineKeyboardButton(
                    text=f"{val_icon} Valorant", callback_data="toggle_cat_valorant"
                ),
            ],
            [InlineKeyboardButton(text=auto_label, callback_data="toggle_auto")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")],
        ]
    )


def get_edit_keyboard(cancel_action: str = "settings") -> InlineKeyboardMarkup:
    """Клавиатура с одной кнопкой «Отмена» для FSM-ввода значения."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data=cancel_action)]
        ]
    )


def get_confirm_keyboard(
    confirm_action: str, cancel_action: str = "settings"
) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения значения (2-step apply)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Применить", callback_data=confirm_action
                ),
                InlineKeyboardButton(text="❌ Отмена", callback_data=cancel_action),
            ]
        ]
    )
