import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, MESSAGE_RATE_LIMIT, CALLBACK_RATE_LIMIT
from database import create_table
from middlewares.user_check import UserCheckMiddleware
from middlewares.throttling import ThrottlingMiddleware
from middlewares.auth import AuthMiddleware
from handlers import start, authentication, registration, unknown, profile, main_menu, charge

logging.basicConfig(level=logging.DEBUG)

async def main():
    default_properties = DefaultBotProperties(parse_mode='HTML')
    bot = Bot(token=BOT_TOKEN, default=default_properties)
    
    storage = MemoryStorage()
    
    dp = Dispatcher(storage=storage)

    await create_table()

    user_check_mw = UserCheckMiddleware()
    throttling_mw = ThrottlingMiddleware(
        message_rate_limit=MESSAGE_RATE_LIMIT,
        callback_rate_limit=CALLBACK_RATE_LIMIT
    )
    auth_mw = AuthMiddleware()

    dp.update.middleware(user_check_mw)
    dp.update.middleware(throttling_mw)
    #dp.update.middleware(auth_mw)

    start.register_start_handlers(dp)
    authentication.register_auth_handlers(dp)
    registration.register_registration_handlers(dp)
    profile.register_profile_handlers(dp)
    main_menu.register_main_menu_handlers(dp)
    charge.register_charge_handlers(dp)
    unknown.register_unknown_handlers(dp)

    logging.info("Bot is starting polling...")
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped!")