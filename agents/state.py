from typing import Annotated, TypedDict
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    # Contatore errori Pydantic consecutivi (per self-reflection sui tool)
    pydantic_error_count: int
    # ID utente Telegram (iniettato dal middleware per isolare il tenant)
    telegram_user_id: str
    # Flag per indicare se ci sono tool in attesa di conferma umana
    pending_human_confirmation: bool
