from agents.factory import create_agent
from agents.prompts import build_segretario_prompt
from tools.read_tools import cerca_utenti, leggi_storico_sessioni, leggi_agenda
from tools.write_tools import (
    registra_sessione, pianifica_sessione, crea_utente,
    elimina_utente, modifica_utente, elimina_sessione_pianificata,
    modifica_sessione_pianificata, modifica_sessione_passata,
    elimina_sessione_passata, modifica_nota_utente, elimina_nota_utente
)
from tools.diario_tools import aggiungi_nota_utente

def create_segretario(checkpointer):
    tools = [
        cerca_utenti, leggi_storico_sessioni, leggi_agenda,
        registra_sessione, pianifica_sessione, crea_utente,
        elimina_utente, modifica_utente, elimina_sessione_pianificata,
        modifica_sessione_pianificata, modifica_sessione_passata,
        elimina_sessione_passata, aggiungi_nota_utente,
        modifica_nota_utente, elimina_nota_utente
    ]
    
    return create_agent(
        agent_name="segretario",
        model_name="mistral-large-latest",
        system_prompt_builder=build_segretario_prompt,
        tools=tools,
        checkpointer=checkpointer,
        max_iterations=10,
        rate_limit_min=10,
        rate_limit_hour=100,
        read_tool_names=["cerca_utenti", "leggi_storico_sessioni", "leggi_agenda"],
        write_tool_names=[
            "registra_sessione", "pianifica_sessione", "crea_utente",
            "elimina_utente", "modifica_utente", "elimina_sessione_pianificata",
            "modifica_sessione_pianificata", "modifica_sessione_passata",
            "elimina_sessione_passata", "aggiungi_nota_utente",
            "modifica_nota_utente", "elimina_nota_utente"
        ],
    )
