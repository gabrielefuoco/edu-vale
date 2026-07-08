import pytest
from bot.main_registry import AGENT_REGISTRY
from bot.handlers.router import route_message
from agents.segretario import create_segretario
from agents.diario import create_diario_agent
from langgraph.checkpoint.memory import MemorySaver

@pytest.fixture(autouse=True)
def setup_agents():
    checkpointer = MemorySaver()
    segretario = create_segretario(checkpointer)
    diario = create_diario_agent(checkpointer)
    
    AGENT_REGISTRY.clear()
    AGENT_REGISTRY[None] = segretario
    AGENT_REGISTRY[100] = segretario # Topic Segreteria fittizio
    AGENT_REGISTRY[200] = diario     # Topic Diari fittizio

@pytest.mark.asyncio
async def test_route_private_chat_rate_limit(fake_msg_factory):
    # Test rate limiter limit
    messages = [fake_msg_factory(f"Msg {i}", thread_id=None) for i in range(12)]
    
    for i, msg in enumerate(messages):
        await route_message(msg)
        if i >= 10:
            # Dovrebbe bloccare
            assert any("Troppi messaggi" in r["text"] for r in msg.replies)
        else:
            # Non dovrebbe bloccare
            assert not any("Troppi messaggi" in r["text"] for r in msg.replies)

@pytest.mark.asyncio
async def test_route_to_diario(fake_msg_factory):
    msg = fake_msg_factory("Test diario", thread_id=200)
    await route_message(msg)
    assert len(msg.replies) > 0
    assert "Mock response" in msg.replies[-1]["text"]
