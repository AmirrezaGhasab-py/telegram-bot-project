from aiogram import Dispatcher, types, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.types import ReplyKeyboardRemove
import logging

from database import add_new_user, update_user_details, get_user_by_referral_code, add_credit_to_user
from utils.validation import is_valid_persian_name, is_valid_national_code, is_valid_birth_date
from handlers.authentication import AuthStates
from handlers.keyboard import get_main_menu
from config import REFERRAL_REWARD_AMOUNT

class RegistrationStates(StatesGroup):
    in_progress = State()
    awaiting_confirmation = State()

REGISTRATION_STEPS = {
    'first_name': {
        'prompt': "📝 لطفاً نام خود را وارد نمایید:",
        'validator': is_valid_persian_name,
        'error_message': "❌ نام وارد شده معتبر نیست. لطفاً یک نام فارسی صحیح وارد کنید.",
        'next_step': 'last_name',
        'display_name': 'نام'
    },
    'last_name': {
        'prompt': "📝 لطفاً نام خانوادگی خود را وارد نمایید:",
        'validator': is_valid_persian_name,
        'error_message': "❌ نام خانوادگی وارد شده معتبر نیست. لطفاً یک نام خانوادگی فارسی صحیح وارد کنید.",
        'next_step': 'national_id',
        'display_name': 'نام خانوادگی'
    },
    'national_id': {
        'prompt': "📝 لطفاً کد ملی خود را وارد نمایید:\n\n(این بخش اختیاری است، برای رد کردن /skip را تایپ کنید)",
        'validator': is_valid_national_code,
        'error_message': "❌ کد ملی وارد شده نامعتبر است. لطفاً مجدداً تلاش کنید یا /skip را بزنید.",
        'is_optional': True,
        'next_step': 'birth_date',
        'display_name': 'کد ملی'
    },
    'birth_date': {
        'prompt': "📝 لطفاً تاریخ تولد خود را وارد نمایید:\n\n(فرمت: 1375/05/14)",
        'validator': is_valid_birth_date,
        'error_message': "❌ فرمت تاریخ تولد اشتباه است.",
        'next_step': 'gender',
        'display_name': 'تاریخ تولد'
    },
    'gender': {
        'prompt': "📝 لطفاً جنسیت خود را انتخاب کنید:",
        'validator': lambda g: g in ["آقا", "خانم"],
        'error_message': "❌ لطفاً فقط یکی از گزینه‌های روی کیبورد را انتخاب کنید.",
        'keyboard': ReplyKeyboardBuilder().add(types.KeyboardButton(text="آقا"), types.KeyboardButton(text="خانم")).adjust(2),
        'next_step': 'confirmation',
        'display_name': 'جنسیت'
    }
}

def create_nav_buttons(current_step: str, data: dict):
    builder = InlineKeyboardBuilder()
    previous_step = data.get('previous_step')
    if previous_step:
        builder.button(text="⬅️ بازگشت", callback_data=f"reg_step:{previous_step}")
    builder.button(text="❌ انصراف کامل", callback_data="cancel_flow")
    builder.adjust(2)
    return builder.as_markup()

async def ask_for_step(message: types.Message, state: FSMContext, step_name: str, user_data: dict, is_edit: bool = False):
    step_info = REGISTRATION_STEPS.get(step_name)
    if not step_info: return
    
    previous_step = next((key for key, value in REGISTRATION_STEPS.items() if value['next_step'] == step_name), None)
    await state.update_data(current_step=step_name, previous_step=previous_step)
    
    reply_markup = step_info.get('keyboard')
    if reply_markup:
        reply_markup = reply_markup.as_markup(resize_keyboard=True, one_time_keyboard=True)
    else:
        reply_markup = create_nav_buttons(step_name, {'previous_step': previous_step})
    
    prompt_message = step_info['prompt']
    
    if is_edit:
        await message.edit_text(prompt_message, reply_markup=reply_markup)
    else:
        await message.answer(prompt_message, reply_markup=reply_markup)
    
    await state.set_state(RegistrationStates.in_progress)

async def show_confirmation_summary(message: types.Message, state: FSMContext, is_edit: bool = False):
    user_data = await state.get_data()
    summary_text = (
        "لطفاً اطلاعات زیر را بررسی و تأیید نمایید:\n\n"
        f"▫️ <b>نام:</b> {user_data.get('first_name', '-')}\n"
        f"▫️ <b>نام خانوادگی:</b> {user_data.get('last_name', '-')}\n"
        f"▫️ <b>کد ملی:</b> {user_data.get('national_id') or 'وارد نشده'}\n"
        f"▫️ <b>تاریخ تولد:</b> {user_data.get('birth_date', '-')}\n"
        f"▫️ <b>جنسیت:</b> {user_data.get('gender', '-')}"
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ تأیید و ثبت نهایی", callback_data="confirm_registration")
    
    for field in REGISTRATION_STEPS.keys():
        display_name = REGISTRATION_STEPS[field]['display_name']
        builder.button(text=f"✏️ ویرایش {display_name}", callback_data=f"reg_step:{field}")
    
    builder.button(text="❌ انصراف کامل", callback_data="cancel_flow")
    builder.adjust(1)
    
    if is_edit:
        await message.edit_text(summary_text, reply_markup=builder.as_markup())
    else:
        await message.answer(summary_text, reply_markup=builder.as_markup())
    
    await state.set_state(RegistrationStates.awaiting_confirmation)

async def start_registration_flow(callback_query: types.CallbackQuery, state: FSMContext):
    if not isinstance(callback_query.message, types.Message): return
    
    user_data = await state.get_data()
    if not user_data.get('phone_number'):
        await callback_query.answer("❌ خطای منطقی: لطفاً ابتدا شماره تلفن خود را از طریق دکمه /start ارسال نمایید.", show_alert=True)
        return
        
    await callback_query.answer("📝 شروع فرآیند ثبت نام")
    await callback_query.message.delete()
    await ask_for_step(callback_query.message, state, 'first_name', user_data)

async def process_registration_step(message: types.Message, state: FSMContext):
    if not message.text: return
    
    user_data = await state.get_data()
    current_step_name = user_data.get('current_step')
    if not current_step_name: return
    
    step_info = REGISTRATION_STEPS[current_step_name]
    user_input = message.text.strip()
    
    # بررسی skip برای فیلدهای اختیاری
    if step_info.get('is_optional') and user_input.lower() == '/skip':
        await state.update_data({current_step_name: None})
    elif not step_info['validator'](user_input):
        await message.answer(step_info['error_message'])
        return
    else:
        await state.update_data({current_step_name: user_input})
    
    # حذف کیبورد اگر وجود داشت
    if step_info.get('keyboard'):
        await message.answer("✅ انتخاب شما ثبت شد.", reply_markup=ReplyKeyboardRemove())
    
    next_step_name = step_info['next_step']
    if next_step_name == 'confirmation':
        await show_confirmation_summary(message, state)
    else:
        await ask_for_step(message, state, next_step_name, user_data)

async def handle_step_navigation(callback_query: types.CallbackQuery, state: FSMContext):
    if not callback_query.data: return
    
    step_name = callback_query.data.split(":")[1]
    if not isinstance(callback_query.message, types.Message): return
    
    await callback_query.answer()
    user_data = await state.get_data()
    
    if step_name == "confirmation":
        await show_confirmation_summary(callback_query.message, state, is_edit=True)
    else:
        # برای ویرایش یک فیلد خاص، فقط همان فیلد را بپرس
        await ask_for_step(callback_query.message, state, step_name, user_data, is_edit=True)

async def handle_final_confirmation(callback_query: types.CallbackQuery, state: FSMContext, bot: Bot):
    if not isinstance(callback_query.message, types.Message): return
    
    await callback_query.answer()

    user_data = await state.get_data()
    required_fields = ['first_name', 'last_name', 'birth_date', 'gender']
    if not all(user_data.get(field) for field in required_fields):
        await callback_query.message.edit_text("❌ خطای سیستمی: اطلاعات ثبت نام ناقص است. لطفاً با /start از ابتدا شروع کنید.")
        await state.clear()
        return
    
    if user_data.get("is_editing"):
        await update_user_details(
            telegram_id=callback_query.from_user.id,
            first_name=user_data['first_name'],
            last_name=user_data['last_name'],
            national_id=user_data.get('national_id'),
            birth_date=user_data['birth_date'],
            gender=user_data['gender']
        )
        await callback_query.message.delete()
        await callback_query.message.answer(
            "✅ اطلاعات پروفایل شما با موفقیت به‌روزرسانی شد.",
            reply_markup=get_main_menu()
        )
    else:
        phone_number = user_data.get('phone_number')
        if not phone_number:
            await callback_query.message.edit_text("❌ خطای سیستمی: شماره تلفن یافت نشد. لطفاً از ابتدا شروع کنید.")
            await state.clear()
            return
            
        await add_new_user(
            telegram_id=callback_query.from_user.id,
            phone_number=phone_number,
            first_name=user_data['first_name'],
            last_name=user_data['last_name'],
            national_id=user_data.get('national_id'),
            birth_date=user_data['birth_date'],
            gender=user_data['gender']
        )
        
        # پردازش کد معرف
        referrer_code = user_data.get('referrer_code')
        if referrer_code:
            referrer = await get_user_by_referral_code(referrer_code)
            if referrer and referrer.get('telegram_id'):
                await add_credit_to_user(referrer['telegram_id'], REFERRAL_REWARD_AMOUNT)
                try:
                    await bot.send_message(
                        referrer['telegram_id'],
                        f"🎉 تبریک! یک نفر با کد معرف شما ثبت نام کرد و مبلغ {REFERRAL_REWARD_AMOUNT:,} تومان به اعتبار شما اضافه شد."
                    )
                except Exception as e:
                    logging.error(f"Failed to send referral notification to {referrer['telegram_id']}: {e}")

        await callback_query.message.delete()
        await callback_query.message.answer(
            "✅ ثبت نام شما با موفقیت تکمیل گردید. به سامانه ما خوش آمدید.",
            reply_markup=get_main_menu()
        )
    
    await state.clear()

async def cancel_flow_handler(callback_query: types.CallbackQuery, state: FSMContext):
    if not isinstance(callback_query.message, types.Message): return
    
    current_state = await state.get_state()
    if current_state is None:
        await callback_query.answer()
        return

    await state.clear()
    await callback_query.answer("عملیات لغو شد.", show_alert=True)
    await callback_query.message.edit_text(
        "عملیات لغو شد. برای شروع مجدد، دستور /start را ارسال کنید."
    )

def register_registration_handlers(dp: Dispatcher):
    dp.callback_query.register(start_registration_flow, AuthStates.awaiting_registration_decision, F.data == "start_registration")
    dp.callback_query.register(cancel_flow_handler, F.data == "cancel_flow")
    dp.callback_query.register(handle_step_navigation, F.data.startswith("reg_step:"))
    dp.message.register(process_registration_step, RegistrationStates.in_progress)
    dp.callback_query.register(handle_final_confirmation, RegistrationStates.awaiting_confirmation, F.data == "confirm_registration")