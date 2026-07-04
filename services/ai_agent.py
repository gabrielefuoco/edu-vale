import os
import json
from mistralai.async_client import MistralAsyncClient
from mistralai.models.chat_completion import ChatMessage, ToolCall

mistral_client = MistralAsyncClient(api_key=os.getenv("MISTRAL_API_KEY"))

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "registra_sessione",
            "description": "Salva una sessione GIA' AVVENUTA in passato o nella giornata di oggi. Non usare per il futuro.",
            "parameters": {
                "type": "object",
                "properties": {
                    "Giorno": {"type": "string", "description": "Data in formato YYYY-MM-DD"},
                    "Ore": {"type": "number", "description": "Ore svolte"},
                    "Utente": {"type": "string", "description": "Nome dell'utente"},
                    "Luogo": {"type": "string", "description": "Luogo dell'incontro"},
                    "Attività svolte": {"type": "string", "description": "Riassunto delle attività"}
                },
                "required": ["Giorno", "Ore", "Utente", "Attività svolte"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "pianifica_sessione",
            "description": "Pianifica un appuntamento FUTURO in agenda. Non usare per eventi già conclusi.",
            "parameters": {
                "type": "object",
                "properties": {
                    "Data": {"type": "string", "description": "Data in formato YYYY-MM-DD"},
                    "Ora Inizio": {"type": "string", "description": "Ora inizio HH:MM"},
                    "Ora Fine": {"type": "string", "description": "Ora fine HH:MM"},
                    "Utente": {"type": "string", "description": "Nome dell'utente"},
                    "Luogo": {"type": "string", "description": "Luogo"}
                },
                "required": ["Data", "Ora Inizio", "Ora Fine", "Utente"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "crea_utente",
            "description": "Crea un nuovo utente. Usalo SOLO se l'utente non è nella lista degli utenti in carico o se cerca_utenti ha dato esito vuoto.",
            "parameters": {
                "type": "object",
                "properties": {
                    "nome": {"type": "string", "description": "Nome e cognome dell'utente"},
                    "ore_settimanali": {"type": "number", "description": "Ore settimanali previste, default 0 se non specificato"},
                    "note": {"type": "string", "description": "Eventuali note sull'utente"}
                },
                "required": ["nome"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "cerca_utenti",
            "description": "Cerca nel database il nome completo di un utente. Usalo SEMPRE se l'utente fornisce solo il nome di battesimo (es. 'Mario') per disambiguare.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Nome o parte del nome dell'utente da cercare"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "leggi_storico_sessioni",
            "description": "Legge le sessioni passate di un utente per ricavare contesto o controllare duplicati.",
            "parameters": {
                "type": "object",
                "properties": {
                    "utente": {"type": "string", "description": "Nome dell'utente"},
                    "limite": {"type": "number", "description": "Numero massimo di sessioni da recuperare (default 5)"}
                },
                "required": ["utente"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "leggi_agenda",
            "description": "Legge gli appuntamenti pianificati nel futuro (nella data specificata) per evitare sovrapposizioni o rispondere a domande sull'agenda.",
            "parameters": {
                "type": "object",
                "properties": {
                    "data_inizio": {"type": "string", "description": "Data inizio ricerca in formato YYYY-MM-DD"},
                    "data_fine": {"type": "string", "description": "Data fine ricerca in formato YYYY-MM-DD (opzionale)"}
                },
                "required": ["data_inizio"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "elimina_sessione_pianificata",
            "description": "Annulla e rimuove un appuntamento futuro precedentemente pianificato.",
            "parameters": {
                "type": "object",
                "properties": {
                    "Data": {"type": "string", "description": "Data dell'appuntamento da annullare (YYYY-MM-DD)"},
                    "Utente": {"type": "string", "description": "Nome dell'utente"}
                },
                "required": ["Data", "Utente"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "modifica_utente",
            "description": "Aggiorna i dati anagrafici di un utente esistente (ore settimanali o note).",
            "parameters": {
                "type": "object",
                "properties": {
                    "nome_utente": {"type": "string", "description": "Nome esatto dell'utente"},
                    "ore_settimanali": {"type": "number", "description": "Nuove ore settimanali (opzionale se si vogliono cambiare solo le note)"},
                    "note": {"type": "string", "description": "Nuove note da aggiungere (opzionale se si vogliono cambiare solo le ore)"}
                },
                "required": ["nome_utente"]
            }
        }
    }
]

async def chat_with_agent(messages: list[dict]) -> tuple[ChatMessage, list[ToolCall]]:
    formatted_messages = []
    for m in messages:
        kwargs = {"role": m["role"], "content": m.get("content", "")}
        if "tool_calls" in m and m["tool_calls"]:
            # Reconstruct ToolCall objects
            kwargs["tool_calls"] = []
            for tc in m["tool_calls"]:
                from mistralai.models.chat_completion import FunctionCall
                kwargs["tool_calls"].append(ToolCall(
                    id=tc["id"],
                    type="function",
                    function=FunctionCall(name=tc["function"]["name"], arguments=tc["function"]["arguments"])
                ))
        if "name" in m:
            kwargs["name"] = m["name"]
        if "tool_call_id" in m:
            kwargs["tool_call_id"] = m["tool_call_id"]
            
        formatted_messages.append(ChatMessage(**kwargs))
    
    response = await mistral_client.chat(
        model="mistral-large-latest", # large is better for tool calling
        messages=formatted_messages,
        tools=TOOLS,
        tool_choice="auto"
    )
    
    message = response.choices[0].message
    tool_calls = message.tool_calls if hasattr(message, 'tool_calls') and message.tool_calls else []
    
    return message, tool_calls

async def summarize_context(messages: list[dict]) -> list[dict]:
    context_lines = []
    for m in messages:
        if m['role'] == 'system' and m['content'].startswith("Riassunto contesto precedente:"):
            context_lines.append(f"[STORICO PRECEDENTE]: {m['content']}")
        elif m['role'] != 'system':
            context_lines.append(f"{m['role']}: {m['content']}")
            
    text_context = "\n".join(context_lines)
    prompt = (
        "Riassumi il seguente storico di conversazione. Estrai in modo asettico, oggettivo e cronologico "
        "esclusivamente i fatti, le azioni richieste e i dati citati (nomi, luoghi, orari, task). "
        "ELIMINA categoricamente qualsiasi chiacchierata, saluto, opinione o commento emotivo. "
        "Il risultato deve essere una sintesi puramente operativa da usare come memoria tecnica:\n"
        f"{text_context}"
    )
    
    res = await mistral_client.chat(
        model="mistral-small-latest",
        messages=[ChatMessage(role="user", content=prompt)]
    )
    
    summary = res.choices[0].message.content
    return [{"role": "system", "content": "Riassunto contesto precedente: " + summary}]
