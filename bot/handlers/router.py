import asyncio
import os
from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from langchain_core.messages import HumanMessage
from services.ai_service import transcribe_audio
from database.connection import get_collection, get_group_config
from langchain_core.messages import HumanMessage, ToolMessage
from bot.main_registry import AGENT_REGISTRY, _processing_locks
from utils.helpers import invoke_with_backoff, send_split_message
from utils.logger import db_log

router = Router()

async def transcribe_voice(message: Message, known_names: list[str] = None) -> str:
    file_id = message.voice.file_id
    file = await message.bot.get_file(file_id)
    file_path = f"tmp_{file_id}.ogg"
    await message.bot.download_file(file.file_path, file_path)
    try:
        text = await transcribe_audio(file_path, known_names=known_names)
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
    return text

@router.message((F.text & ~F.text.startswith("/")) | F.voice)
async def route_message(message: Message):
    if message.chat.type == "private":
        await message.reply("ℹ️ Per interagire con me, scrivi nel gruppo nei topic dedicati.")
        return

    topic_id = message.message_thread_id
    
    # Se il topic non è registrato, usa l'agente di default (chiave None)
    agent_config = AGENT_REGISTRY.get(topic_id, AGENT_REGISTRY[None])
    
    # 1. Rate Limit check
    user_id = str(message.from_user.id)
    allowed, reason = agent_config["rate_limiter"].check(user_id)
    if not allowed:
        await message.reply(reason)
        return
        
    # 2. Concurrency Lock
    thread_key = f"{user_id}_{topic_id}"
    if thread_key not in _processing_locks:
        _processing_locks[thread_key] = asyncio.Lock()
        
    if _processing_locks[thread_key].locked():
        await message.reply("⏳ Sto già elaborando un tuo messaggio in questa chat, attendi...")
        return
        
    async with _processing_locks[thread_key]:
        await message.bot.send_chat_action(chat_id=message.chat.id, action="typing", message_thread_id=topic_id)
        
        if message.voice:
            # Carica i nomi noti dal DB per guidare la trascrizione
            user_id = str(message.from_user.id)
            try:
                col_utenti = await get_collection("utenti", uid=user_id)
                utenti_db = await col_utenti.find({}, {"nome": 1}).to_list(length=100)
                known_names = [u["nome"] for u in utenti_db if u.get("nome")]
            except Exception:
                known_names = []
            
            text = await transcribe_voice(message, known_names=known_names)
            try:
                await message.reply(f"🎙️ <b>Trascrizione:</b> {text}", parse_mode="HTML")
            except Exception:
                await message.reply(f"🎙️ Trascrizione: {text}")
        else:
            text = message.text
            
        group_config = await get_group_config(message.chat.id)
        if not group_config:
            await db_log("DEBUG", "router", "Ignorato: Configurazione di gruppo non trovata.")
            try:
                await message.reply("⚠️ Esegui /setup per configurare i topic in questo gruppo.")
            except Exception:
                pass
            return
            
        segreteria_id = group_config.get("segreteria_id")
        diario_id = group_config.get("diario_id")
        owner_id = group_config.get("owner_id", user_id)
        
        await db_log("DEBUG", "router", f"Messaggio da {user_id}. Thread: {message.message_thread_id}. GroupOwner: {owner_id}, Seg={segreteria_id}, Diar={diario_id}")
            
        # Ignora i messaggi nei topic non gestiti (incluso il topic Generale)
        if message.message_thread_id not in [segreteria_id, diario_id]:
            await db_log("DEBUG", "router", f"Ignorato: thread_id {message.message_thread_id} non in [{segreteria_id}, {diario_id}]")
            return
            
        config = {
            "configurable": {
                "thread_id": thread_key,
                "user_id": owner_id,
                "bot": message.bot,
                "chat_id": message.chat.id
            }
        }
        
        try:
            # Build and inject system prompt dynamically if it's the first message or if it's stateless injected
            # LangGraph can keep it in state, but to ensure up-to-date data, we rely on the node logic.
            # Here we just pass the human message. The memory manager or agent node handles system prompt.
            
            await db_log("INFO", "chat", f"📩 Ricevuto da {user_id} in {message.message_thread_id}:\n{text}")
            
            # Controllo se il grafo è attualmente interrotto (richiesta tool in sospeso)
            state = await agent_config["graph"].aget_state(config)
            if state.next and "write_tools" in state.next:
                # L'utente ha ignorato i bottoni di conferma e ha inviato un messaggio di testo
                # Annulliamo automaticamente i tool in sospeso per evitare crash (message_order)
                last_msg = state.values["messages"][-1]
                if hasattr(last_msg, 'tool_calls') and last_msg.tool_calls:
                    tool_messages = []
                    for tc in last_msg.tool_calls:
                        tool_messages.append(ToolMessage(
                            tool_call_id=tc["id"],
                            name=tc["name"],
                            content="L'utente ha ignorato questa azione inviando un nuovo messaggio testuale. Operazione annullata."
                        ))
                    await agent_config["graph"].aupdate_state(config, {"messages": tool_messages}, as_node="write_tools")
            
            status_msg = await message.reply("⏳ <i>Elaborazione in corso...</i>", parse_mode="HTML")
                
            result = await invoke_with_backoff(
                agent_config["graph"],
                {"messages": [HumanMessage(content=text)]},
                config,
                status_msg
            )
            
            # Controlla se il grafo è interrotto (aspetta conferma per i write_tools)
            state = await agent_config["graph"].aget_state(config)
            
            if state.next and "write_tools" in state.next:
                # Il grafo si è interrotto prima di write_tools
                # Estraiamo l'ultima richiesta di tool per farla approvare
                last_msg = state.values["messages"][-1]
                
                # Costruisci descrizione dettagliata con argomenti
                tools_lines = []
                for tc in last_msg.tool_calls:
                    args = tc.get("args", {})
                    # Filtra 'config' e campi interni, mostra solo i parametri utili
                    readable_args = {k: v for k, v in args.items() if k != "config" and v is not None}
                    if readable_args:
                        args_str = ", ".join(f"<i>{k}</i>=<code>{v}</code>" for k, v in readable_args.items())
                        tools_lines.append(f"• <b>{tc['name']}</b>\n  {args_str}")
                    else:
                        tools_lines.append(f"• <b>{tc['name']}</b>")
                tools_desc = "\n".join(tools_lines)
                
                markup = InlineKeyboardMarkup(inline_keyboard=[
                    [
                        InlineKeyboardButton(text="✅ Conferma Azione", callback_data="confirm_tools"),
                        InlineKeyboardButton(text="❌ Annulla", callback_data="cancel_tools")
                    ]
                ])
                await db_log("INFO", "agent", f"⚠️ Richiesta approvazione tools:\n{tools_desc}")
                try:
                    await status_msg.edit_text(f"⚠️ <b>Richiesta di conferma</b>\nL'agente vuole eseguire:\n\n{tools_desc}", reply_markup=markup, parse_mode="HTML")
                except Exception:
                    await message.reply(f"⚠️ <b>Richiesta di conferma</b>\nL'agente vuole eseguire:\n\n{tools_desc}", reply_markup=markup, parse_mode="HTML")
            else:
                # Nessuna interruzione, risposta finale
                final_msg = result["messages"][-1]
                await db_log("INFO", "chat", f"📤 Risposta dell'agente a {user_id}:\n{final_msg.content}")
                await send_split_message(status_msg, final_msg.content, parse_mode="HTML_from_Markdown")
                
        except Exception as e:
            await db_log("ERROR", "router", f"Errore durante l'esecuzione del grafo: {e}")
            try:
                if 'status_msg' in locals():
                    await status_msg.edit_text("❌ Si è verificato un errore interno. Riprova.")
                else:
                    await message.reply("❌ Si è verificato un errore interno. Riprova.")
            except Exception:
                pass
                
    # Lock Cleanup
    if thread_key in _processing_locks and not _processing_locks[thread_key].locked():
        _processing_locks.pop(thread_key, None)
