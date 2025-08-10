from aiogram import Dispatcher, types, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from config import REFERRAL_REWARD_AMOUNT, SUPPORT_CONTACT
from handlers.charge import start_charge_process

async def show_products(message: types.Message, **kwargs):
    await message.answer("این بخش در حال ساخت است. به زودی لیست مشتریان در اینجا نمایش داده خواهد شد.")

async def show_credit(message: types.Message, **kwargs):
    user = kwargs.get('user', {})
    credit = user.get('credit', 0)
    await message.answer(f"💳 اعتبار فعلی شما: <b>{credit:,} تومان</b>")

async def charge_account(message: types.Message, state: FSMContext, **kwargs):
    await start_charge_process(message, state)
    
async def show_support(message: types.Message, **kwargs):
    await message.answer(f"📞 برای تماس با پشتیبانی می‌توانید با شماره {SUPPORT_CONTACT} در ارتباط باشید.")

async def marketing(message: types.Message, bot: Bot, **kwargs):
    user = kwargs.get('user', {})
    referral_code = user.get('referral_code')
    
    if not referral_code:
        await message.answer("❌ کد معرف شما یافت نشد. لطفاً با پشتیبانی تماس بگیرید.")
        return
    
    bot_info = await bot.get_me()
    invite_link = f"https://t.me/{bot_info.username}?start={referral_code}"

    banner_text = (
        f"🤝 <b>همکاری در فروش</b>\n\n"
        f"با دعوت دوستان خود به ربات، کسب درآمد کنید!\n\n"
        f"به ازای هر کاربری که با لینک اختصاصی شما وارد ربات شده و ثبت نام خود را <b>کامل کند</b>، مبلغ <b>{REFERRAL_REWARD_AMOUNT:,} تومان</b> اعتبار هدیه به شما تعلق خواهد گرفت.\n\n"
        f"🔗 <b>این لینک دعوت اختصاصی شماست:</b>\n"
        f"<code>{invite_link}</code>\n\n"
        f"<i>(روی لینک کلیک کنید تا به صورت خودکار کپی شود)</i>"
    )
    await message.answer(banner_text, disable_web_page_preview=True)

def register_main_menu_handlers(dp: Dispatcher):
    dp.message.register(show_products, F.text == "🛍️ لیست مشتریان")
    dp.message.register(show_credit, F.text == "💳 اعتبار من")
    dp.message.register(charge_account, F.text == "💵 شارژ حساب")
    dp.message.register(marketing, F.text == "🤝 همکاری در فروش")
    dp.message.register(show_support, F.text == "📞 پشتیبانی")

    dp.message.register(show_products, Command("products"))
    dp.message.register(show_credit, Command("credit"))
    dp.message.register(charge_account, Command("charge"))
    dp.message.register(marketing, Command("marketing"))
    dp.message.register(show_support, Command("support"))