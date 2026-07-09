import re
from typing import Optional
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from langchain_core.runnables import RunnableConfig
from database.connection import get_collection

class CercaUtentiArgs(BaseModel):
    query: str = Field(description="Nome o parte del nome dell'utente da cercare")

@tool(args_schema=CercaUtentiArgs)
async def cerca_utenti(query: str, config: RunnableConfig) -> str:
    """Cerca nel database il nome completo di un utente. Restituisce anche il suo ID e la lista delle note episodiche con i relativi ID."""
    uid = config["configurable"]["user_id"]
    col_utenti = await get_collection(f"utenti", uid)
    pattern = re.compile(query, re.IGNORECASE)
    cursor = col_utenti.find({"nome": {"$regex": pattern}})
    utenti = await cursor.to_list(length=10)
    
    if not utenti:
        return f"Nessun utente trovato con nome simile a '{query}'."
        
    risposta = f"Utenti trovati (query '{query}'):\n"
    for u in utenti:
        risposta += f"- NOME: {u.get('nome')} | ORE: {u.get('ore_settimanali')} | ID DB: {u['_id']}\n"
        if u.get('preferenze'):
            risposta += f"  PREFERENZE GENERALI: {u.get('preferenze')}\n"
        note = u.get('note', [])
        if note:
            risposta += f"  NOTE EPISODICHE:\n"
            for n in note:
                risposta += f"    [{n['id']}] {n['testo']}\n"
        else:
            risposta += f"  NOTE EPISODICHE: Nessuna.\n"
    return risposta

class LeggiStoricoSessioniArgs(BaseModel):
    utente: str = Field(description="Nome dell'utente")
    limite: int = Field(default=5, description="Numero massimo di sessioni da recuperare")

@tool(args_schema=LeggiStoricoSessioniArgs)
async def leggi_storico_sessioni(utente: str, limite: int, config: RunnableConfig) -> str:
    """Legge le sessioni passate di un utente per ricavare contesto. Restituisce anche l'id di ogni sessione per eventuali modifiche."""
    uid = config["configurable"]["user_id"]
    col_sessioni = await get_collection(f"diario_sessioni", uid)
    cursor = col_sessioni.find({"utente_id": utente}).sort("data", -1).limit(limite)
    sessioni = await cursor.to_list(length=limite)
    
    if not sessioni:
        return f"Nessuno storico trovato per l'utente '{utente}'."
        
    risposta = f"Ultime {len(sessioni)} sessioni registrate per {utente}:\n"
    for s in sessioni:
        risposta += f"-[ID: {s['_id']}] DATA: {s.get('data')} | ORE: {s.get('ore_svolte')} | TESTO: {s.get('testo_riassunto')}\n"
    return risposta

class LeggiAgendaArgs(BaseModel):
    data_inizio: str = Field(description="Data inizio ricerca in formato YYYY-MM-DD", pattern=r"^\d{4}-\d{2}-\d{2}$")
    data_fine: Optional[str] = Field(default=None, description="Data fine ricerca in formato YYYY-MM-DD (opzionale)", pattern=r"^\d{4}-\d{2}-\d{2}$")

@tool(args_schema=LeggiAgendaArgs)
async def leggi_agenda(data_inizio: str, config: RunnableConfig, data_fine: str = None) -> str:
    """Legge gli appuntamenti pianificati nel futuro."""
    uid = config["configurable"]["user_id"]
    col_prog = await get_collection(f"programmazione", uid)
    query = {"data": {"$gte": data_inizio}}
    if data_fine:
        query["data"]["$lte"] = data_fine
        
    cursor = col_prog.find(query).sort("data", 1)
    appuntamenti = await cursor.to_list(length=50)
    
    if not appuntamenti:
        return f"Nessun appuntamento trovato a partire da {data_inizio}."
        
    risposta = f"Agenda dal {data_inizio}:\n"
    for a in appuntamenti:
        risposta += f"- {a.get('data')} | {a.get('ora_inizio')}-{a.get('ora_fine')} | {a.get('utente_id')} ({a.get('luogo')})\n"
    return risposta

class LeggiDiariBordoArgs(BaseModel):
    utente: str = Field(description="Nome dell'utente")
    limite: int = Field(default=3, description="Numero massimo di diari da recuperare")

@tool(args_schema=LeggiDiariBordoArgs)
async def leggi_diari_bordo(utente: str, limite: int, config: RunnableConfig) -> str:
    """Legge i diari di bordo completi (dettagliati) passati di un utente. Restituisce anche l'ID per eventuali modifiche o eliminazioni."""
    uid = config["configurable"]["user_id"]
    col_diari = await get_collection(f"diari_bordo", uid)
    cursor = col_diari.find({"utente": utente}).sort("data", -1).limit(limite)
    diari = await cursor.to_list(length=limite)
    
    if not diari:
        return f"Nessun diario di bordo trovato per l'utente '{utente}'."
        
    risposta = f"Ultimi {len(diari)} diari di bordo per {utente}:\n\n"
    for d in diari:
        risposta += f"=== DIARIO ID: {d['_id']} ===\n"
        risposta += f"DATA: {d.get('data')}\n"
        risposta += f"{d.get('testo_generato')}\n\n"
    return risposta
