import os
import contextvars
from aiogram import BaseMiddleware
from aiogram.types import Message

current_user_id = contextvars.ContextVar('current_user_id', default=None)

class AuthMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: Message, data):
        allowed_ids_str = os.getenv("AUTHORIZED_USER_IDS", "")
        allowed_ids = [uid.strip() for uid in allowed_ids_str.split(",") if uid.strip()]
        user_id = str(event.from_user.id)
        
        if not allowed_ids or user_id not in allowed_ids:
            await event.answer("Accesso Negato.")
            return
            
        current_user_id.set(user_id)
        return await handler(event, data)
