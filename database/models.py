from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field

class User(BaseModel):
    nome: str
    indirizzo: Optional[str] = None
    ore_settimanali: int = 0
    note: Optional[str] = None

class UserInDB(User):
    id: str = Field(alias="_id")

class Schedule(BaseModel):
    data: str # YYYY-MM-DD
    ora_inizio: str # HH:MM
    ora_fine: str # HH:MM
    utente_id: str
    luogo: Optional[str] = None

class SessionDiary(BaseModel):
    data: str
    utente_id: str
    ore_svolte: float
    testo_riassunto: Optional[str] = None
    note_progressi: Optional[str] = None

class ChatSession(BaseModel):
    user_id: int
    contesto: List[dict] = []
    ultimo_aggiornamento: datetime = Field(default_factory=datetime.utcnow)
