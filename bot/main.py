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
from bot.handlers import commands, progress, router as topic_router, callbacks
from bot.main_registry import AGENT_REGISTRY
from database.connection import get_checkpointer, get_system_config
from agents.segretario import create_segretario
from agents.diario import create_diario_agent
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
    
    sessions = await col.find().sort("data", -1).to_list(length=100)
    
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
            "data": body.get("Giorno"),
            "ore_svolte": body.get("Ore"),
            "utente_id": body.get("Utente"),
            "luogo": body.get("Luogo"),
            "testo_riassunto": body.get("Attività svolte")
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
    
    # Setup LangGraph Agents and Registry
    checkpointer = await get_checkpointer()
    segretario = create_segretario(checkpointer)
    diario = create_diario_agent(checkpointer)
    
    # Registry population
    AGENT_REGISTRY[None] = segretario
    AGENT_REGISTRY["segretario"] = segretario
    AGENT_REGISTRY["diario"] = diario
    
    sys_config = await get_system_config()
    
    tg_group_id = sys_config.get("group_id") or os.getenv("TELEGRAM_GROUP_ID")
    segreteria_topic_id = sys_config.get("segreteria_id") or os.getenv("SEGRETERIA_TOPIC_ID")
    diario_topic_id = sys_config.get("diario_id") or os.getenv("DIARIO_TOPIC_ID")
            
    if segreteria_topic_id:
        AGENT_REGISTRY[int(segreteria_topic_id)] = segretario
    if diario_topic_id:
        AGENT_REGISTRY[int(diario_topic_id)] = diario
    
    # Routers
    dp.include_router(commands.router)
    dp.include_router(progress.router)
    dp.include_router(callbacks.router)
    dp.include_router(topic_router.router)
    
    # Setup Scheduler
    setup_scheduler(bot)
    
    # Setup Telegram Menu Commands
    commands_list = [
        BotCommand(command="setup", description="Inizializza i topic nel gruppo"),
        BotCommand(command="aiuto", description="Mostra la lista dei comandi"),
        BotCommand(command="oggi", description="Mostra l'agenda di oggi"),
        BotCommand(command="utenti", description="Mostra gli utenti in carico"),
        BotCommand(command="esporta", description="Esporta i dati (Excel)"),
        BotCommand(command="log", description="Esporta e azzera i log di sistema"),
        BotCommand(command="reset", description="Azzera la memoria del topic"),
        BotCommand(command="nuke", description="[TEST] Resetta tutto il DB")
    ]
    await bot.set_my_commands(commands_list)
    
    await bot.set_my_description("Assistente IA Multi-Agente per la gestione delle attività educative.")
    await bot.set_my_short_description("Gestione operativa e stesura diari educativi.")
    
    # Avvia il server web per API e TMA
    await start_web_server()
    
    logger.info("Bot avviato!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
