import json
from datetime import datetime
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from services.ai_agent import chat_with_agent, summarize_context
from database.connection import get_collection
from services.sheets_service import append_session_to_sheet

from services.sheets_service import append_session_to_sheet

def format_tool_args(args: dict) -> str:
    return "\n".join([f"• **{k}**: {v}" for k, v in args.items()])

router = Router()

def get_system_prompt() -> dict:
    oggi = datetime.now().strftime('%Y-%m-%d')
    return {
        "role": "system",
        "content": (
            f"Sei l'assistente IA operativo di un'educatrice. Oggi è {oggi}. "
            "Il tuo unico scopo è estrarre dati strutturati per eseguire i Tool a tua disposizione "
            "(registra_sessione o pianifica_sessione). "
            "REGOLE RIGIDE:\n"
            "- Mantieni un tono essenziale, professionale e oggettivo.\n"
            "- NON fornire consigli didattici, psicologici o educativi.\n"
            "- NON fare complimenti, NON congratularti e NON usare esclamazioni emotive.\n"
            "- Se mancano parametri obbligatori per un tool, chiedili in modo diretto, secco e focalizzato solo sui dati mancanti, senza preamboli."
        )
    }

@router.message((F.text & ~F.text.startswith("/")) | F.voice)
async def chat_handler(message: Message, state: FSMContext):
    data = await state.get_data()
    messages = data.get("messages", [])
    
    if not messages:
        messages = [get_system_prompt()]
    
    # Auto-summarize if context grows too large (e.g. > 30000 chars)
    total_chars = sum(len(m.get("content", "")) for m in messages if m.get("content"))
    if total_chars > 30000:
        await message.bot.send_chat_action(message.chat.id, "typing")
        summary_messages = await summarize_context(messages)
        messages = [get_system_prompt()] + summary_messages
    
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
        
        await message.answer(f"🎙️ **Trascrizione (Groq Whisper):**\n_{transcribed_text}_", parse_mode="Markdown")
        user_input = transcribed_text
    else:
        user_input = message.text

    # Append user message
    messages.append({"role": "user", "content": user_input})
    await message.bot.send_chat_action(message.chat.id, "typing")
    
    # Call Mistral
    bot_msg, tool_calls = await chat_with_agent(messages)
    
    # Se non ci sono chiamate ai Tool, risponde e basta
    if not tool_calls:
        messages.append({"role": "assistant", "content": bot_msg.content})
        await state.update_data(messages=messages)
        try:
            await message.answer(bot_msg.content, parse_mode="Markdown")
        except Exception:
            # Fallback se il markdown generato ha sintassi non valida per Telegram
            await message.answer(bot_msg.content)
        return
        
    # Handle Tool Calls
    if tool_calls:
        # Convertiamo i tool calls in una lista di dizionari per metterli in coda
        tools_list = [{"name": tc.function.name, "args": json.loads(tc.function.arguments)} for tc in tool_calls]
        first_tool = tools_list.pop(0)
        
        # Salviamo la coda e il tool corrente nello stato FSM
        await state.update_data(
            pending_tool=first_tool["name"],
            pending_args=first_tool["args"],
            pending_tools_queue=tools_list,
            messages=messages
        )
        
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Conferma Azione", callback_data="confirm_tool")],
            [InlineKeyboardButton(text="❌ Annulla", callback_data="cancel_tool")]
        ])
        
        queue_msg = f" (1 di {len(tools_list) + 1})" if tools_list else ""
        formatted_args = format_tool_args(first_tool['args'])
        
        try:
            await message.answer(
                f"L'agente vuole eseguire l'azione: **{first_tool['name']}**{queue_msg}\n\n{formatted_args}\n\nConfermi?",
                reply_markup=markup,
                parse_mode="Markdown"
            )
        except Exception:
            await message.answer(
                f"L'agente vuole eseguire l'azione: {first_tool['name']}{queue_msg}\n\n{formatted_args}\n\nConfermi?",
                reply_markup=markup
            )
        return

@router.callback_query(F.data == "confirm_tool")
async def confirm_tool_call(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    fn_name = data.get("pending_tool")
    fn_args = data.get("pending_args")
    messages = data.get("messages", [])
    
    if not fn_name:
        return await callback.message.edit_text("Nessuna azione in sospeso.")
    
    if fn_name == "registra_sessione":
        append_session_to_sheet(fn_args)
        col = await get_collection("diario_sessioni")
        await col.insert_one({"parsed": fn_args, "timestamp": datetime.now()})
        res_text = "✅ Sessione registrata nel DB e nel Foglio Google."
        
    elif fn_name == "pianifica_sessione":
        col = await get_collection("programmazione")
        await col.insert_one(fn_args)
        res_text = "✅ Sessione pianificata in agenda."
        
    else:
        res_text = "Errore: Tool sconosciuto."
        
    # Append the action result to the context so Mistral knows it was executed
    messages.append({"role": "system", "content": f"Azione {fn_name} eseguita con successo dall'utente."})
    
    queue = data.get("pending_tools_queue", [])
    if queue:
        next_tool = queue.pop(0)
        await state.update_data(
            messages=messages, 
            pending_tool=next_tool["name"], 
            pending_args=next_tool["args"],
            pending_tools_queue=queue
        )
        
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Conferma Azione", callback_data="confirm_tool")],
            [InlineKeyboardButton(text="❌ Annulla", callback_data="cancel_tool")]
        ])
        
        queue_msg = f" (rimanenti in coda: {len(queue)})" if queue else " (ultimo in coda)"
        formatted_args = format_tool_args(next_tool['args'])
        
        try:
            await callback.message.edit_text(
                f"{res_text}\n\nAzione successiva:\n**{next_tool['name']}**{queue_msg}\n\n{formatted_args}\n\nConfermi?", 
                reply_markup=markup,
                parse_mode="Markdown"
            )
        except Exception:
            await callback.message.edit_text(
                f"{res_text}\n\nAzione successiva:\n{next_tool['name']}{queue_msg}\n\n{formatted_args}\n\nConfermi?", 
                reply_markup=markup
            )
    else:
        await state.update_data(messages=messages, pending_tool=None, pending_args=None, pending_tools_queue=[])
        await callback.message.edit_text(f"{res_text}\n\n✅ Tutte le azioni richieste sono state completate.")

@router.callback_query(F.data == "cancel_tool")
async def cancel_tool_call(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    messages = data.get("messages", [])
    fn_name = data.get("pending_tool")
    
    messages.append({"role": "system", "content": f"L'utente ha annullato l'azione {fn_name}. Attendi che fornisca le correzioni per ritentare."})
    
    queue = data.get("pending_tools_queue", [])
    if queue:
        next_tool = queue.pop(0)
        await state.update_data(
            messages=messages, 
            pending_tool=next_tool["name"], 
            pending_args=next_tool["args"],
            pending_tools_queue=queue
        )
        
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Conferma Azione", callback_data="confirm_tool")],
            [InlineKeyboardButton(text="❌ Annulla", callback_data="cancel_tool")]
        ])
        
        queue_msg = f" (rimanenti in coda: {len(queue)})" if queue else " (ultimo in coda)"
        formatted_args = format_tool_args(next_tool['args'])
        
        try:
            await callback.message.edit_text(
                f"❌ Azione '{fn_name}' annullata.\nPuoi scrivermi qui sotto le correzioni da applicare.\n\nAzione successiva:\n**{next_tool['name']}**{queue_msg}\n\n{formatted_args}\n\nConfermi?", 
                reply_markup=markup,
                parse_mode="Markdown"
            )
        except Exception:
            await callback.message.edit_text(
                f"❌ Azione '{fn_name}' annullata.\nPuoi scrivermi qui sotto le correzioni da applicare.\n\nAzione successiva:\n{next_tool['name']}{queue_msg}\n\n{formatted_args}\n\nConfermi?", 
                reply_markup=markup
            )
    else:
        await state.update_data(messages=messages, pending_tool=None, pending_args=None, pending_tools_queue=[])
        await callback.message.edit_text(f"❌ Azione '{fn_name}' annullata.\n\nScrivi qui sotto cosa c'era di sbagliato e ricreerò l'azione corretta.")
