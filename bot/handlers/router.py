import asyncio
from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from langchain_core.messages import HumanMessage
from services.ai_service import transcribe_audio
from utils.logger import db_log
from bot.main_registry import AGENT_REGISTRY, _processing_locks
import os

router = Router()

async def transcribe_voice(message: Message) -> str:
    file_id = message.voice.file_id
    file = await message.bot.get_file(file_id)
    file_path = f"tmp_{file_id}.ogg"
    await message.bot.download_file(file.file_path, file_path)
    try:
        text = await transcribe_audio(file_path)
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
    return text

@router.message((F.text & ~F.text.startswith("/")) | F.voice)
async def route_message(message: Message):
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
            text = await transcribe_voice(message)
            await message.reply(f"🎙️ *Trascrizione:* {text}", parse_mode="Markdown")
        else:
            text = message.text
            
        config = {
            "configurable": {
                "thread_id": thread_key,
                "user_id": user_id,
            }
        }
        
        try:
            # Build and inject system prompt dynamically if it's the first message or if it's stateless injected
            # LangGraph can keep it in state, but to ensure up-to-date data, we rely on the node logic.
            # Here we just pass the human message. The memory manager or agent node handles system prompt.
            
            result = await agent_config["graph"].ainvoke(
                {"messages": [HumanMessage(content=text)]},
                config=config,
            )
            
            # Controlla se il grafo è interrotto (aspetta conferma per i write_tools)
            state = await agent_config["graph"].aget_state(config)
            
            if state.next and "write_tools" in state.next:
                # Il grafo si è interrotto prima di write_tools
                # Estraiamo l'ultima richiesta di tool per farla approvare
                last_msg = state.values["messages"][-1]
                tools_desc = "\n".join([f"- {tc['name']}" for tc in last_msg.tool_calls])
                
                markup = InlineKeyboardMarkup(inline_keyboard=[
                    [
                        InlineKeyboardButton(text="✅ Conferma Azione", callback_data="confirm_tools"),
                        InlineKeyboardButton(text="❌ Annulla", callback_data="cancel_tools")
                    ]
                ])
                await message.reply(f"⚠️ **Richiesta di conferma**\nL'agente vuole eseguire le seguenti azioni:\n{tools_desc}", reply_markup=markup, parse_mode="Markdown")
            else:
                # Nessuna interruzione, risposta finale
                final_msg = result["messages"][-1]
                await message.reply(final_msg.content)
                
        except Exception as e:
            await db_log("ERROR", "router", f"Errore durante l'esecuzione del grafo: {e}")
            await message.reply("❌ Si è verificato un errore interno. Riprova.")
