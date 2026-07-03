import asyncio
import os
import sys

# Aggiunge la root folder al path di python per risolvere l'errore ModuleNotFoundError su Render
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
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
    
    # Setup Scheduler
    setup_scheduler(bot)
    
    # Setup Telegram Menu Commands
    commands_list = [
        BotCommand(command="nuovo_utente", description="Crea un nuovo utente"),
        BotCommand(command="elimina_utente", description="Elimina un utente"),
        BotCommand(command="oggi", description="Mostra le sessioni di oggi"),
        BotCommand(command="esporta", description="Esporta i dati in CSV")
    ]
    await bot.set_my_commands(commands_list)
    
    print("Bot avviato!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
