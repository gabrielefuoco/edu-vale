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

import hmac
import hashlib
from urllib.parse import parse_qsl
import json
from motor.motor_asyncio import AsyncIOMotorClient

async def health_check(request):
    return web.Response(text="Bot is running!")

def validate_telegram_data(init_data: str, bot_token: str) -> dict:
    if not init_data: return None
    parsed_data = dict(parse_qsl(init_data))
    hash_value = parsed_data.pop('hash', None)
    if not hash_value:
        return None
        
    data_check_string = '\n'.join([f"{k}={v}" for k, v in sorted(parsed_data.items())])
    secret_key = hmac.new("WebAppData".encode(), bot_token.encode(), hashlib.sha256).digest()
    calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    
    if calculated_hash == hash_value:
        user_data = json.loads(parsed_data.get('user', '{}'))
        return user_data
    return None

async def api_get_sessions(request):
    init_data = request.headers.get("X-Telegram-Init-Data")
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    user_data = validate_telegram_data(init_data, bot_token)
    
    if not user_data:
        return web.json_response({"error": "Unauthorized"}, status=401)
        
    user_id = str(user_data.get("id"))
    
    # Check if authorized
    allowed_ids_str = os.getenv("AUTHORIZED_USER_IDS", "")
    allowed_ids = [uid.strip() for uid in allowed_ids_str.split(",") if uid.strip()]
    if user_id not in allowed_ids:
        return web.json_response({"error": "Forbidden"}, status=403)
        
    mongo_uri = os.getenv("MONGODB_URI")
    client = AsyncIOMotorClient(mongo_uri)
    db = client[f"edu_agent_{user_id}"]
    col = db["diario_sessioni"]
    
    sessions = await col.find().sort("parsed.Giorno", -1).to_list(length=100)
    
    for s in sessions:
        s["_id"] = str(s["_id"])
        if "timestamp" in s:
            s["timestamp"] = s["timestamp"].isoformat()
            
    client.close()
    return web.json_response({"sessions": sessions})

async def api_update_session(request):
    init_data = request.headers.get("X-Telegram-Init-Data")
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    user_data = validate_telegram_data(init_data, bot_token)
    
    if not user_data:
        return web.json_response({"error": "Unauthorized"}, status=401)
        
    user_id = str(user_data.get("id"))
    session_id = request.match_info.get("id")
    
    try:
        body = await request.json()
    except:
        return web.json_response({"error": "Invalid JSON"}, status=400)
        
    mongo_uri = os.getenv("MONGODB_URI")
    client = AsyncIOMotorClient(mongo_uri)
    db = client[f"edu_agent_{user_id}"]
    col = db["diario_sessioni"]
    
    from bson import ObjectId
    try:
        obj_id = ObjectId(session_id)
        update_data = {
            "parsed.Giorno": body.get("Giorno"),
            "parsed.Ore": body.get("Ore"),
            "parsed.Utente": body.get("Utente"),
            "parsed.Luogo": body.get("Luogo"),
            "parsed.Attività svolte": body.get("Attività svolte")
        }
        update_data = {k: v for k, v in update_data.items() if v is not None}
        
        if update_data:
            await col.update_one({"_id": obj_id}, {"$set": update_data})
            
        client.close()
        return web.json_response({"status": "success"})
    except Exception as e:
        client.close()
        return web.json_response({"error": str(e)}, status=500)

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", health_check)
    app.router.add_get("/api/sessions", api_get_sessions)
    app.router.add_post("/api/sessions/{id}", api_update_session)
    
    webapp_dir = os.path.join(os.path.dirname(__file__), '..', 'webapp')
    if os.path.exists(webapp_dir):
        app.router.add_static('/webapp/', path=webapp_dir, name='webapp')
    
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"Web server running on port {port}. WebApp at /webapp/index.html")

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
        BotCommand(command="esporta", description="Esporta i dati (Excel)"),
        BotCommand(command="log", description="Esporta e azzera i log di sistema"),
        BotCommand(command="reset", description="Azzera la memoria della chat"),
        BotCommand(command="nuke", description="[TEST] Resetta tutto il DB")
    ]
    await bot.set_my_commands(commands_list)
    
    # Imposta la descrizione di benvenuto (mostrata all'utente prima dell'avvio)
    await bot.set_my_description(
        "Ciao! Sono Edu-Agent, il tuo assistente operativo per la gestione delle attività educative. 📊\n\n"
        "Posso aiutarti a:\n"
        "- 📝 Registrare sessioni svolte ed esportarle automaticamente su Fogli Google.\n"
        "- 📅 Pianificare appuntamenti futuri e gestire la tua agenda.\n"
        "- 👥 Memorizzare informazioni, note e preferenze degli utenti in carico.\n\n"
        "Inviami un vocale o un messaggio di testo per iniziare a lavorare insieme! 🎙️"
    )
    
    # Imposta la descrizione breve (visibile sul profilo)
    await bot.set_my_short_description(
        "Assistente IA per la gestione operativa di sessioni, agenda e note educative."
    )
    
    # Avvia il server web per API e TMA
    await start_web_server()
    
    logger.info("Bot avviato!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
