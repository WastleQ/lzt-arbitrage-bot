from aiogram.fsm.state import State, StatesGroup


class SettingsStates(StatesGroup):
    waiting_profit = State()
    waiting_roi = State()
    waiting_cooldown = State()
    waiting_max_auto_buy = State()
    waiting_confirm_price = State()
    waiting_exclude_words = State()

    confirm_profit = State()
    confirm_roi = State()
    confirm_cooldown = State()
    confirm_max_auto_buy = State()
    confirm_exclude_words = State()
