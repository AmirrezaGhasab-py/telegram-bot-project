from aiogram import Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime, timedelta

from handlers.charge import start_charge_process
from handlers.registration import show_confirmation_summary
from config import AUTH_EXPIRATION_DAYS

async def show_profile(message: types.Message, user: dict):
    last_verified_str = user.get('last_verified_at')
    expiration_info = "نامشخص"

    if last_verified_str:
        try:
            last_verified_date = datetime.fromisoformat(last_verified_str)
            expiration_date = last_verified_date + timedelta(days=AUTH_EXPIRATION_DAYS)
            remaining_delta = expiration_date - datetime.now()
            
            if remaining_delta.days > 0:
                expiration_info = f"{remaining_delta.days} روز دیگر"
            else:
                expiration_info = "منقضی شده"
        except (ValueError, TypeError):
            expiration_info = "خطا در محاسبه"

    credit = user.get('credit', 0)
    profile_text = (
        f"👤 <b>پروفایل کاربری</b>\n\n"
        f"▫️ <b>نام:</b> {user.get('first_name', '')} {user.get('last_name', '')}\n"
        f"▫️ <b>جنسیت:</b> {user.get('gender', 'ثبت نشده')}\n"
        f"▫️ <b>تاریخ تولد:</b> {user.get('birth_date', 'ثبت نشده')}\n"
        f"▫️ <b>شماره موبایل:</b> {user.get('phone_number', 'ثبت نشده')}\n"
        f"▫️ <b>کد ملی:</b> {user.get('national_id') or 'ثبت نشده'}\n"
        f"▫️ <b>اعتبار حساب:</b> {credit:,} تومان\n\n"
        f"⏳ <b>انقضای احراز هویت:</b> {expiration_info}"
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text="✏️ ویرایش اطلاعات", callback_data="edit_profile")
    builder.button(text="💵 افزایش اعتبار", callback_data="charge_credit_profile")
    builder.adjust(1)

    await message.answer(profile_text, reply_markup=builder.as_markup())

async def handle_profile_buttons(callback_query: types.CallbackQuery, user: dict, state: FSMContext):
    action = callback_query.data
    
    if action == "edit_profile":
        if not isinstance(callback_query.message, types.Message): return
        await callback_query.answer("در حال آماده‌سازی فرم ویرایش...")

        await state.update_data(
            is_editing=True,
            first_name=user.get('first_name'),
            last_name=user.get('last_name'),
            national_id=user.get('national_id'),
            birth_date=user.get('birth_date'),
            gender=user.get('gender')
        )
        
        await callback_query.message.delete()
        await show_confirmation_summary(callback_query.message, state)

    elif action == "charge_credit_profile":
        if isinstance(callback_query.message, types.Message):
            await callback_query.answer()
            await start_charge_process(callback_query.message, state)
        else:
            await callback_query.answer("خطا: پیام اصلی یافت نشد.", show_alert=True)

def register_profile_handlers(dp: Dispatcher):
    dp.message.register(show_profile, Command("profile"))
    dp.message.register(show_profile, F.text == "👤 پروفایل من")
    dp.callback_query.register(handle_profile_buttons, F.data.in_({"edit_profile", "charge_credit_profile"}))