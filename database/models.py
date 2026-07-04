from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field

class User(BaseModel):
    nome: str
    indirizzo: Optional[str] = None
    ore_settimanali: int = 0
    note: Optional[str] = None
    preferenze: List[str] = []

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

# --- Tool Validation Models ---
class ToolRegistraSessione(BaseModel):
    Giorno: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    Ore: float
    Utente: str
    Luogo: Optional[str] = None
    Attività_svolte: str = Field(alias="Attività svolte") # alias per lo spazio
    
class ToolPianificaSessione(BaseModel):
    Data: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    Ora_Inizio: str = Field(alias="Ora Inizio", pattern=r"^\d{2}:\d{2}$")
    Ora_Fine: str = Field(alias="Ora Fine", pattern=r"^\d{2}:\d{2}$")
    Utente: str
    Luogo: Optional[str] = None

class ToolCreaUtente(BaseModel):
    nome: str
    ore_settimanali: float = 0
    note: Optional[str] = ""
    preferenze: List[str] = []

class ToolCercaUtenti(BaseModel):
    query: str

class ToolLeggiStoricoSessioni(BaseModel):
    utente: str
    limite: int = 5

class ToolLeggiAgenda(BaseModel):
    data_inizio: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    data_fine: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")

class ToolEliminaSessionePianificata(BaseModel):
    Data: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    Utente: str

class ToolModificaUtente(BaseModel):
    nome_utente: str
    ore_settimanali: Optional[float] = None
    note: Optional[str] = None

class ToolRichiediChiarimentoUtente(BaseModel):
    domanda_da_porre: str

class ToolSalvaNotaUtente(BaseModel):
    nome_utente: str
    nota_testuale: str
