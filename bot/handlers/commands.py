import os
from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from database.connection import get_collection

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer("Ciao! Sono Edu-Agent. Usa /aiuto per vedere cosa posso fare.")

@router.message(Command("aiuto"))
async def cmd_aiuto(message: Message):
    help_text = """
Ecco i comandi rapidi a tua disposizione:

/oggi - 📅 Mostra l'agenda della giornata
/utenti - 👥 Mostra la lista degli utenti in carico
/foglio - 📊 Link al file Google Sheets
/esporta - 💾 Esporta tutto il database in CSV
/reset - 🧹 Pulisce la memoria e riavvia l'agente
/aiuto - ℹ️ Mostra questo messaggio

_💡 Suggerimento: Per tutto il resto (creare utenti, registrare sessioni, annullare appuntamenti, ecc.), parla direttamente con me inviandomi un vocale o un messaggio di testo!_
    """
    await message.answer(help_text)

@router.message(Command("foglio"))
async def cmd_foglio(message: Message):
    url = os.getenv("GOOGLE_SHEET_URL", "URL non configurato")
    await message.answer(f"Ecco il link al tuo registro: {url}")

@router.message(Command("reset"))
async def cmd_reset(message: Message, state: FSMContext):
    await state.clear()
    col = await get_collection("chat_history")
    await col.delete_many({"user_id": message.from_user.id})
    await message.answer("🔄 Memoria della chat azzerata! L'agente ha dimenticato il contesto recente e ripartirà da zero.")

@router.message(Command("nuke"))
async def cmd_nuke(message: Message, state: FSMContext):
    from services.sheets_service import clear_all_sheets
    await state.clear()
    
    # Reset DB
    col = await get_collection("chat_history")
    await col.delete_many({})
    col = await get_collection("utenti")
    await col.delete_many({})
    col = await get_collection("programmazione")
    await col.delete_many({})
    col = await get_collection("diario_sessioni")
    await col.delete_many({})
    
    # Reset Fogli Google
    success, msg = await clear_all_sheets()
    
    await message.answer(f"💥 NUKE COMPLETATO: Memoria, DB Utenti, Programmazione e Sessioni azzerati.\n📊 Fogli: {msg}")

@router.message(Command("annulla"))
async def cmd_annulla(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Operazione annullata.")

@router.message(Command("utenti"))
async def cmd_utenti(message: Message):
    col = await get_collection("utenti")
    utenti = await col.find().to_list(length=100)
    msg = "\n".join([f"- {u.get('nome')} ({u.get('ore_settimanali')} ore)" for u in utenti]) if utenti else "Nessun utente."
    await message.answer(f"Utenti attivi:\n{msg}")

from datetime import datetime
from zoneinfo import ZoneInfo
from aiogram.types import FSInputFile
from services.export_service import export_sessions_to_csv
from services.calendar_service import generate_ics_file

from aiogram.fsm.context import FSMContext

@router.message(Command("esporta"))
async def cmd_esporta(message: Message, state: FSMContext):
    await message.answer("Sto esportando i dati, un attimo di pazienza...")
    file_path = await export_sessions_to_csv()
    doc = FSInputFile(file_path)
    await message.answer_document(doc, caption="Ecco il tuo backup in CSV!")
    os.remove(file_path)
    
    # Inject context
    data = await state.get_data()
    messages = data.get("messages", [])
    messages.append({"role": "system", "content": "L'utente ha esportato con successo il database in CSV."})
    await state.update_data(messages=messages)

@router.message(Command("oggi"))
async def cmd_oggi(message: Message, state: FSMContext):
    oggi = datetime.now(ZoneInfo("Europe/Rome")).strftime("%Y-%m-%d")
    col = await get_collection("programmazione")
    # Finding sessions where "Data" matches today
    sessioni = await col.find({"Data": oggi}).to_list(length=20)
    
    if not sessioni:
        return await message.answer("Non hai sessioni programmate per oggi.")
    
    riepilogo = f"📅 **Agenda di Oggi ({oggi}):**\n\n"
    files_to_send = []
    
    for s in sessioni:
        utente = s.get("Utente", "Sconosciuto")
        inizio = s.get("Ora Inizio", "")
        fine = s.get("Ora Fine", "")
        luogo = s.get("Luogo", "")
        
        riepilogo += f"🔹 **{utente}** | {inizio} - {fine} | 📍 {luogo}\n"
        
        filename = f"Sessione_{utente}_{inizio.replace(':', '')}.ics"
        ics_path = generate_ics_file(oggi, inizio, fine, utente, luogo, filename=filename)
        files_to_send.append(ics_path)
        
    await message.answer(riepilogo)
    
    for ics in files_to_send:
        doc = FSInputFile(ics)
        await message.answer_document(doc)
        os.remove(ics)
        
    # Inject context
    data = await state.get_data()
    messages = data.get("messages", [])
    messages.append({"role": "system", "content": f"Il bot ha appena mostrato l'agenda di oggi. Eventi: {sessioni}"})
    await state.update_data(messages=messages)

