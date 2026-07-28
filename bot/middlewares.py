import os
import contextvars
from aiogram import BaseMiddleware
from aiogram.types import Message

current_user_id = contextvars.ContextVar('current_user_id', default=None)

class AuthMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        allowed_ids_str = os.getenv("AUTHORIZED_USER_IDS", "")
        allowed_ids = [uid.strip() for uid in allowed_ids_str.split(",") if uid.strip()]
        
        from_user = getattr(event, "from_user", None)
        if not from_user:
            return await handler(event, data)
            
        user_id = str(from_user.id)
        
        if not allowed_ids or user_id not in allowed_ids:
            if hasattr(event, "answer"):
                if hasattr(event, "message"): # E' una callback
                    await event.answer("Accesso Negato.", show_alert=True)
                else:
                    await event.answer("Accesso Negato.")
            return
            
        current_user_id.set(user_id)
        return await handler(event, data)
