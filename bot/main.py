import asyncio
import os
from aiogram import Bot, Dispatcher
from dotenv import load_dotenv

from bot.middlewares import AuthMiddleware
from bot.scheduler import setup_scheduler
from bot.handlers import commands, fsm_wizards, progress, chat

load_dotenv()

async def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Errore: TELEGRAM_BOT_TOKEN non impostato.")
        return
    
    bot = Bot(token=token)
    dp = Dispatcher()
    
    # Middleware
    dp.message.middleware(AuthMiddleware())
    
    # Routers
    dp.include_router(commands.router)
    dp.include_router(fsm_wizards.router)
    dp.include_router(progress.router)
    dp.include_router(chat.router)  # Must be last as fallback
    
    # Scheduler
    setup_scheduler(bot)
    
    print("Bot avviato!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
