from aiogram.fsm.state import State, StatesGroup


class SettingsStates(StatesGroup):
    waiting_profit = State()
    waiting_roi = State()
    waiting_cooldown = State()
