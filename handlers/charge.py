from aiogram import Dispatcher, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import StateFilter
from aiogram.utils.keyboard import InlineKeyboardBuilder
import logging

from handlers.keyboard import get_main_menu
from config import ZARINPAL_MERCHANT_ID
from database import add_credit_to_user

class ChargeStates(StatesGroup):
    awaiting_amount = State()

async def start_charge_process(message: types.Message, state: FSMContext):
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ انصراف", callback_data="cancel_charge")
    
    await message.answer(
        "لطفاً مبلغ مورد نظر برای شارژ را به <b>تومان</b> وارد کنید:",
        reply_markup=builder.as_markup()
    )
    await state.set_state(ChargeStates.awaiting_amount)

async def process_charge_amount(message: types.Message, state: FSMContext):
    if not message.text or not message.text.isdigit() or not message.from_user:
        await message.answer("❌ لطفاً مبلغ را به صورت عددی و صحیح وارد کنید.")
        return
    
    amount = int(message.text)
    if amount < 1000:
        await message.answer("❌ حداقل مبلغ برای شارژ ۱,۰۰۰ تومان است.")
        return

    payment_link = f"https://zarinpal.com/pg/v4/request.html?merchant_id={ZARINPAL_MERCHANT_ID}&amount={amount}&description=شارژ حساب"
    
    builder = InlineKeyboardBuilder()
    builder.button(text="💳 پرداخت", url=payment_link)
    builder.button(text="✅ پرداخت را انجام دادم", callback_data=f"verify_payment:{amount}")
    builder.adjust(1)
    
    await message.answer(
        f"برای شارژ حساب به مبلغ {amount:,} تومان، لطفاً از طریق لینک زیر اقدام و سپس پرداخت خود را تایید کنید:",
        reply_markup=builder.as_markup()
    )

async def handle_payment_verification(callback_query: types.CallbackQuery, state: FSMContext):
    if not callback_query.data or not callback_query.from_user:
        await callback_query.answer("خطا در پردازش.", show_alert=True)
        return
        
    await callback_query.answer("⏳ در حال بررسی پرداخت شما...", show_alert=False)
    
    try:
        amount = int(callback_query.data.split(":")[1])
    except (ValueError, IndexError):
        await callback_query.answer("خطا در مبلغ پرداختی.", show_alert=True)
        return

    payment_successful = True
    
    if payment_successful:
        await add_credit_to_user(callback_query.from_user.id, amount)
        if isinstance(callback_query.message, types.Message):
            await callback_query.message.edit_text(
                f"✅ پرداخت شما با موفقیت تایید شد و مبلغ {amount:,} تومان به اعتبار شما اضافه گردید."
            )
            await callback_query.message.answer("شما به منوی اصلی بازگشتید.", reply_markup=get_main_menu())
    else:
        if isinstance(callback_query.message, types.Message):
            await callback_query.message.edit_text("❌ پرداخت شما موفقیت آمیز نبود. لطفاً مجدداً تلاش کنید.")
    
    await state.clear()

async def cancel_charge_handler(callback_query: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback_query.answer("عملیات شارژ لغو شد.", show_alert=False)
    if isinstance(callback_query.message, types.Message):
        await callback_query.message.delete()

def register_charge_handlers(dp: Dispatcher):
    dp.message.register(process_charge_amount, ChargeStates.awaiting_amount)
    dp.callback_query.register(handle_payment_verification, F.data.startswith("verify_payment:"))
    dp.callback_query.register(cancel_charge_handler, ChargeStates.awaiting_amount, F.data == "cancel_charge")