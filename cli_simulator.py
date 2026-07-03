import asyncio
import json
from dotenv import load_dotenv
load_dotenv()
from services.ai_agent import chat_with_agent

async def main():
    messages = [{"role": "system", "content": "Sei l'assistente IA di un'educatrice. Oggi è il 3 Luglio 2026. Puoi conversare liberamente e se noti l'intenzione di salvare dati usa i tools."}]
    
    script = [
        "Ciao, volevo appuntarmi che oggi ho fatto 2 ore con Giulia. Abbiamo lavorato sulla matematica e ha fatto molti progressi con le divisioni.",
        "confirm",
        "Perfetto. E per dopodomani dalle 15 alle 17 segnami un appuntamento con Marco in ludoteca."
    ]
    
    print("\n" + "="*50)
    print("INIZIO SIMULAZIONE DI CHAT (Locale)")
    print("="*50 + "\n")
    
    for user_text in script:
        if user_text == "confirm":
            print("\n[TU] 👉 *Clicca sul bottone ✅ Conferma Azione*", flush=True)
            print("[BOT] 🤖: ✅ Sessione registrata nel DB e nel Foglio Google.", flush=True)
            messages.append({"role": "system", "content": "L'utente ha confermato e l'azione è stata eseguita con successo."})
            continue
            
        print(f"\n[TU] 👉: {user_text}", flush=True)
        messages.append({"role": "user", "content": user_text})
        
        # Simuliamo il pensiero del bot
        print("[BOT] 💭 (Analisi di Mistral in corso...)", flush=True)
        bot_msg, tool_calls = await chat_with_agent(messages)
        
        if tool_calls:
            for tc in tool_calls:
                fn_name = tc.function.name
                fn_args = json.loads(tc.function.arguments)
                print(f"[BOT] 🤖: L'agente vuole eseguire l'azione: **{fn_name}**")
                print(f"Dati dedotti automaticamente:")
                print(json.dumps(fn_args, indent=2))
                print("\nVuoi confermare? [✅ Conferma Azione] [❌ Annulla]")
        else:
            print(f"[BOT] 🤖: {bot_msg.content}")
            messages.append({"role": "assistant", "content": bot_msg.content})
            
    print("\n" + "="*50)
    print("FINE SIMULAZIONE")
    print("="*50 + "\n")

if __name__ == '__main__':
    asyncio.run(main())
