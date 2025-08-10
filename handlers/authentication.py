from aiogram import Dispatcher, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.types import ReplyKeyboardRemove

from database import get_user_by_phone, update_user_authentication
from handlers.keyboard import get_main_menu

class AuthStates(StatesGroup):
    awaiting_registration_decision = State()

async def request_authentication(message: types.Message, custom_prompt: str | None = None):
    builder = ReplyKeyboardBuilder()
    builder.button(text="🔒 ارسال شماره و احراز هویت", request_contact=True)
    builder.adjust(1)
    
    prompt = custom_prompt or (
        "سلام! به ربات ما خوش آمدید.\n"
        "برای استفاده از امکانات ربات، لطفاً ابتدا با کلیک روی دکمه زیر و ارسال شماره تلفن خود، احراز هویت نمایید."
    )
    
    await message.answer(
        prompt,
        reply_markup=builder.as_markup(resize_keyboard=True)
    )

async def handle_contact(message: types.Message, state: FSMContext):
    contact = message.contact
    if not contact or not message.from_user:
        return

    if contact.user_id != message.from_user.id:
        await message.answer("❌ خطا: شماره تلفن ارسال شده با حساب کاربری تلگرام شما مغایرت دارد.")
        return

    phone_number = contact.phone_number
    user_data = await get_user_by_phone(phone_number)

    if user_data:
        await update_user_authentication(phone_number, message.from_user.id)
        
        await message.answer(
            f"✅ کاربر گرامی <b>{user_data['first_name']} {user_data['last_name']}</b>، احراز هویت شما با موفقیت انجام شد و به منوی اصلی هدایت شدید.",
            reply_markup=get_main_menu()
        )
    else:
        await state.update_data(phone_number=phone_number)
        
        builder = InlineKeyboardBuilder()
        builder.button(text="📝 ثبت نام", callback_data="start_registration")
        builder.button(text="❌ لغو", callback_data="cancel_registration_decision")
        
        await message.answer(
            "شماره شما با موفقیت دریافت شد. به نظر می‌رسد شما هنوز در سامانه ثبت‌نام نکرده‌اید.\n\nآیا مایل به ثبت نام هستید؟",
            reply_markup=builder.as_markup()
        )
        await state.set_state(AuthStates.awaiting_registration_decision)

async def handle_cancel_decision(callback_query: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback_query.answer("درخواست شما لغو گردید.", show_alert=False)
    if isinstance(callback_query.message, types.Message):
        await callback_query.message.edit_text(
            "عملیات لغو شد. برای شروع مجدد، دستور /start را ارسال کنید."
        )

def register_auth_handlers(dp: Dispatcher):
    dp.message.register(handle_contact, F.contact)
    dp.callback_query.register(
        handle_cancel_decision, 
        AuthStates.awaiting_registration_decision, 
        F.data == "cancel_registration_decision"
    )