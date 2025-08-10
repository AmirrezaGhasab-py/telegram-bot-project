from aiogram import Dispatcher, types

async def handle_unknown_command(message: types.Message):
    await message.answer(
        "❌ متوجه درخواست شما نشدم.\n\n"
        "لطفاً از دکمه‌های منوی زیر استفاده کنید یا دستور /start را وارد نمایید."
    )

def register_unknown_handlers(dp: Dispatcher):
    # این handler در آخرین اولویت قرار می‌گیرد 
    dp.message.register(handle_unknown_command)