from aiogram import Router, F
from aiogram.types import CallbackQuery
from langchain_core.messages import ToolMessage
from bot.main_registry import AGENT_REGISTRY, _processing_locks
from utils.helpers import invoke_with_backoff
from utils.logger import db_log

router = Router()

@router.callback_query(F.data == "confirm_tools")
async def confirm_tools(callback: CallbackQuery):
    await callback.answer("⏳ Esecuzione in corso...")
    
    topic_id = callback.message.message_thread_id
    agent_config = AGENT_REGISTRY.get(topic_id, AGENT_REGISTRY[None])
    user_id = str(callback.from_user.id)
    thread_key = f"{user_id}_{topic_id}"
    
    config = {
        "configurable": {
            "thread_id": thread_key,
            "user_id": user_id,
        }
    }
    
    async with _processing_locks[thread_key]:
        try:
            await db_log("INFO", "agent", f"Utente {user_id} ha CONFERMATO l'esecuzione dei tool.")
            # Riprendi l'esecuzione (valore None fa riprendere dal punto di interrupt)
            async def send_msg(text):
                await callback.message.answer(text, parse_mode="HTML")
                
            result = await invoke_with_backoff(
                agent_config["graph"],
                None,
                config,
                send_msg
            )
            state = await agent_config["graph"].aget_state(config)
            if state.next and "write_tools" in state.next:
                pass # Continua ad aspettare conferme (non dovrebbe succedere se abbiamo eseguito tutti i tool)
            else:
                final_msg = result["messages"][-1]
                try:
                    await callback.message.edit_text(f"✅ **Eseguito**\n\n{final_msg.content}", parse_mode="Markdown")
                except Exception:
                    await callback.message.edit_text(f"✅ Eseguito\n\n{final_msg.content}")
        except Exception as e:
            await callback.message.edit_text(f"❌ Errore durante l'esecuzione: {e}")

@router.callback_query(F.data == "cancel_tools")
async def cancel_tools(callback: CallbackQuery):
    await callback.answer("Annullato")
    
    topic_id = callback.message.message_thread_id
    user_id = str(callback.from_user.id)
    await db_log("INFO", "agent", f"Utente {user_id} ha ANNULLATO l'esecuzione dei tool.")
    agent_config = AGENT_REGISTRY.get(topic_id, AGENT_REGISTRY[None])
    user_id = str(callback.from_user.id)
    thread_key = f"{user_id}_{topic_id}"
    
    config = {
        "configurable": {
            "thread_id": thread_key,
            "user_id": user_id,
        }
    }
    
    async with _processing_locks[thread_key]:
        try:
            # Dobbiamo aggiornare lo stato in LangGraph per comunicare l'annullamento
            # Raccogliamo l'ultima chiamata al tool
            state = await agent_config["graph"].aget_state(config)
            last_msg = state.values["messages"][-1]
            
            tool_messages = []
            for tc in last_msg.tool_calls:
                tool_messages.append(ToolMessage(
                    tool_call_id=tc["id"],
                    name=tc["name"],
                    content="L'utente ha annullato questa operazione."
                ))
            
            # Iniettiamo il finto risultato del tool e continuiamo come se il tool avesse restituito "annullato"
            result = await agent_config["graph"].ainvoke({"messages": tool_messages}, config=config)
            
            final_msg = result["messages"][-1]
            try:
                await callback.message.edit_text(f"❌ **Azione Annullata**\n\n{final_msg.content}", parse_mode="Markdown")
            except Exception:
                await callback.message.edit_text(f"❌ Azione Annullata\n\n{final_msg.content}")
        except Exception as e:
            await callback.message.edit_text(f"❌ Errore durante l'annullamento: {e}")
