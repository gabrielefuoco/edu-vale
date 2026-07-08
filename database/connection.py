import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from bot.middlewares import current_user_id
from langgraph.checkpoint.mongodb import MongoDBSaver as AsyncMongoDBSaver

load_dotenv()

MONGO_URI = os.getenv("MONGODB_URI", "")
client = AsyncIOMotorClient(MONGO_URI) if MONGO_URI else None

async def get_db():
    if client is None:
        raise Exception("Database non configurato. Controlla MONGODB_URI.")
    
    uid = current_user_id.get()
    if not uid:
        # Fallback nel caso in cui get_db venga chiamato fuori dal contesto del bot (es. script)
        uid = "default"
        
    return client[f"edu_agent_{uid}"]

async def get_collection(name: str):
    database = await get_db()
    return database[name]

async def get_checkpointer():
    """Restituisce il checkpointer MongoDB condiviso."""
    return AsyncMongoDBSaver(client, db_name="edu_agent_checkpoints")
