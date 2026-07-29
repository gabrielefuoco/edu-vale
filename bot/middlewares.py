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
        # 1. Super-admin da .env
        env_ids_str = os.getenv("AUTHORIZED_USER_IDS", "")
        env_ids = set(uid.strip() for uid in env_ids_str.split(",") if uid.strip())
        
        # 2. Owner registrati nel DB (con cache di 60 secondi)
        now = time.time()
        if now - _auth_cache["timestamp"] > 60:
            from database.connection import get_all_group_configs
            db_configs = await get_all_group_configs()
            _auth_cache["db_owner_ids"] = {cfg["owner_id"] for cfg in db_configs if "owner_id" in cfg}
            _auth_cache["timestamp"] = now
            
        all_allowed = env_ids | _auth_cache["db_owner_ids"]
        
        from_user = getattr(event, "from_user", None)
        if not from_user:
            return await handler(event, data)
            
        user_id = str(from_user.id)
        
        if not all_allowed or user_id not in all_allowed:
            if hasattr(event, "answer"):
                if hasattr(event, "message"): # E' una callback
                    await event.answer("Accesso Negato.", show_alert=True)
                else:
                    await event.answer("Accesso Negato.")
            return
            
        current_user_id.set(user_id)
        return await handler(event, data)
