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
            "description": "Salva una sessione passata nel database.",
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
            "description": "Pianifica un appuntamento futuro in agenda.",
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
    }
]

async def chat_with_agent(messages: list[dict]) -> tuple[ChatMessage, list[ToolCall]]:
    # Convert list of dicts to ChatMessage objects
    formatted_messages = [ChatMessage(role=m["role"], content=m["content"]) for m in messages]
    
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
