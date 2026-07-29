import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from bot.middlewares import current_user_id
# from langgraph.checkpoint.mongodb import MongoDBSaver

load_dotenv()

from config import settings

MONGO_URI = settings.MONGODB_URI
client = AsyncIOMotorClient(MONGO_URI) if MONGO_URI else None

async def get_db(uid: str = None):
    if client is None:
        raise Exception("Database non configurato. Controlla MONGODB_URI.")
    
    if not uid:
        uid = current_user_id.get()
        
    if not uid:
        # Fallback nel caso in cui get_db venga chiamato fuori dal contesto del bot (es. script)
        uid = "default"
        
    return client[f"edu_agent_{uid}"]

async def get_collection(name: str, uid: str = None):
    database = await get_db(uid)
    return database[name]
    
async def get_system_collection(name: str):
    if client is None:
        raise Exception("MongoDB client non inizializzato.")
    database = client["edu_agent_system"]
    return database[name]

async def get_checkpoint_collection(name: str):
    if client is None:
        raise Exception("MongoDB client non inizializzato.")
    database = client["edu_agent_checkpoints"]
    return database[name]

from langgraph.checkpoint.mongodb import MongoDBSaver

# Sync client for LangGraph checkpointer
from pymongo import MongoClient
sync_client = MongoClient(MONGO_URI) if MONGO_URI else None

async def get_checkpointer():
    """Restituisce il checkpointer MongoDB condiviso."""
    return MongoDBSaver(sync_client, db_name="edu_agent_checkpoints")

async def get_all_group_configs() -> list[dict]:
    """Ritorna TUTTE le configurazioni di gruppo registrate."""
    if client is None: return []
    db = client["edu_agent_system"]
    return await db["groups"].find().to_list(length=100)

async def get_group_config(group_id: int) -> dict | None:
    """Ritorna la config di UN specifico gruppo Telegram."""
    if client is None: return None
    db = client["edu_agent_system"]
    return await db["groups"].find_one({"group_id": group_id})

async def save_group_config(config_data: dict):
    """Salva/aggiorna la config di un gruppo (upsert per group_id)."""
    if client is None: return
    db = client["edu_agent_system"]
    await db["groups"].update_one(
        {"group_id": config_data["group_id"]},
        {"$set": config_data},
        upsert=True
    )

async def migrate_old_config():
    """Migra la vecchia configurazione singola nel nuovo formato multi-gruppo."""
    if client is None: return
    db = client["edu_agent_system"]
    old_config = await db["config"].find_one({"_id": "telegram_setup"})
    if old_config and "group_id" in old_config:
        # Crea la nuova config assumendo che il primo admin nel .env sia l'owner
        # Se non c'è, usiamo 'default'
        allowed_ids_str = os.getenv("AUTHORIZED_USER_IDS", "")
        allowed_ids = [uid.strip() for uid in allowed_ids_str.split(",") if uid.strip()]
        owner_id = allowed_ids[0] if allowed_ids else "default"
        
        new_config = {
            "group_id": old_config["group_id"],
            "owner_id": owner_id,
            "segreteria_id": old_config.get("segreteria_id"),
            "diario_id": old_config.get("diario_id")
        }
        await save_group_config(new_config)
        # Rimuove la vecchia per non migrarla più
        await db["config"].delete_one({"_id": "telegram_setup"})
        print(f"Migrata configurazione per il gruppo {new_config['group_id']} con owner {owner_id}")
