import re
from typing import Optional
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from langchain_core.runnables import RunnableConfig
from database.connection import get_collection
from bson import ObjectId

class AggiungiNotaArgs(BaseModel):
    nome_utente: str = Field(description="Il nome dell'utente")
    nota_testuale: str = Field(description="Il testo della nota")

@tool(args_schema=AggiungiNotaArgs)
async def aggiungi_nota_utente(nome_utente: str, nota_testuale: str, config: RunnableConfig) -> str:
    """Aggiunge una nuova nota episodica a un utente per tracciare progressi o avvenimenti."""
    uid = config["configurable"]["user_id"]
    col_utenti = await get_collection(f"utenti", uid)
    pattern = re.compile(f'^{re.escape(nome_utente)}$', re.IGNORECASE)
    
    user = await col_utenti.find_one({"nome": {"$regex": pattern}})
    if not user:
        return f"Errore: Utente '{nome_utente}' non trovato."
        
    note = user.get("note", [])
    new_id = max([n.get("id", 0) for n in note], default=0) + 1
    nuova_nota = {"id": new_id, "testo": nota_testuale}
    
    await col_utenti.update_one(
        {"_id": user["_id"]},
        {"$push": {"note": nuova_nota}}
    )
    return f"Nota (ID {new_id}) aggiunta con successo all'utente {user['nome']}."

class SalvaDiarioArgs(BaseModel):
    data: str = Field(description="Data del diario in formato YYYY-MM-DD")
    utente: str = Field(description="Nome dell'utente")
    testo_generato: str = Field(description="Il testo formattato del diario di bordo")
    note_estratte: list[str] = Field(default=[], description="Elenco opzionale di note estratte automaticamente")

@tool(args_schema=SalvaDiarioArgs)
async def salva_diario_bordo(data: str, utente: str, testo_generato: str, config: RunnableConfig, note_estratte: list[str] = None) -> str:
    """Salva un diario di bordo nel database. Deve essere approvato dall'operatore."""
    uid = config["configurable"]["user_id"]
    col_diari = await get_collection(f"diari_bordo", uid)
    
    doc = {
        "data": data,
        "utente": utente,
        "prompt_originale": config["configurable"].get("original_text", ""),
        "testo_generato": testo_generato,
        "note_estratte": note_estratte or []
    }
    
    await col_diari.insert_one(doc)
    return f"Diario di bordo salvato con successo per {utente} il {data}."
