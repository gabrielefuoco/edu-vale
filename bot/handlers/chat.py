import json
import io
import csv
import re
import csv
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import List

from pydantic import ValidationError
from database.models import (
    ToolRegistraSessione, ToolPianificaSessione, ToolCreaUtente, 
    ToolCercaUtenti, ToolLeggiStoricoSessioni, ToolLeggiAgenda, 
    ToolEliminaSessionePianificata, ToolModificaUtente, ToolRichiediChiarimentoUtente,
    ToolSalvaNotaUtente
)

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from database.connection import get_collection
from services.ai_agent import chat_with_agent, summarize_context
from services.sheets_service import append_session_to_sheet

TOOL_MODELS = {
    "registra_sessione": ToolRegistraSessione,
    "pianifica_sessione": ToolPianificaSessione,
    "crea_utente": ToolCreaUtente,
    "cerca_utenti": ToolCercaUtenti,
    "leggi_storico_sessioni": ToolLeggiStoricoSessioni,
    "leggi_agenda": ToolLeggiAgenda,
    "elimina_sessione_pianificata": ToolEliminaSessionePianificata,
    "modifica_utente": ToolModificaUtente,
    "richiedi_chiarimento_utente": ToolRichiediChiarimentoUtente,
    "salva_nota_utente": ToolSalvaNotaUtente
}

def format_for_telegram(text: str) -> str:
    """Converte la sintassi Markdown di base nell'HTML di Telegram."""
    # Sostituisce **testo** con <b>testo</b>
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    # Sostituisce _testo_ con <i>testo</i> (opzionale)
    text = re.sub(r'_(.*?)_', r'<i>\1</i>', text)
    
    # Assicurati di sfuggire i caratteri speciali HTML <, >, & se Mistral li genera
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    
    # Ripristina i tag HTML che abbiamo appena sfuggito
    text = text.replace("&lt;b&gt;", "<b>").replace("&lt;/b&gt;", "</b>")
    text = text.replace("&lt;i&gt;", "<i>").replace("&lt;/i&gt;", "</i>")
    
    return text

def format_tool_args(args: dict) -> str:
    return "\n".join([f"• **{k}**: {v}" for k, v in args.items()])

router = Router()

async def get_system_prompt() -> dict:
    oggi = datetime.now(ZoneInfo("Europe/Rome")).strftime('%Y-%m-%d')
    col = await get_collection("utenti")
    utenti = await col.find().to_list(length=100)
    utenti_str = ", ".join([u.get('nome') for u in utenti]) if utenti else "Nessuno"
    
    col_prog = await get_collection("programmazione")
    agenda_oggi = await col_prog.find({"Data": oggi}).sort("Ora Inizio", 1).to_list(length=50)
    if agenda_oggi:
        agenda_str = "\n".join([f"- {a.get('Ora Inizio')}-{a.get('Ora Fine')} : {a.get('Utente')} ({a.get('Luogo', 'N/D')})" for a in agenda_oggi])
    else:
        agenda_str = "Nessun appuntamento in agenda per oggi."
        
    return {
        "role": "system",
        "content": (
            f"Sei l'assistente IA operativo di un'educatrice. Oggi è {oggi}.\n"
            f"Gli utenti attualmente in carico sono: {utenti_str}.\n"
            f"📍 LA TUA AGENDA DI OGGI:\n{agenda_str}\n\n"
            "Il tuo scopo è estrarre dati strutturati per eseguire i Tool a tua disposizione "
            "(registra_sessione, pianifica_sessione, crea_utente, cerca_utenti, leggi_storico_sessioni, leggi_agenda, elimina_sessione_pianificata, modifica_utente, richiedi_chiarimento_utente). "
            "REGOLE DI COMPORTAMENTO (AGENTE RE-ACT):\n"
            "1. RAGIONAMENTO E VERIFICA: Valuta sempre se hai tutti i dati prima di agire. Se un nome è ambiguo, usa 'cerca_utenti'. PRIMA di eliminare o modificare appuntamenti in blocco, DEVI TASSATIVAMENTE usare 'leggi_agenda' per verificare cosa esiste realmente. Non tirare a indovinare date o nomi se non sei sicuro che esistano.\n"
            "2. MULTI-TOOL: Puoi chiamare più tool contemporaneamente (es. registrare 3 sessioni diverse in un solo colpo).\n"
            "3. DOMANDE ESPLICITE: Se mancano parametri obbligatori e non puoi dedurli dal contesto o dai read-tools, USA IL TOOL 'richiedi_chiarimento_utente'. Non chiedere cose scrivendo testo libero.\n"
            "4. STILE: Mantieni un tono essenziale, professionale e oggettivo. Niente consigli, niente convenevoli.\n"
            "5. FORMATTAZIONE: Non usare MAI il Markdown (come gli asterischi **). Se devi evidenziare qualcosa in grassetto, usa esclusivamente i tag HTML <b>testo</b>."
        )
    }

@router.message((F.text & ~F.text.startswith("/")) | F.voice)
async def chat_handler(message: Message, state: FSMContext):
    data = await state.get_data()
    messages = data.get("messages", [])
    
    if not messages:
        messages = [await get_system_prompt()]
    
    # Auto-summarize if context grows too large (e.g. > 30000 chars)
    total_chars = sum(len(m.get("content", "")) for m in messages if m.get("content"))
    if total_chars > 30000:
        await message.bot.send_chat_action(message.chat.id, "typing")
        summary_messages = await summarize_context(messages)
        messages = [await get_system_prompt()] + summary_messages
    
    # Handle voice messages
    if message.voice:
        await message.bot.send_chat_action(message.chat.id, "typing")
        file = await message.bot.get_file(message.voice.file_id)
        file_path = f"tmp_{message.voice.file_id}.ogg"
        await message.bot.download_file(file.file_path, file_path)
        
        from services.ai_service import transcribe_audio
        import os
        transcribed_text = await transcribe_audio(file_path)
        os.remove(file_path)
        
        await message.answer(f"🎙️ <b>Trascrizione (Groq Whisper):</b>\n<i>{transcribed_text}</i>", parse_mode="HTML")
        user_input = transcribed_text
    else:
        user_input = message.text

    # Append user message
    messages.append({"role": "user", "content": user_input})
    await message.bot.send_chat_action(message.chat.id, "typing")
    
    MAX_LOOP = 5
    loop_count = 0
    pending_write_tools = []
    
    while loop_count < MAX_LOOP:
        loop_count += 1
        bot_msg, tool_calls = await chat_with_agent(messages)
        
        if not tool_calls:
            # End of agentic loop, no more tools
            messages.append({"role": "assistant", "content": bot_msg.content})
            await state.update_data(messages=messages)
            if bot_msg.content:
                testo_pulito = format_for_telegram(bot_msg.content)
                try:
                    await message.answer(testo_pulito, parse_mode="HTML")
                except Exception as e:
                    await message.answer(bot_msg.content.replace("**", "").replace("<", "").replace(">", ""))
            return
            
        # We have tool calls
        # Append assistant message with tool_calls
        tc_dicts = [{"id": tc.id, "function": {"name": tc.function.name, "arguments": tc.function.arguments}} for tc in tool_calls]
        messages.append({"role": "assistant", "content": bot_msg.content or "", "tool_calls": tc_dicts})
        
        has_read_tools = False
        
        for tc in tool_calls:
            fn_name = tc.function.name
            try:
                fn_args = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                fn_args = {}
                
            # Self-Reflection (Validazione Pydantic)
            model_cls = TOOL_MODELS.get(fn_name)
            if model_cls:
                try:
                    # Validiamo e dumpo gestendo gli alias (es. "Attività svolte")
                    fn_args = model_cls(**fn_args).model_dump(by_alias=True)
                except ValidationError as e:
                    error_msg = str(e).replace('\n', ' ')
                    messages.append({"role": "tool", "name": fn_name, "content": f"Errore di validazione Pydantic: {error_msg}. Correggi la tua chiamata.", "tool_call_id": tc.id})
                    has_read_tools = True
                    continue # Continua il ciclo while per permettere a Mistral di auto-correggersi
                
            if fn_name == "richiedi_chiarimento_utente":
                domanda = fn_args.get("domanda_da_porre", "Puoi chiarire?")
                messages.append({"role": "tool", "name": fn_name, "content": "Domanda inviata all'utente. In attesa di risposta testuale.", "tool_call_id": tc.id})
                await state.update_data(messages=messages, pending_tools_queue=[]) # Scartiamo eventuali write tools in coda per non incartare lo stato
                await message.answer(f"❓ {domanda}")
                return # Interrompiamo il loop agentico e mettiamoci in ascolto
                
            elif fn_name == "cerca_utenti":
                has_read_tools = True
                query = fn_args.get("query", "")
                col = await get_collection("utenti")
                
                try:
                    # Fuzzy Search con Atlas
                    pipeline = [{"$search": {"index": "default", "text": {"query": query, "path": "nome", "fuzzy": {}}}}]
                    utenti = await col.aggregate(pipeline).to_list(10)
                except Exception:
                    # Fallback robusto al Regex se l'indice non esiste su Atlas
                    utenti = await col.find({"nome": {"$regex": query, "$options": "i"}}).to_list(10)
                
                if utenti:
                    res_str = "Utenti trovati:\n" + "\n".join([f"- {u.get('nome')} (Ore: {u.get('ore_settimanali', 0)}), Note: {u.get('note', '')}, Preferenze Episodiche: {u.get('preferenze', [])}" for u in utenti])
                else:
                    res_str = "Nessun utente trovato con quel nome."
                messages.append({"role": "tool", "name": fn_name, "content": res_str, "tool_call_id": tc.id})
                
            elif fn_name == "leggi_storico_sessioni":
                has_read_tools = True
                utente = fn_args.get("utente", "")
                limite = fn_args.get("limite", 5)
                col = await get_collection("diario_sessioni")
                res = await col.find({"parsed.Utente": {"$regex": utente, "$options": "i"}}).sort("timestamp", -1).limit(limite).to_list(limite)
                if not res:
                    res_str = "Nessuna sessione trovata per questo utente."
                else:
                    res_str = json.dumps([r["parsed"] for r in res])
                messages.append({"role": "tool", "name": fn_name, "content": res_str, "tool_call_id": tc.id})
                
            elif fn_name == "leggi_agenda":
                has_read_tools = True
                data_inizio = fn_args.get("data_inizio", "")
                data_fine = fn_args.get("data_fine", "")
                col = await get_collection("programmazione")
                query = {"Data": {"$gte": data_inizio}}
                if data_fine:
                    query["Data"]["$lte"] = data_fine
                res = await col.find(query).sort("Data", 1).to_list(20)
                if not res:
                    res_str = "Nessun appuntamento in agenda per il periodo specificato."
                else:
                    res_str = json.dumps([{"Data": r.get("Data"), "Utente": r.get("Utente"), "Inizio": r.get("Ora Inizio"), "Fine": r.get("Ora Fine")} for r in res])
                messages.append({"role": "tool", "name": fn_name, "content": res_str, "tool_call_id": tc.id})
                
            else:
                # Write tools: registra_sessione, pianifica_sessione, crea_utente, elimina_sessione_pianificata, modifica_utente
                pending_write_tools.append({"name": fn_name, "args": fn_args, "id": tc.id})
                messages.append({"role": "tool", "name": fn_name, "content": "Azione messa in coda. In attesa di conferma dall'utente.", "tool_call_id": tc.id})
                
        # If there are only write tools, stop the loop and ask for confirmation
        if not has_read_tools and pending_write_tools:
            break
            
        # If we have read tools, continue loop to let Agent reason with DB results
        
    if pending_write_tools:
        await state.update_data(
            pending_tools_queue=pending_write_tools,
            messages=messages
        )
        
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Conferma Tutto in Blocco", callback_data="confirm_all")],
            [InlineKeyboardButton(text="➡️ Conferma Singolarmente", callback_data="confirm_single")],
            [InlineKeyboardButton(text="❌ Annulla Tutto", callback_data="cancel_all")]
        ])
        
        testo_azioni = "L'agente vuole eseguire le seguenti azioni:\n\n"
        for i, pt in enumerate(pending_write_tools, 1):
            testo_azioni += f"{i}. <b>{pt['name']}</b>\n"
            for k, v in pt['args'].items():
                testo_azioni += f"   - {k}: {v}\n"
            testo_azioni += "\n"
            
        testo_azioni += "Cosa vuoi fare?"
        
        await message.answer(format_for_telegram(testo_azioni), reply_markup=markup, parse_mode="HTML")
        return

@router.callback_query(F.data == "confirm_all")
async def confirm_all_tools(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    queue = data.get("pending_tools_queue", [])
    messages = data.get("messages", [])
    
    if not queue:
        return await callback.message.edit_text("Nessuna azione in coda.")
        
    res_text = "✅ <b>Risultati esecuzione in blocco:</b>\n\n"
    
    for tool in queue:
        fn_name = tool["name"]
        fn_args = tool["args"]
        
        if fn_name == "registra_sessione":
            success, msg = await append_session_to_sheet(fn_args)
            col = await get_collection("diario_sessioni")
            await col.insert_one({"parsed": fn_args, "timestamp": datetime.now(ZoneInfo("Europe/Rome"))})
            
            icona = "✅" if success else "⚠️"
            res_text += f"- Sessione registrata: {fn_args.get('Utente')} ({fn_args.get('Ore')}h). {msg}\n"
            messages.append({"role": "system", "content": f"Azione '{fn_name}' confermata: Sessione registrata. Sheets: {msg}"})
            
        elif fn_name == "pianifica_sessione":
            col = await get_collection("programmazione")
            await col.insert_one(fn_args)
            res_text += f"- Sessione pianificata: {fn_args.get('Utente')} il {fn_args.get('Data')}\n"
            messages.append({"role": "system", "content": f"Azione '{fn_name}' confermata: Sessione pianificata con successo."})
            
        elif fn_name == "crea_utente":
            col = await get_collection("utenti")
            existing = await col.find_one({"nome": {"$regex": f"^{fn_args.get('nome')}$", "$options": "i"}})
            if not existing:
                await col.insert_one({
                    "nome": fn_args.get("nome"),
                    "ore_settimanali": fn_args.get("ore_settimanali", 0),
                    "note": fn_args.get("note", ""),
                    "preferenze": []
                })
                res_text += f"- Utente creato: {fn_args.get('nome')}\n"
                messages.append({"role": "system", "content": f"Azione '{fn_name}' confermata: Utente creato con successo."})
            else:
                res_text += f"- Creazione ignorata: {fn_args.get('nome')} esiste già.\n"
                messages.append({"role": "system", "content": f"Azione '{fn_name}' ignorata: L'utente esisteva già."})
            
        elif fn_name == "elimina_sessione_pianificata":
            col = await get_collection("programmazione")
            result = await col.delete_one({"Data": fn_args.get("Data"), "Utente": {"$regex": fn_args.get("Utente", ""), "$options": "i"}})
            if result.deleted_count > 0:
                res_text += f"- Sessione annullata: {fn_args.get('Utente')} il {fn_args.get('Data')}\n"
                messages.append({"role": "system", "content": f"Azione '{fn_name}' confermata: Sessione annullata con successo."})
            else:
                res_text += f"- Impossibile annullare: nessuna sessione trovata per {fn_args.get('Utente')} il {fn_args.get('Data')}\n"
                messages.append({"role": "system", "content": f"Azione '{fn_name}' fallita: Nessuna sessione trovata da annullare."})
                
        elif fn_name == "modifica_utente":
            col = await get_collection("utenti")
            update_data = {}
            if "ore_settimanali" in fn_args:
                update_data["ore_settimanali"] = fn_args["ore_settimanali"]
            if "note" in fn_args:
                update_data["note"] = fn_args["note"]
                
            if update_data:
                await col.update_one({"nome": {"$regex": fn_args.get("nome_utente", ""), "$options": "i"}}, {"$set": update_data})
                res_text += f"- Utente {fn_args.get('nome_utente', '')} aggiornato.\n"
                messages.append({"role": "system", "content": f"Azione '{fn_name}' confermata: Utente aggiornato con successo."})
            else:
                res_text += f"- Nessun campo da aggiornare per {fn_args.get('nome_utente', '')}.\n"
                messages.append({"role": "system", "content": f"Azione '{fn_name}' ignorata: Nessuna modifica specificata."})

        elif fn_name == "salva_nota_utente":
            col = await get_collection("utenti")
            await col.update_one(
                {"nome": {"$regex": fn_args.get("nome_utente", ""), "$options": "i"}},
                {"$push": {"preferenze": fn_args.get("nota_testuale")}}
            )
            res_text += f"- Nota salvata in memoria per {fn_args.get('nome_utente')}.\n"
            messages.append({"role": "system", "content": f"Azione '{fn_name}' confermata: Nota utente salvata in memoria episodica."})
            
    await state.update_data(pending_tools_queue=[], messages=messages)
    await callback.message.edit_text(format_for_telegram(res_text), parse_mode="HTML")

@router.callback_query(F.data == "confirm_single")
async def start_single_confirmation(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    queue = data.get("pending_tools_queue", [])
    
    if not queue:
        return await callback.message.edit_text("Nessuna azione in coda.")
        
    first_tool = queue.pop(0)
    await state.update_data(
        pending_tool=first_tool["name"],
        pending_args=first_tool["args"],
        pending_tool_id=first_tool["id"],
        pending_tools_queue=queue
    )
    
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Conferma Azione", callback_data="confirm_tool")],
        [InlineKeyboardButton(text="❌ Annulla Azione", callback_data="cancel_tool")]
    ])
    
    queue_msg = f" (1 di {len(queue) + 1})"
    formatted_args = format_tool_args(first_tool['args'])
    
    await callback.message.edit_text(
        format_for_telegram(f"Azione in sospeso {queue_msg}:\n<b>{first_tool['name']}</b>\n\n{formatted_args}\n\nConfermi?"),
        reply_markup=markup,
        parse_mode="HTML"
    )

@router.callback_query(F.data == "cancel_all")
async def cancel_all_tools(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    messages = data.get("messages", [])
    messages.append({"role": "system", "content": "L'utente ha annullato tutte le operazioni in sospeso."})
    await state.update_data(messages=messages, pending_tools_queue=[])
    await callback.message.edit_text("❌ Tutte le operazioni annullate.")

@router.callback_query(F.data == "confirm_tool")
async def confirm_tool_call(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    fn_name = data.get("pending_tool")
    fn_args = data.get("pending_args")
    fn_id = data.get("pending_tool_id", "dummy")
    messages = data.get("messages", [])
    
    if not fn_name:
        return await callback.message.edit_text("Nessuna azione in sospeso.")
    
    if fn_name == "registra_sessione":
        success, msg = await append_session_to_sheet(fn_args)
        col = await get_collection("diario_sessioni")
        await col.insert_one({"parsed": fn_args, "timestamp": datetime.now(ZoneInfo("Europe/Rome"))})
        
        icona = "✅" if success else "⚠️"
        res_text = f"✅ Sessione registrata: {fn_args.get('Utente')}. {msg}"
        messages.append({"role": "system", "content": f"Azione '{fn_name}' confermata: Sessione registrata. Sheets: {msg}"})
        
    elif fn_name == "pianifica_sessione":
        col = await get_collection("programmazione")
        await col.insert_one(fn_args)
        res_text = "✅ Sessione pianificata."
        messages.append({"role": "system", "content": f"Azione '{fn_name}' confermata: Sessione pianificata con successo."})
        
    elif fn_name == "crea_utente":
        col = await get_collection("utenti")
        existing = await col.find_one({"nome": {"$regex": f"^{fn_args.get('nome')}$", "$options": "i"}})
        if not existing:
            await col.insert_one({
                "nome": fn_args.get("nome"),
                "ore_settimanali": fn_args.get("ore_settimanali", 0),
                "note": fn_args.get("note", ""),
                "preferenze": fn_args.get("preferenze", [])
            })
            res_text = "✅ Utente creato."
            messages.append({"role": "system", "content": f"Azione '{fn_name}' confermata: Utente creato con successo."})
        else:
            res_text = "⚠️ Utente già esistente."
            messages.append({"role": "system", "content": f"Azione '{fn_name}' ignorata: L'utente esisteva già."})
        
    elif fn_name == "elimina_sessione_pianificata":
        col = await get_collection("programmazione")
        result = await col.delete_one({"Data": fn_args.get("Data"), "Utente": {"$regex": fn_args.get("Utente", ""), "$options": "i"}})
        if result.deleted_count > 0:
            res_text = "✅ Sessione annullata."
            messages.append({"role": "system", "content": f"Azione '{fn_name}' confermata: Sessione annullata con successo."})
        else:
            res_text = "⚠️ Impossibile annullare: sessione non trovata."
            messages.append({"role": "system", "content": f"Azione '{fn_name}' fallita: Nessuna sessione trovata da annullare."})
            
    elif fn_name == "modifica_utente":
        col = await get_collection("utenti")
        update_data = {}
        if "ore_settimanali" in fn_args:
            update_data["ore_settimanali"] = fn_args["ore_settimanali"]
        if "note" in fn_args:
            update_data["note"] = fn_args["note"]
            
        if update_data:
            await col.update_one({"nome": {"$regex": fn_args.get("nome_utente", ""), "$options": "i"}}, {"$set": update_data})
            res_text = "✅ Utente aggiornato."
            messages.append({"role": "system", "content": f"Azione '{fn_name}' confermata: Utente aggiornato con successo."})
        else:
            res_text = "⚠️ Nessun campo da aggiornare."
            messages.append({"role": "system", "content": f"Azione '{fn_name}' ignorata: Nessuna modifica specificata."})
            
    elif fn_name == "salva_nota_utente":
        col = await get_collection("utenti")
        await col.update_one(
            {"nome": {"$regex": fn_args.get("nome_utente", ""), "$options": "i"}},
            {"$push": {"preferenze": fn_args.get("nota_testuale")}}
        )
        res_text = "✅ Nota salvata."
        messages.append({"role": "system", "content": f"Azione '{fn_name}' confermata: Nota utente salvata in memoria episodica."})
        
    else:
        res_text = "Errore: Tool sconosciuto."
        messages.append({"role": "system", "content": f"Azione '{fn_name}' fallita: Tool sconosciuto."})
    
    queue = data.get("pending_tools_queue", [])
    if queue:
        next_tool = queue.pop(0)
        await state.update_data(
            messages=messages, 
            pending_tool=next_tool["name"], 
            pending_args=next_tool["args"],
            pending_tool_id=next_tool["id"],
            pending_tools_queue=queue
        )
        
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Conferma Azione", callback_data="confirm_tool")],
            [InlineKeyboardButton(text="❌ Annulla", callback_data="cancel_tool")]
        ])
        
        queue_msg = f" (rimanenti in coda: {len(queue)})" if queue else " (ultimo in coda)"
        formatted_args = format_tool_args(next_tool['args'])
        
        await callback.message.edit_text(
            format_for_telegram(f"{res_text}\n\nAzione successiva:\n<b>{next_tool['name']}</b>{queue_msg}\n\n{formatted_args}\n\nConfermi?"), 
            reply_markup=markup,
            parse_mode="HTML"
        )
    else:
        await state.update_data(messages=messages, pending_tool=None, pending_args=None, pending_tool_id=None, pending_tools_queue=[])
        await callback.message.edit_text(format_for_telegram(f"{res_text}\n\n✅ Tutte le azioni richieste sono state completate."), parse_mode="HTML")

@router.callback_query(F.data == "cancel_tool")
async def cancel_tool_call(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    messages = data.get("messages", [])
    fn_name = data.get("pending_tool")
    
    # Aggiorna i messaggi per informare Mistral dell'annullamento
    messages.append({"role": "system", "content": f"L'utente ha annullato l'azione '{fn_name}'."})
    
    # Rimuoviamo il tool dalla coda in attesa
    queue = data.get("pending_tools_queue", [])
    if queue:
        next_tool = queue.pop(0)
        await state.update_data(
            messages=messages, 
            pending_tool=next_tool["name"], 
            pending_args=next_tool["args"],
            pending_tool_id=next_tool["id"],
            pending_tools_queue=queue
        )
        
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Conferma Azione", callback_data="confirm_tool")],
            [InlineKeyboardButton(text="❌ Annulla", callback_data="cancel_tool")]
        ])
        
        queue_msg = f" (rimanenti in coda: {len(queue)})" if queue else " (ultimo in coda)"
        formatted_args = format_tool_args(next_tool['args'])
        
        await callback.message.edit_text(
            format_for_telegram(f"❌ Azione '{fn_name}' annullata.\n\nAzione successiva:\n<b>{next_tool['name']}</b>{queue_msg}\n\n{formatted_args}\n\nConfermi?"), 
            reply_markup=markup,
            parse_mode="HTML"
        )
    else:
        await state.update_data(messages=messages, pending_tool=None, pending_args=None, pending_tool_id=None, pending_tools_queue=[])
        await callback.message.edit_text(format_for_telegram(f"❌ Azione '{fn_name}' annullata.\n\nCoda svuotata."), parse_mode="HTML")
