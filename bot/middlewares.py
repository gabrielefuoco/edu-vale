import os
import time
import contextvars
from aiogram import BaseMiddleware
from aiogram.types import Message

current_user_id = contextvars.ContextVar('current_user_id', default=None)

# Cache per evitare query a MongoDB ad ogni messaggio
_auth_cache = {
    "timestamp": 0,
    "db_owner_ids": set()
}

class AuthMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        from_user = getattr(event, "from_user", None)
        if not from_user:
            return await handler(event, data)
            
        user_id = str(from_user.id)
        
        # Nessun blocco: chiunque può usare il bot
        current_user_id.set(user_id)
        return await handler(event, data)
