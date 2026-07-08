import logging
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

# Setup console logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - [%(name)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger("edu_agent")

async def db_log(level: str, module: str, message: str, details: dict = None):
    """
    Logga in console e salva su MongoDB nella collection 'system_logs'.
    level: "INFO", "WARNING", "ERROR", "DEBUG"
    """
    formatted_msg = f"[{module}] {message}"
    
    if level == "ERROR":
        logger.error(formatted_msg)
    elif level == "WARNING":
        logger.warning(formatted_msg)
    elif level == "DEBUG":
        logger.debug(formatted_msg)
    else:
        logger.info(formatted_msg)
        
    try:
        from database.connection import get_system_collection
        col = await get_system_collection("system_logs")
        log_doc = {
            "timestamp": datetime.now(ZoneInfo("Europe/Rome")),
            "level": level,
            "module": module,
            "message": message,
            "details": details or {}
        }
        await col.insert_one(log_doc)
    except Exception as e:
        logger.error(f"[logger] Errore salvataggio log su MongoDB: {e}")
