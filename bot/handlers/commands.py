import os
from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from database.connection import get_collection

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message):
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from aiogram.types.web_app_info import WebAppInfo
    import os
    
    # Su Render, RENDER_EXTERNAL_URL viene fornita automaticamente.
    # Altrimenti mettiamo un URL di fallback.
    base_url = os.getenv("RENDER_EXTERNAL_URL", "https://il-tuo-sito.com")
    app_url = f"{base_url}/webapp/index.html"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Apri Dati (Mini App)", web_app=WebAppInfo(url=app_url))]
    ])
    
    await message.answer(
        "Ciao! Sono Edu-Agent. Usa /aiuto per vedere cosa posso fare.\n\n"
        "Clicca il bottone qui sotto per visualizzare e modificare le tue sessioni.",
        reply_markup=keyboard
    )

@router.message(Command("aiuto"))
async def cmd_aiuto(message: Message):
    msg1 = (
        "🤖 <b>Benvenuto in EduAgent!</b>\n"
        "Sono il tuo assistente operativo per supportarti nella gestione delle tue attività educative quotidiane.\n\n"
        "🎙️ <b>Come parlarmi:</b>\n"
        "- Puoi inviarmi un <b>messaggio vocale</b>: lo trascriverò e comprenderò immediatamente le tue istruzioni.\n"
        "- Oppure puoi scrivermi un normale <b>messaggio di testo</b>.\n\n"
        "🧠 <b>Come funziona la mia logica (Loop Agentico):</b>\n"
        "- <b>Domande di chiarimento:</b> Se mi chiedi di registrare o pianificare qualcosa ma mancano dei dati fondamentali (es. l'orario o il nome dell'utente), non inventerò nulla: mi fermerò e ti farò una domanda diretta.\n"
        "- <b>Sistema di conferma:</b> Prima di effettuare qualsiasi scrittura, modifica o cancellazione nel Database o sui Fogli Google, ti mostrerò una lista riepilogativa delle azioni e ti chiederò conferma tramite dei <b>bottoni interattivi</b>.\n"
        "- <b>Azioni multiple:</b> Puoi chiedermi più cose contemporaneamente (es: <i>\"Registra la sessione di ieri con Marco e pianifica un incontro con Lucia per venerdì\"</i>) e io metterò in coda tutte le azioni necessarie per te."
    )
    msg2 = (
        "📅 <b>I comandi rapidi a tua disposizione:</b>\n\n"
        "/oggi - Mostra la tua agenda di oggi e ti invia i file <code>.ics</code> pronti da salvare sul calendario del telefono.\n"
        "/utenti - Mostra la lista degli utenti attivi attualmente in carico.\n"
        "/esporta - Genera ed esporta un foglio Excel con tutte le tue sessioni salvate nel database.\n"
        "/log - Genera un file <code>.txt</code> con l'intero storico delle attività/chiamate dell'agente e svuota la tabella dei log su MongoDB.\n"
        "/reset - Svuota la memoria recente della chat (utile se l'agente va in confusione).\n"
        "/nuke - ⚠️ <b>[TEST]</b> Azzera completamente il tuo database (utenti, agenda, storico).\n\n"
        "---\n\n"
        "💡 <b>Esempi di cose che puoi chiedermi a voce o per iscritto:</b>\n\n"
        "• <i>\"Registra: ieri ho fatto 2 ore con Alice in biblioteca, abbiamo fatto analisi logica\"</i>\n"
        "• <i>\"Pianifica: martedì prossimo dalle 15 alle 17 ho un incontro con Marco a domicilio\"</i>\n"
        "• <i>\"Aggiungi un nuovo utente: Sofia, 4 ore settimanali, preferisce attività grafiche\"</i>\n"
        "• <i>\"Salva nota per Sofia: Ricordati che è allergica alle fragole\"</i>\n"
        "• <i>\"Mostrami le ultime sessioni di Alice\"</i>\n"
        "• <i>\"Cosa ho in agenda per la prossima settimana?\"</i>\n"
        "• <i>\"Modifica le ore settimanali di Marco a 6 ore\"</i>"
    )
    await message.answer(msg1, parse_mode="HTML")
    await message.answer(msg2, parse_mode="HTML")


@router.message(Command("reset"))
async def cmd_reset(message: Message, state: FSMContext):
    await state.clear()
    col = await get_collection("chat_history")
    await col.delete_many({"user_id": message.from_user.id})
    await message.answer("🔄 Memoria della chat azzerata! L'agente ha dimenticato il contesto recente e ripartirà da zero.")

@router.message(Command("nuke"))
async def cmd_nuke(message: Message, state: FSMContext):
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
    
    await message.answer("💥 NUKE COMPLETATO: Memoria, DB Utenti, Programmazione e Sessioni azzerati per questo account.")

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
from services.export_service import export_sessions_to_excel
from services.calendar_service import generate_ics_file

from aiogram.fsm.context import FSMContext

@router.message(Command("esporta"))
async def cmd_esporta(message: Message, state: FSMContext):
    await message.answer("Sto generando il tuo Excel, un attimo di pazienza...")
    user_id = str(message.from_user.id)
    file_path = await export_sessions_to_excel(user_id=user_id)
    doc = FSInputFile(file_path)
    await message.answer_document(doc, caption="Ecco il tuo file Excel aggiornato!")
    os.remove(file_path)
    
    # Inject context
    data = await state.get_data()
    messages = data.get("messages", [])
    messages.append({"role": "system", "content": "L'utente ha esportato con successo il database in Excel."})
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

@router.message(Command("log"))
async def cmd_log(message: Message):
    await message.answer("Recupero i log dal database, attendi...")
    col = await get_collection("system_logs")
    logs = await col.find().sort("timestamp", 1).to_list(length=None)
    
    if not logs:
        return await message.answer("Nessun log presente nel database.")
        
    file_path = "system_logs_export.txt"
    with open(file_path, "w", encoding="utf-8") as f:
        for log in logs:
            ts = log.get("timestamp")
            if ts:
                ts_str = ts.strftime("%Y-%m-%d %H:%M:%S")
            else:
                ts_str = "N/A"
            lvl = log.get("level", "INFO")
            mod = log.get("module", "unknown")
            msg = log.get("message", "")
            f.write(f"[{ts_str}] {lvl} [{mod}] - {msg}\n")
            
            details = log.get("details")
            if details:
                f.write(f"  Details: {details}\n")
                
    doc = FSInputFile(file_path)
    await message.answer_document(doc, caption="Ecco tutti i log registrati. Ora verranno cancellati dal database.")
    
    os.remove(file_path)
    
    # Cancella i log dal db
    await col.delete_many({})
    await message.answer("✅ Tutti i log sono stati eliminati dal database.")
