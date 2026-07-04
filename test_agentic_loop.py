import asyncio
import json
import os
from dotenv import load_dotenv

# Load env before importing anything else
load_dotenv()

from services.ai_agent import chat_with_agent

async def run_test():
    messages = [
        {
            "role": "system",
            "content": (
                "Sei l'assistente IA operativo di un'educatrice. Oggi è 2026-07-04. "
                "Gli utenti attualmente in carico sono: Mario Rossi, Luigi Bianchi. "
                "Il tuo unico scopo è estrarre dati strutturati per eseguire i Tool a tua disposizione "
                "(registra_sessione, pianifica_sessione, crea_utente, cerca_utenti, leggi_storico_sessioni). "
                "REGOLE RIGIDE:\n"
                "- Mantieni un tono essenziale, professionale e oggettivo.\n"
                "- Se mancano parametri obbligatori per un tool, chiedili in modo diretto."
            )
        },
        {
            "role": "user",
            "content": "Lunedì ho visto Mario 2 ore. Martedì ho pianificato un nuovo utente, Giovanna, per dopodomani 2 ore dalle 15 alle 17 in sede."
        }
    ]

    print("\n--- INIZIO TEST LOOP AGENTICO ---")
    MAX_LOOP = 5
    loop_count = 0
    pending_write_tools = []
    
    while loop_count < MAX_LOOP:
        loop_count += 1
        print(f"\n[Iterazione {loop_count}] Chiamata a Mistral...")
        bot_msg, tool_calls = await chat_with_agent(messages)
        
        if not tool_calls:
            print("[Mistral Output Testo]:", bot_msg.content)
            break
            
        print(f"[Mistral richiede {len(tool_calls)} Tool Calls]")
        
        tc_dicts = [{"id": tc.id, "function": {"name": tc.function.name, "arguments": tc.function.arguments}} for tc in tool_calls]
        messages.append({"role": "assistant", "content": bot_msg.content or "", "tool_calls": tc_dicts})
        
        has_read_tools = False
        
        for tc in tool_calls:
            fn_name = tc.function.name
            fn_args = json.loads(tc.function.arguments)
            print(f"  -> Eseguo/Accodo {fn_name}: {fn_args}")
            
            if fn_name == "cerca_utenti":
                has_read_tools = True
                query = fn_args.get("query", "")
                # Simulate DB Response
                if "mario" in query.lower():
                    res_str = json.dumps([{"nome": "Mario Rossi", "ore_settimanali": 10}])
                else:
                    res_str = "Nessun utente trovato con questo nome. Valuta se usare crea_utente."
                
                print(f"     Risultato DB fittizio: {res_str}")
                messages.append({"role": "tool", "name": fn_name, "content": res_str, "tool_call_id": tc.id})
                
            elif fn_name == "leggi_storico_sessioni":
                has_read_tools = True
                res_str = "Nessuna sessione trovata per questo utente."
                print(f"     Risultato DB fittizio: {res_str}")
                messages.append({"role": "tool", "name": fn_name, "content": res_str, "tool_call_id": tc.id})
                
            else:
                pending_write_tools.append({"name": fn_name, "args": fn_args, "id": tc.id})
                messages.append({"role": "tool", "name": fn_name, "content": "Azione in attesa di conferma dell'utente.", "tool_call_id": tc.id})
                
        if not has_read_tools and pending_write_tools:
            print("\n[LOOP TERMINATO] Ci sono Write Tools in attesa di conferma.")
            break
            
    if pending_write_tools:
        print("\n--- RIEPILOGO AZIONI DA CONFERMARE ---")
        for i, pt in enumerate(pending_write_tools, 1):
            print(f"{i}. {pt['name']}")
            for k, v in pt['args'].items():
                print(f"   - {k}: {v}")

if __name__ == "__main__":
    asyncio.run(run_test())
