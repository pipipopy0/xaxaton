from aiogram.fsm.state import State, StatesGroup

class CalendarStates(StatesGroup):
    waiting_email = State()
    waiting_password = State()