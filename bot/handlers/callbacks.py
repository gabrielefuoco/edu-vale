from aiogram import Router, F
from aiogram.types import CallbackQuery
from langchain_core.messages import ToolMessage
from bot.main_registry import AGENT_REGISTRY, _processing_locks
from utils.helpers import invoke_with_backoff, send_split_message
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
            await callback.message.edit_text("⏳ <i>Esecuzione tool in corso...</i>", parse_mode="HTML")
            
            # Riprendi l'esecuzione (valore None fa riprendere dal punto di interrupt)
            result = await invoke_with_backoff(
                agent_config["graph"],
                None,
                config,
                callback.message
            )
            state = await agent_config["graph"].aget_state(config)
            if state.next and "write_tools" in state.next:
                pass # Continua ad aspettare conferme (non dovrebbe succedere se abbiamo eseguito tutti i tool)
            else:
                final_msg = result["messages"][-1]
                await send_split_message(callback.message, f"✅ **Eseguito**\n\n{final_msg.content}", parse_mode="HTML_from_Markdown")
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
            state = await agent_config["graph"].aget_state(config)
            
            # Verifichiamo che ci sia un AIMessage con tool_calls prima di annullare
            last_msg = state.values["messages"][-1]
            if hasattr(last_msg, 'tool_calls') and last_msg.tool_calls:
                tool_messages = []
                for tc in last_msg.tool_calls:
                    tool_messages.append(ToolMessage(
                        tool_call_id=tc["id"],
                        name=tc["name"],
                        content="L'utente ha annullato l'operazione."
                    ))
                
                # Aggiorniamo lo stato bypassando il nodo write_tools
                await agent_config["graph"].aupdate_state(config, {"messages": tool_messages}, as_node="write_tools")
            
            await callback.message.edit_text("⏳ <i>Annullamento in corso...</i>", parse_mode="HTML")
            
            # Riprendiamo l'esecuzione del grafo
            result = await invoke_with_backoff(
                agent_config["graph"],
                None,
                config,
                callback.message
            )
            
            state = await agent_config["graph"].aget_state(config)
            if state.next and "write_tools" in state.next:
                pass
            else:
                final_msg = result["messages"][-1]
                await send_split_message(callback.message, f"❌ **Azione Annullata**\n\n{final_msg.content}", parse_mode="HTML_from_Markdown")
        except Exception as e:
            await callback.message.edit_text(f"❌ Errore durante l'annullamento: {e}")
