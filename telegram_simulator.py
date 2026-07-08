import asyncio
import os
import sys
from dotenv import load_dotenv
from telethon import TelegramClient

load_dotenv()
api_id = int(os.getenv("TELEGRAM_API_ID"))
api_hash = os.getenv("TELEGRAM_API_HASH")
phone_number = os.getenv("TELEGRAM_PHONE_NUMBER")
bot_username = 'edu_agent_valetta_bot'

async def main():
    client = TelegramClient('test_session', api_id, api_hash)
    
    print("--- INIZIALIZZAZIONE CONNESSIONE TELEGRAM ---", flush=True)
    # Telethon si occuperà di chiedere il codice SMS stampando:
    # "Please enter the code you received: "
    await client.start(phone=phone_number)
    
    print("\n✅ Autenticazione completata con successo!", flush=True)
    print(f"Stiamo per inviare messaggi a @{bot_username}...\n", flush=True)

    messages_to_test = [
        "/utenti",
        "Ciao, oggi ho notato che Marco ha imparato a colorare nei margini",
    ]

    for msg in messages_to_test:
        print(f"👉 INVIANDO (TU): {msg}", flush=True)
        await client.send_message(bot_username, msg)
        
        # Aspettiamo qualche secondo per far elaborare l'agente
        await asyncio.sleep(5)
        
        # Leggiamo l'ultima risposta
        async for message in client.iter_messages(bot_username, limit=1):
            print(f"🤖 RISPOSTA (BOT): {message.text}\n", flush=True)
            
        await asyncio.sleep(3)

    print("Test completato.", flush=True)
    await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
