from aiogram import Dispatcher, types
from aiogram.filters import CommandStart, CommandObject
from aiogram.fsm.context import FSMContext
import logging

from handlers.authentication import request_authentication
from handlers.keyboard import get_main_menu
from database import get_user_by_referral_code

async def command_start_handler(message: types.Message, state: FSMContext, command: CommandObject | None = None, user: dict | None = None):
    if not user:
        if command and command.args and message.from_user:
            referrer_code = command.args
            referrer = await get_user_by_referral_code(referrer_code)
            if referrer:
                await state.update_data(referrer_code=referrer_code)
                logging.info(f"User {message.from_user.id} started with valid referral code: {referrer_code}")
        
        await request_authentication(message)
        return

    await message.answer(
        f"<b>{user['first_name']} عزیز</b>، به ربات خوش آمدید!",
        reply_markup=get_main_menu()
    )

def register_start_handlers(dp: Dispatcher):
    dp.message.register(command_start_handler, CommandStart())