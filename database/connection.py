import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGODB_URI", "")
client = AsyncIOMotorClient(MONGO_URI) if MONGO_URI else None
db = client.edu_agent if client else None

async def get_db():
    if db is None:
        raise Exception("Database non configurato. Controlla MONGODB_URI.")
    return db

async def get_collection(name: str):
    database = await get_db()
    return database[name]
