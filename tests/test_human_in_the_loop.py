import pytest
import json
from langchain_core.messages import AIMessage
from langchain_core.messages.tool import ToolCall
from tests.conftest import FakeCallbackQuery
from tests.mock_llm_state import set_next_llm_response
from bot.handlers.router import route_message
from bot.handlers.callbacks import confirm_tools
from bot.main_registry import AGENT_REGISTRY
from agents.segretario import create_segretario
from langgraph.checkpoint.memory import MemorySaver

@pytest.fixture(autouse=True)
def setup_agents():
    checkpointer = MemorySaver()
    segretario = create_segretario(checkpointer)
    AGENT_REGISTRY.clear()
    AGENT_REGISTRY[None] = segretario

@pytest.mark.asyncio
async def test_write_tool_interrupt_and_confirm(fake_msg_factory, mock_db):
    msg = fake_msg_factory("Registra sessione di 2 ore", thread_id=None)
    
    # Prepariamo la richiesta Tool
    args = {"Giorno": "2026-07-04", "Ore": 2.0, "Utente": "Mario Rossi", "Attivita_svolte": "Studio"}
    tc = {"name": "registra_sessione", "args": args, "id": "call_123", "type": "tool_call"}
    
    # L'LLM restituisce il tool call
    set_next_llm_response(AIMessage(content="", tool_calls=[tc]))
    
    # 1. Routing del messaggio (fermerà il grafo all'interrupt)
    await route_message(msg)
    
    state = await AGENT_REGISTRY[None]["graph"].aget_state({"configurable": {"thread_id": "12345_None", "user_id": "12345"}})
    print("STATE.NEXT:", state.next)
    print("REPLIES:", msg.replies)
    
    # Verifica che il bot abbia mostrato il messaggio di interruzione
    assert "Richiesta di conferma" in msg.replies[-1]["text"]
    
    # 2. L'LLM genera la risposta finale dopo l'esecuzione del tool
    set_next_llm_response(AIMessage(content="Fatto, ho registrato!"))
    
    # 3. L'utente clicca Conferma
    cb = FakeCallbackQuery("confirm_tools", message=msg)
    await confirm_tools(cb)
    
    # Verifica che il tool abbia scritto nel database finto
    col = mock_db["edu_agent_default"]["diario_sessioni"]
    docs = await col.find().to_list(10)
    assert len(docs) == 1
    assert docs[0]["utente_id"] == "Mario Rossi"
    assert docs[0]["ore_svolte"] == 2.0
    
    # Verifica la risposta finale inviata all'utente
    assert any("Fatto, ho registrato!" in r["text"] for r in msg.replies)
