import asyncio
import os
import sys

# Aggiunge la root folder al path di python per risolvere l'errore ModuleNotFoundError su Render
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from aiohttp import web
from dotenv import load_dotenv

from bot.middlewares import AuthMiddleware
from bot.scheduler import setup_scheduler
from bot.handlers import commands, fsm_wizards, progress, chat
from utils.logger import logger

load_dotenv()

async def health_check(request):
    return web.Response(text="Bot is running!")

async def start_dummy_server():
    app = web.Application()
    app.router.add_get("/", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"Dummy web server running on port {port} to satisfy Render health checks.")

async def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN non impostato.")
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
        BotCommand(command="aiuto", description="Mostra la lista dei comandi"),
        BotCommand(command="oggi", description="Mostra l'agenda di oggi"),
        BotCommand(command="utenti", description="Mostra gli utenti in carico"),
        BotCommand(command="foglio", description="Link al Foglio Google"),
        BotCommand(command="esporta", description="Esporta i dati (PDF/Excel)"),
        BotCommand(command="log", description="Esporta e azzera i log di sistema"),
        BotCommand(command="reset", description="Azzera la memoria della chat"),
        BotCommand(command="nuke", description="[TEST] Resetta tutto il DB e i Fogli")
    ]
    await bot.set_my_commands(commands_list)
    
    # Avvia il server web fittizio per Render
    await start_dummy_server()
    
    logger.info("Bot avviato!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
