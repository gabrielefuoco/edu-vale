import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    TELEGRAM_BOT_TOKEN: str
    MONGODB_URI: str
    AUTHORIZED_USER_IDS: str
    
    # Optional with defaults or None
    TELEGRAM_GROUP_ID: str | None = None
    SEGRETERIA_TOPIC_ID: str | None = None
    DIARIO_TOPIC_ID: str | None = None
    PORT: int = 8080
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    
    @property
    def authorized_users(self) -> List[str]:
        return [uid.strip() for uid in self.AUTHORIZED_USER_IDS.split(",") if uid.strip()]

settings = Settings()
