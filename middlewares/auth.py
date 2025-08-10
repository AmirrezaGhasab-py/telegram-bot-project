from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject
from datetime import datetime, timedelta

from database import get_user
from handlers.authentication import request_authentication, AuthStates
from config import AUTH_EXPIRATION_DAYS
from handlers.registration import RegistrationStates

class AuthMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        from_user = data.get('event_from_user')
        if not from_user:
            return await handler(event, data)

        user = await get_user(telegram_id=from_user.id)
        state = data.get('state')

        if user:
            data['user'] = user
            if not user.get('is_active', True):
                if isinstance(event, Message):
                    await event.answer("❌ حساب کاربری شما غیرفعال شده است.")
                elif isinstance(event, CallbackQuery):
                    await event.answer("❌ حساب کاربری شما غیرفعال شده است.", show_alert=True)
                return

            last_verified_str = user.get('last_verified_at')
            is_expired = False
            if last_verified_str:
                try:
                    last_verified_date = datetime.fromisoformat(last_verified_str)
                    if datetime.now() - last_verified_date > timedelta(days=AUTH_EXPIRATION_DAYS):
                        is_expired = True
                except (ValueError, TypeError):
                    is_expired = True
            else:
                 is_expired = True

            if is_expired:
                target_message = None
                if isinstance(event, Message):
                    target_message = event
                elif isinstance(event, CallbackQuery):
                    target_message = event.message

                if isinstance(target_message, Message):
                    await request_authentication(
                        target_message,
                        custom_prompt="⚠️ اعتبار احراز هویت شما منقضی شده است. لطفاً برای ادامه، مجدداً شماره تلفن خود را ارسال کنید."
                    )
                elif isinstance(event, CallbackQuery):
                     await event.answer("⚠️ اعتبار شما منقضی شده، لطفاً /start را بزنید.", show_alert=True)
                return

            return await handler(event, data)

        else:
            data['user'] = None
            current_state = await state.get_state() if state else None

            allowed_states = [
                AuthStates.awaiting_registration_decision,
                RegistrationStates.in_progress,
                RegistrationStates.awaiting_confirmation
            ]

            allowed_for_new_users = (
                isinstance(event, Message) and (event.text and event.text.startswith('/start') or event.contact)
            ) or (
                isinstance(event, CallbackQuery) and (
                    event.data in ["start_registration", "cancel_registration_decision", "confirm_registration", "cancel_flow"] or
                    (event.data and event.data.startswith("reg_step:"))
                )
            ) or (
                current_state in allowed_states
            )

            if allowed_for_new_users:
                return await handler(event, data)

            target_message = None
            if isinstance(event, Message):
                target_message = event
            elif isinstance(event, CallbackQuery):
                target_message = event.message

            if isinstance(target_message, Message):
                await request_authentication(target_message)
            elif isinstance(event, CallbackQuery):
                await event.answer("⛔️ برای دسترسی به این بخش، ابتدا باید احراز هویت کنید.", show_alert=True)
            return