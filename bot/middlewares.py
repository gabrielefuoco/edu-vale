import os
from aiogram import BaseMiddleware
from aiogram.types import Message

class AuthMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: Message, data):
        allowed_id = os.getenv("AUTHORIZED_USER_ID")
        if not allowed_id or str(event.from_user.id) != allowed_id:
            await event.answer("Accesso Negato.")
            return
        return await handler(event, data)
