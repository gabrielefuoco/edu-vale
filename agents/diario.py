from agents.factory import create_agent
from agents.prompts import build_diario_prompt
from tools.read_tools import cerca_utenti, leggi_storico_sessioni, leggi_diari_bordo
from tools.diario_tools import salva_diario_bordo, aggiungi_nota_utente, modifica_diario_bordo, elimina_diario_bordo

def create_diario_agent(checkpointer):
    tools = [
        cerca_utenti, leggi_storico_sessioni, leggi_diari_bordo,
        salva_diario_bordo, aggiungi_nota_utente, modifica_diario_bordo, elimina_diario_bordo
    ]
    
    return create_agent(
        agent_name="diario",
        model_name="mistral-small-latest",
        system_prompt_builder=build_diario_prompt,
        tools=tools,
        checkpointer=checkpointer,
        max_iterations=10,
        rate_limit_min=10,
        rate_limit_hour=100,
        read_tool_names=["cerca_utenti", "leggi_storico_sessioni", "leggi_diari_bordo"],
        write_tool_names=["salva_diario_bordo", "aggiungi_nota_utente", "modifica_diario_bordo", "elimina_diario_bordo"],
    )
