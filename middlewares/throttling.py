from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject
from cachetools import TTLCache

class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, message_rate_limit: float = 0.7, callback_rate_limit: float = 0.3):
        self.message_cache = TTLCache(maxsize=10_000, ttl=message_rate_limit)
        self.callback_cache = TTLCache(maxsize=10_000, ttl=callback_rate_limit)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        from_user = data.get('event_from_user')
        
        if not from_user:
            return await handler(event, data)
        
        user_id = from_user.id

        if isinstance(event, CallbackQuery):
            if user_id in self.callback_cache:
                await event.answer()
                return
            self.callback_cache[user_id] = True
        
        elif isinstance(event, Message):
            if user_id in self.message_cache:
                if self.message_cache.get(user_id) is None:
                    await event.answer("⏳ لطفاً کمی تامل فرمایید.")
                    self.message_cache[user_id] = True
                return
            
            self.message_cache[user_id] = None

        return await handler(event, data)