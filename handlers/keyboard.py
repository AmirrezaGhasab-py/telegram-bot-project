from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.types import ReplyKeyboardMarkup

def get_main_menu() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    
    builder.button(text="👤 پروفایل من")
    builder.button(text="🛍️ مشاهده محصولات")
    builder.button(text="💳 اعتبار من")
    builder.button(text="💵 شارژ حساب")
    builder.button(text="🤝 همکاری در فروش")
    builder.button(text="📞 پشتیبانی")
    
    builder.adjust(2)
    
    return builder.as_markup(resize_keyboard=True)