import re
from typing import Optional
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from langchain_core.runnables import RunnableConfig
from database.connection import get_collection
from bson import ObjectId

class RegistraSessioneArgs(BaseModel):
    Giorno: str = Field(description="Data in formato YYYY-MM-DD", pattern=r"^\d{4}-\d{2}-\d{2}$")
    Ore: float = Field(description="Ore svolte")
    Utente: str = Field(description="Nome dell'utente")
    Luogo: Optional[str] = Field(default=None, description="Luogo dell'incontro")
    Attivita_svolte: str = Field(description="Riassunto delle attività")

@tool(args_schema=RegistraSessioneArgs)
async def registra_sessione(Giorno: str, Ore: float, Utente: str, Attivita_svolte: str, config: RunnableConfig, Luogo: str = None) -> str:
    """Salva una sessione GIA' AVVENUTA in passato o nella giornata di oggi."""
    uid = config["configurable"]["user_id"]
    col_sessioni = await get_collection(f"diario_sessioni", uid)
    
    doc = {
        "data": Giorno,
        "utente_id": Utente,
        "ore_svolte": Ore,
        "testo_riassunto": Attivita_svolte,
        "luogo": Luogo
    }
    await col_sessioni.insert_one(doc)
    return f"✅ Sessione per {Utente} registrata il {Giorno} ({Ore}h)."

class PianificaSessioneArgs(BaseModel):
    Data: str = Field(description="Data in formato YYYY-MM-DD", pattern=r"^\d{4}-\d{2}-\d{2}$")
    Ora_Inizio: str = Field(description="Ora inizio HH:MM", pattern=r"^\d{2}:\d{2}$")
    Ora_Fine: str = Field(description="Ora fine HH:MM", pattern=r"^\d{2}:\d{2}$")
    Utente: str = Field(description="Nome dell'utente")
    Luogo: Optional[str] = Field(default=None, description="Luogo")

@tool(args_schema=PianificaSessioneArgs)
async def pianifica_sessione(Data: str, Ora_Inizio: str, Ora_Fine: str, Utente: str, config: RunnableConfig, Luogo: str = None) -> str:
    """Pianifica un appuntamento FUTURO in agenda."""
    uid = config["configurable"]["user_id"]
    col_prog = await get_collection(f"programmazione", uid)
    
    doc = {
        "data": Data,
        "ora_inizio": Ora_Inizio,
        "ora_fine": Ora_Fine,
        "utente_id": Utente,
        "luogo": Luogo
    }
    await col_prog.insert_one(doc)
    return f"✅ Appuntamento pianificato per {Utente} il {Data} dalle {Ora_Inizio} alle {Ora_Fine}."

class CreaUtenteArgs(BaseModel):
    nome: str = Field(description="Nome e cognome dell'utente")
    ore_settimanali: float = Field(default=0, description="Ore settimanali previste")
    preferenze: Optional[str] = Field(default="", description="Preferenze dell'utente")

@tool(args_schema=CreaUtenteArgs)
async def crea_utente(nome: str, config: RunnableConfig, ore_settimanali: float = 0, preferenze: str = "") -> str:
    """Crea un nuovo utente. Usalo SOLO se l'utente non è nella lista."""
    uid = config["configurable"]["user_id"]
    col_utenti = await get_collection(f"utenti", uid)
    pattern = re.compile(f"^{nome}$", re.IGNORECASE)
    
    existing = await col_utenti.find_one({"nome": {"$regex": pattern}})
    if existing:
        return f"⚠️ Errore: Un utente con nome simile ({existing['nome']}) esiste già."
        
    doc = {
        "nome": nome,
        "ore_settimanali": ore_settimanali,
        "preferenze": preferenze,
        "note": []
    }
    await col_utenti.insert_one(doc)
    return f"✅ Utente {nome} creato con successo."

class EliminaSessionePianificataArgs(BaseModel):
    Data: str = Field(description="Data dell'appuntamento (YYYY-MM-DD)", pattern=r"^\d{4}-\d{2}-\d{2}$")
    Utente: str = Field(description="Nome dell'utente")

@tool(args_schema=EliminaSessionePianificataArgs)
async def elimina_sessione_pianificata(Data: str, Utente: str, config: RunnableConfig) -> str:
    """Annulla e rimuove un appuntamento futuro precedentemente pianificato."""
    uid = config["configurable"]["user_id"]
    col_prog = await get_collection(f"programmazione", uid)
    pattern = re.compile(Utente, re.IGNORECASE)
    
    res = await col_prog.delete_one({"data": Data, "utente_id": {"$regex": pattern}})
    if res.deleted_count > 0:
        return f"✅ Appuntamento rimosso."
    else:
        return f"⚠️ Nessun appuntamento trovato."

class ModificaUtenteArgs(BaseModel):
    nome_utente: str = Field(description="Nome esatto dell'utente")
    ore_settimanali: Optional[float] = Field(default=None, description="Nuove ore settimanali")
    preferenze: Optional[str] = Field(default=None, description="Nuove preferenze")

@tool(args_schema=ModificaUtenteArgs)
async def modifica_utente(nome_utente: str, config: RunnableConfig, ore_settimanali: float = None, preferenze: str = None) -> str:
    """Aggiorna i dati generali di un utente esistente."""
    uid = config["configurable"]["user_id"]
    col_utenti = await get_collection(f"utenti", uid)
    pattern = re.compile(nome_utente, re.IGNORECASE)
    
    update_doc = {}
    if ore_settimanali is not None: update_doc["ore_settimanali"] = ore_settimanali
    if preferenze is not None: update_doc["preferenze"] = preferenze
        
    if not update_doc:
        return "Nessuna modifica richiesta."
        
    res = await col_utenti.update_one({"nome": {"$regex": pattern}}, {"$set": update_doc})
    if res.modified_count > 0:
        return f"✅ Utente aggiornato."
    return "⚠️ Utente non trovato o dati identici."

class EliminaUtenteArgs(BaseModel):
    nome_utente: str = Field(description="Nome esatto dell'utente da eliminare")

@tool(args_schema=EliminaUtenteArgs)
async def elimina_utente(nome_utente: str, config: RunnableConfig) -> str:
    """Elimina definitivamente un utente dal database. ATTENZIONE: azione irreversibile."""
    uid = config["configurable"]["user_id"]
    col_utenti = await get_collection("utenti", uid)
    pattern = re.compile(nome_utente, re.IGNORECASE)
    
    res = await col_utenti.delete_one({"nome": {"$regex": pattern}})
    if res.deleted_count > 0:
        return f"✅ Utente '{nome_utente}' eliminato."
    return "⚠️ Utente non trovato."

class ModificaSessionePianificataArgs(BaseModel):
    Data_Attuale: str = Field(description="Data attuale dell'appuntamento (YYYY-MM-DD)", pattern=r"^\d{4}-\d{2}-\d{2}$")
    Utente: str = Field(description="Nome dell'utente")
    Nuova_Data: Optional[str] = Field(default=None, description="Nuova data (YYYY-MM-DD)", pattern=r"^\d{4}-\d{2}-\d{2}$")
    Nuova_Ora_Inizio: Optional[str] = Field(default=None, description="Nuovo orario inizio (HH:MM)", pattern=r"^\d{2}:\d{2}$")
    Nuova_Ora_Fine: Optional[str] = Field(default=None, description="Nuovo orario fine (HH:MM)", pattern=r"^\d{2}:\d{2}$")
    Nuovo_Luogo: Optional[str] = Field(default=None, description="Nuovo luogo")

@tool(args_schema=ModificaSessionePianificataArgs)
async def modifica_sessione_pianificata(Data_Attuale: str, Utente: str, config: RunnableConfig, Nuova_Data: str = None, Nuova_Ora_Inizio: str = None, Nuova_Ora_Fine: str = None, Nuovo_Luogo: str = None) -> str:
    """Modifica un appuntamento futuro già pianificato."""
    uid = config["configurable"]["user_id"]
    col_prog = await get_collection("programmazione", uid)
    pattern = re.compile(Utente, re.IGNORECASE)
    
    update_doc = {}
    if Nuova_Data: update_doc["data"] = Nuova_Data
    if Nuova_Ora_Inizio: update_doc["ora_inizio"] = Nuova_Ora_Inizio
    if Nuova_Ora_Fine: update_doc["ora_fine"] = Nuova_Ora_Fine
    if Nuovo_Luogo: update_doc["luogo"] = Nuovo_Luogo
    
    if not update_doc:
        return "Nessuna modifica specificata."
    
    res = await col_prog.update_one({"data": Data_Attuale, "utente_id": {"$regex": pattern}}, {"$set": update_doc})
    if res.modified_count > 0:
        return "✅ Appuntamento modificato."
    return "⚠️ Appuntamento non trovato."

class ModificaSessionePassataArgs(BaseModel):
    id_sessione: str = Field(description="ID della sessione nel database")
    Nuova_Data: Optional[str] = Field(default=None, description="Nuova data (YYYY-MM-DD)", pattern=r"^\d{4}-\d{2}-\d{2}$")
    Nuove_Ore: Optional[float] = Field(default=None, description="Nuove ore")
    Nuove_Attivita: Optional[str] = Field(default=None, description="Nuovo riassunto attività")

@tool(args_schema=ModificaSessionePassataArgs)
async def modifica_sessione_passata(id_sessione: str, config: RunnableConfig, Nuova_Data: str = None, Nuove_Ore: float = None, Nuove_Attivita: str = None) -> str:
    """Modifica una sessione già registrata nel diario."""
    uid = config["configurable"]["user_id"]
    col_sessioni = await get_collection("diario_sessioni", uid)
    
    update_doc = {}
    if Nuova_Data: update_doc["data"] = Nuova_Data
    if Nuove_Ore is not None: update_doc["ore_svolte"] = Nuove_Ore
    if Nuove_Attivita: update_doc["testo_riassunto"] = Nuove_Attivita
    
    if not update_doc:
        return "Nessuna modifica specificata."
    
    try:
        res = await col_sessioni.update_one({"_id": ObjectId(id_sessione)}, {"$set": update_doc})
        if res.modified_count > 0:
            return "✅ Sessione modificata."
        return "⚠️ Sessione non trovata."
    except Exception:
        return "⚠️ ID sessione non valido."

class EliminaSessionePassataArgs(BaseModel):
    id_sessione: str = Field(description="ID della sessione da eliminare")

@tool(args_schema=EliminaSessionePassataArgs)
async def elimina_sessione_passata(id_sessione: str, config: RunnableConfig) -> str:
    """Elimina definitivamente una sessione passata dal diario."""
    uid = config["configurable"]["user_id"]
    col_sessioni = await get_collection("diario_sessioni", uid)
    
    try:
        res = await col_sessioni.delete_one({"_id": ObjectId(id_sessione)})
        if res.deleted_count > 0:
            return "✅ Sessione eliminata."
        return "⚠️ Sessione non trovata."
    except Exception:
        return "⚠️ ID sessione non valido."

class ModificaNotaUtenteArgs(BaseModel):
    nome_utente: str = Field(description="Nome dell'utente")
    id_nota: int = Field(description="ID della nota da modificare")
    nuovo_testo: str = Field(description="Nuovo testo della nota")

@tool(args_schema=ModificaNotaUtenteArgs)
async def modifica_nota_utente(nome_utente: str, id_nota: int, nuovo_testo: str, config: RunnableConfig) -> str:
    """Modifica il testo di una nota episodica esistente."""
    uid = config["configurable"]["user_id"]
    col_utenti = await get_collection("utenti", uid)
    pattern = re.compile(nome_utente, re.IGNORECASE)
    
    user = await col_utenti.find_one({"nome": {"$regex": pattern}})
    if not user:
        return f"Errore: Utente '{nome_utente}' non trovato."
    
    note = user.get("note", [])
    found = False
    for n in note:
        if n.get("id") == id_nota:
            n["testo"] = nuovo_testo
            found = True
            break
    
    if not found:
        return f"⚠️ Nota con ID {id_nota} non trovata."
    
    await col_utenti.update_one({"_id": user["_id"]}, {"$set": {"note": note}})
    return f"✅ Nota {id_nota} aggiornata."

class EliminaNotaUtenteArgs(BaseModel):
    nome_utente: str = Field(description="Nome dell'utente")
    id_nota: int = Field(description="ID della nota da eliminare")

@tool(args_schema=EliminaNotaUtenteArgs)
async def elimina_nota_utente(nome_utente: str, id_nota: int, config: RunnableConfig) -> str:
    """Elimina una nota episodica di un utente."""
    uid = config["configurable"]["user_id"]
    col_utenti = await get_collection("utenti", uid)
    pattern = re.compile(nome_utente, re.IGNORECASE)
    
    user = await col_utenti.find_one({"nome": {"$regex": pattern}})
    if not user:
        return f"Errore: Utente '{nome_utente}' non trovato."
    
    note = user.get("note", [])
    new_notes = [n for n in note if n.get("id") != id_nota]
    
    if len(new_notes) == len(note):
        return f"⚠️ Nota con ID {id_nota} non trovata."
    
    await col_utenti.update_one({"_id": user["_id"]}, {"$set": {"note": new_notes}})
    return f"✅ Nota {id_nota} eliminata."
